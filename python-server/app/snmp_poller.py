"""Poller SNMP genérico — telemetria real de qualquer dispositivo cadastrado com SNMP.

Um dispositivo entra no polling quando tem o campo `snmp` (criado em Dispositivos ->
Novo Dispositivo -> "Monitorar via SNMP", ou via POST /api/devices / /api/olts com
`snmp: {community, port, oidGroups}`). A cada SNMP_POLL_INTERVAL segundos, uma
thread de fundo consulta todos eles em paralelo (até SNMP_POLL_MAX_WORKERS) e lê os
grupos de OIDs padrão de app/oids.py que o dispositivo declara em `oidGroups`:

  system      GET  sysDescr, sysObjectID, sysUpTime, sysName, sysLocation
  interfaces  BULK ifTable + ifXTable (contadores de 64 bits quando existirem)
  host        BULK hrProcessorLoad + hrStorageTable (CPU por núcleo, memória, discos)

Só MIBs padrão (RFC 1213/2863/2790): servem para servidores Linux/Windows, switches,
roteadores e para a parte de sistema/interfaces de OLTs. OIDs proprietários (GPON
por ONU, Wi-Fi) e SNMPv3 ficam para uma próxima etapa.

O resultado fica em memória, aqui no módulo; o estado da aplicação não é alterado
pela thread, exceto pelos alertas de "sem resposta"/"voltou a responder". As rotas
enxergam a telemetria via enrich().
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from pysnmp.hlapi import (
    CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine,
    UdpTransportTarget, bulkCmd, getCmd,
)
from pysnmp.proto.rfc1905 import EndOfMibView, NoSuchInstance, NoSuchObject

from .config import settings
from .formatting import uptime_to_string
from .oids import OIDs

DEFAULT_OID_GROUPS = ["system", "interfaces", "host"]
HR_STORAGE_RAM = "1.3.6.1.2.1.25.2.1.2"
HR_STORAGE_FIXED_DISK = "1.3.6.1.2.1.25.2.1.4"
IF_OPER_STATUS = {1: "up", 2: "down", 3: "testing", 4: "unknown", 5: "dormant", 6: "notPresent", 7: "lowerLayerDown"}
MAX_TABLE_ROWS = 2000  # trava de segurança contra tabelas gigantes/agentes com loop


class SnmpError(RuntimeError):
    pass


# ── Leitura SNMP (síncrona; uma chamada por dispositivo, em worker do pool) ─────
def _auth(cfg: dict):
    return CommunityData(cfg.get("community") or settings.snmp_community, mpModel=1)


def _target(ip: str, cfg: dict):
    return UdpTransportTarget((ip, int(cfg.get("port") or 161)),
                              timeout=settings.snmp_timeout, retries=settings.snmp_retries)


def _is_missing(value) -> bool:
    return isinstance(value, (NoSuchObject, NoSuchInstance, EndOfMibView))


def _to_python(value):
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value.prettyPrint()


def _oid_tuple(name) -> tuple:
    oid = name.getOid() if hasattr(name, "getOid") else name
    return tuple(int(x) for x in oid)


def _get(engine, auth, target, oids: dict) -> dict:
    error_indication, error_status, _idx, var_binds = next(getCmd(
        engine, auth, target, ContextData(),
        *[ObjectType(ObjectIdentity(oid)) for oid in oids.values()], lookupMib=False,
    ))
    if error_indication:
        raise SnmpError(str(error_indication))
    if error_status:
        raise SnmpError(error_status.prettyPrint())
    return {name: _to_python(vb[1]) for name, vb in zip(oids, var_binds)}


def _walk_columns(engine, auth, target, columns: dict) -> dict:
    """Lê várias colunas de uma tabela via GETBULK -> {coluna: {índice: valor}}.
    Colunas que o agente não implementa (ex: ifXTable em equipamentos antigos)
    simplesmente voltam vazias."""
    names = list(columns)
    bases = [tuple(int(x) for x in columns[n].split(".")) for n in names]
    result = {n: {} for n in names}
    rows = 0
    for error_indication, error_status, _idx, var_binds in bulkCmd(
        engine, auth, target, ContextData(), 0, 25,
        *[ObjectType(ObjectIdentity(columns[n])) for n in names], lexicographicMode=False, lookupMib=False,
    ):
        if error_indication:
            raise SnmpError(str(error_indication))
        if error_status:
            raise SnmpError(error_status.prettyPrint())
        for vb, name, base in zip(var_binds, names, bases):
            oid = _oid_tuple(vb[0])
            if oid[:len(base)] == base and not _is_missing(vb[1]):
                result[name][".".join(str(x) for x in oid[len(base):])] = _to_python(vb[1])
        rows += 1
        if rows >= MAX_TABLE_ROWS:
            break
    return result


def _read_interfaces(engine, auth, target) -> list:
    i = OIDs["interfaces"]
    cols = _walk_columns(engine, auth, target, {
        k: i[k] for k in ("ifDescr", "ifOperStatus", "ifSpeed", "ifInOctets", "ifOutOctets", "ifInErrors",
                          "ifOutErrors", "ifName", "ifHCInOctets", "ifHCOutOctets", "ifHighSpeed")
    })
    interfaces = []
    for idx in sorted(cols["ifDescr"], key=lambda x: [int(p) for p in x.split(".")]):
        hc = idx in cols["ifHCInOctets"] and idx in cols["ifHCOutOctets"]
        high_speed = cols["ifHighSpeed"].get(idx) or 0
        interfaces.append({
            "index": idx,
            "name": cols["ifName"].get(idx) or cols["ifDescr"][idx],
            "descr": cols["ifDescr"][idx],
            "status": IF_OPER_STATUS.get(cols["ifOperStatus"].get(idx), "unknown"),
            "speedBps": high_speed * 1_000_000 if high_speed else cols["ifSpeed"].get(idx),
            "inOctets": (cols["ifHCInOctets"] if hc else cols["ifInOctets"]).get(idx),
            "outOctets": (cols["ifHCOutOctets"] if hc else cols["ifOutOctets"]).get(idx),
            "counterBits": 64 if hc else 32,
            "inErrors": cols["ifInErrors"].get(idx),
            "outErrors": cols["ifOutErrors"].get(idx),
        })
    return interfaces


def _read_host(engine, auth, target) -> dict:
    h = OIDs["host"]
    cpu = _walk_columns(engine, auth, target, {"load": h["hrProcessorLoad"]})["load"]
    st = _walk_columns(engine, auth, target, {
        k: h[k] for k in ("hrStorageType", "hrStorageDescr", "hrStorageAllocationUnits", "hrStorageSize", "hrStorageUsed")
    })
    memory, disks = [], []
    for idx, stype in st["hrStorageType"].items():
        units = st["hrStorageAllocationUnits"].get(idx) or 0
        size = (st["hrStorageSize"].get(idx) or 0) * units
        used = (st["hrStorageUsed"].get(idx) or 0) * units
        entry = {"descr": st["hrStorageDescr"].get(idx), "sizeBytes": size, "usedBytes": used,
                 "usedPct": round(used / size * 100, 1) if size else None}
        if stype == HR_STORAGE_RAM:
            memory.append(entry)
        elif stype == HR_STORAGE_FIXED_DISK:
            disks.append(entry)
    loads = [v for v in cpu.values() if isinstance(v, int)]
    return {
        "cpuPerCore": loads,
        "cpuAvg": round(sum(loads) / len(loads), 1) if loads else None,
        "memory": memory,
        "disks": disks,
    }


def poll_device(ip: str, cfg: dict) -> dict:
    """Uma leitura completa de um dispositivo. Levanta SnmpError se não responder."""
    groups = cfg.get("oidGroups") or DEFAULT_OID_GROUPS
    engine, auth, target = SnmpEngine(), _auth(cfg), _target(ip, cfg)
    started = time.monotonic()
    s = OIDs["system"]
    data = {"system": _get(engine, auth, target, {
        k: s[k] for k in ("sysDescr", "sysObjectID", "sysUpTime", "sysName", "sysLocation")
    })}
    if "interfaces" in groups:
        data["interfaces"] = _read_interfaces(engine, auth, target)
    if "host" in groups:
        data["host"] = _read_host(engine, auth, target)
    data["responseMs"] = round((time.monotonic() - started) * 1000, 1)
    return data


# ── Taxas a partir dos contadores ──────────────────────────────────────────────
def _counter_delta(cur, prev, bits: int):
    if cur is None or prev is None:
        return None
    delta = cur - prev
    return delta + 2 ** bits if delta < 0 else delta  # contador deu a volta


def _apply_rates(data: dict, prev: dict | None, elapsed: float) -> None:
    """Adiciona inMbps/outMbps em cada interface comparando com a leitura anterior.
    Sem leitura anterior, ou se o equipamento reiniciou (sysUpTime voltou), fica None."""
    rebooted = prev is not None and (data["system"].get("sysUpTime") or 0) < (prev["system"].get("sysUpTime") or 0)
    prev_ifs = {i["index"]: i for i in (prev or {}).get("interfaces", [])} if prev and not rebooted else {}
    for iface in data.get("interfaces", []):
        p = prev_ifs.get(iface["index"])
        if not p or elapsed <= 0 or p["counterBits"] != iface["counterBits"]:
            iface["inMbps"] = iface["outMbps"] = None
            continue
        d_in = _counter_delta(iface["inOctets"], p["inOctets"], iface["counterBits"])
        d_out = _counter_delta(iface["outOctets"], p["outOctets"], iface["counterBits"])
        iface["inMbps"] = round(d_in * 8 / elapsed / 1e6, 3) if d_in is not None else None
        iface["outMbps"] = round(d_out * 8 / elapsed / 1e6, 3) if d_out is not None else None


# ── Poller em background ──────────────────────────────────────────────────────
_lock = threading.Lock()
_stop = threading.Event()
_thread: threading.Thread | None = None
_results: dict = {}  # device_id -> {"ok", "at", "data", "error"}
_cycle = {"lastCycleAt": None, "lastCycleMs": None, "devicesPolled": 0}


def normalize_config(raw) -> dict | None:
    """Valida o `snmp` vindo do cliente (POST /api/devices, /api/olts). Só v2c por ora."""
    if not isinstance(raw, dict) or raw.get("enabled") is False:
        return None
    port = int(raw.get("port") or 161)
    if not 1 <= port <= 65535:
        raise ValueError("porta SNMP inválida")
    groups = [g for g in (raw.get("oidGroups") or DEFAULT_OID_GROUPS) if g in ("system", "interfaces", "host")]
    return {"enabled": True, "version": "2c", "community": str(raw.get("community") or settings.snmp_community),
            "port": port, "oidGroups": groups or ["system"]}


def snmp_config(device: dict) -> dict | None:
    cfg = device.get("snmp")
    return cfg if isinstance(cfg, dict) and cfg.get("enabled", True) else None


def _alert_title(device: dict) -> str:
    return f"Sem resposta SNMP — {device.get('name')}"


def _poll_and_store(device: dict) -> dict:
    from . import state as app_state

    cfg = snmp_config(device)
    now = time.time()
    with _lock:
        prev = _results.get(device["id"])
    try:
        data = poll_device(device["ip"], cfg)
        prev_ok = prev["data"] if prev and prev.get("ok") else None
        _apply_rates(data, prev_ok, now - prev["at"] if prev_ok else 0)
        entry = {"ok": True, "at": now, "data": data, "error": None}
    except Exception as err:  # timeout, community errada, host inexistente...
        entry = {"ok": False, "at": now, "data": prev["data"] if prev else None, "error": str(err) or type(err).__name__}
    with _lock:
        _results[device["id"]] = entry

    # Transições: alerta ao perder resposta (inclusive na 1ª tentativa), resolve ao voltar.
    was_ok = prev["ok"] if prev else None
    if not entry["ok"] and was_ok is not False:
        app_state.raise_device_alert(_alert_title(device), f"{device['ip']} • {entry['error']}", device.get("name"))
    elif entry["ok"] and was_ok is False:
        app_state.resolve_device_alert(_alert_title(device), device.get("name"), f"{device['ip']} voltou a responder SNMP")
    return entry


def poll_now(device: dict) -> dict:
    return _poll_and_store(device)


def _poll_loop() -> None:
    from . import state as app_state

    while not _stop.is_set():
        started = time.monotonic()
        targets = [d for d in app_state.get_devices() if snmp_config(d) and d.get("ip")]
        if targets:
            with ThreadPoolExecutor(max_workers=settings.snmp_poll_max_workers) as pool:
                list(pool.map(_poll_and_store, targets))
        with _lock:
            alive = {d["id"] for d in targets}
            for gone in [k for k in _results if k not in alive]:
                del _results[gone]  # dispositivo removido ou com SNMP desligado
            _cycle.update(lastCycleAt=time.time(), lastCycleMs=round((time.monotonic() - started) * 1000),
                          devicesPolled=len(targets))
        _stop.wait(settings.snmp_poll_interval)


def start() -> None:
    global _thread
    if not settings.snmp_poller_enabled or _thread is not None:
        return
    _stop.clear()
    _thread = threading.Thread(target=_poll_loop, name="snmp-poller", daemon=True)
    _thread.start()


def stop() -> None:
    global _thread
    _stop.set()
    _thread = None


# ── Leitura pelas rotas ──────────────────────────────────────────────────────
def get_result(device_id: int) -> dict | None:
    with _lock:
        return _results.get(device_id)


def _summary(entry: dict) -> dict:
    """Campos planos para tabelas/cards: status e métricas principais."""
    age = time.time() - entry["at"]
    fresh = entry["ok"] and age <= settings.snmp_poll_interval * 3
    out = {"status": "online" if fresh else "offline",
           "snmpStatus": {"ok": entry["ok"], "fresh": fresh, "ageSeconds": round(age, 1), "error": entry["error"]}}
    data = entry.get("data")
    if not data:
        return out
    system, host = data["system"], data.get("host") or {}
    ifs = [i for i in data.get("interfaces", []) if not (i["descr"] or "").lower().startswith("lo")]
    rates_in = [i["inMbps"] for i in ifs if i.get("inMbps") is not None]
    rates_out = [i["outMbps"] for i in ifs if i.get("outMbps") is not None]
    out.update({
        "sysName": system.get("sysName"), "sysDescr": system.get("sysDescr"),
        "uptime": uptime_to_string(system["sysUpTime"]) if system.get("sysUpTime") is not None else None,
        "cpu": host.get("cpuAvg"),
        "memory": host["memory"][0]["usedPct"] if host.get("memory") else None,
        "diskMaxPct": max((d["usedPct"] for d in host.get("disks", []) if d["usedPct"] is not None), default=None),
        "traffic_in": round(sum(rates_in), 2) if rates_in else None,
        "traffic_out": round(sum(rates_out), 2) if rates_out else None,
        "interfacesUp": sum(1 for i in ifs if i["status"] == "up"),
        "interfacesTotal": len(ifs),
        "responseMs": data.get("responseMs"),
    })
    return out


def public_device(device: dict) -> dict:
    """Cópia segura para a API/templates: telemetria SNMP mesclada e community oculta."""
    out = dict(device)
    cfg = snmp_config(device)
    if isinstance(device.get("snmp"), dict):
        out["snmp"] = {**device["snmp"], "community": "***" if device["snmp"].get("community") else None}
    if cfg:
        entry = get_result(device["id"])
        out.update(_summary(entry) if entry else {"snmpStatus": {"ok": None, "fresh": False, "ageSeconds": None,
                                                                   "error": None}})
    return out


def get_status() -> dict:
    with _lock:
        cycle = dict(_cycle)
        polled = len(_results)
        failing = sum(1 for r in _results.values() if not r["ok"])
    return {"enabled": settings.snmp_poller_enabled, "running": _thread is not None and _thread.is_alive(),
            "intervalSeconds": settings.snmp_poll_interval, "maxWorkers": settings.snmp_poll_max_workers,
            "devicesWithResult": polled, "devicesFailing": failing, **cycle}
