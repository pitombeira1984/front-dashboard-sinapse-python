# ===== SINAPSE — TRAP ENGINE =====
# Módulo responsável por gerar, armazenar e expor SNMP Traps simulados.
#
# Tipos suportados (conforme RFC 1157 + MIBs proprietários):
#   coldStart          — OID 1.3.6.1.6.3.1.1.5.1
#   warmStart          — OID 1.3.6.1.6.3.1.1.5.2
#   linkDown           — OID 1.3.6.1.6.3.1.1.5.3
#   linkUp             — OID 1.3.6.1.6.3.1.1.5.4
#   authenticationFail — OID 1.3.6.1.6.3.1.1.5.5
#   opticalDegradation — OID 1.3.6.1.4.1.2011.6.128.1.1.2.51 (Huawei)
#   highTemperature    — OID 1.3.6.1.4.1.2011.6.128.1.1.2.52 (Huawei)
#   highCPU            — OID 1.3.6.1.2.1.25.3.3.1.2
import random
import time

from . import optical_thresholds
from .formatting import now_str_seconds

TRAP_TYPES = {
    "coldStart": {"oid": "1.3.6.1.6.3.1.1.5.1", "name": "coldStart", "label": "Cold Start",
                  "description": "Equipamento inicializou do zero (cold boot)", "severity": "warning",
                  "icon": "fa-power-off", "rfc": "RFC 1157 — Generic Trap 0"},
    "warmStart": {"oid": "1.3.6.1.6.3.1.1.5.2", "name": "warmStart", "label": "Warm Start",
                  "description": "Equipamento reiniciou sem perda de configuração", "severity": "info",
                  "icon": "fa-redo", "rfc": "RFC 1157 — Generic Trap 1"},
    "linkDown": {"oid": "1.3.6.1.6.3.1.1.5.3", "name": "linkDown", "label": "Link Down",
                 "description": "Interface de rede ficou inativa", "severity": "critical",
                 "icon": "fa-unlink", "rfc": "RFC 1157 — Generic Trap 2"},
    "linkUp": {"oid": "1.3.6.1.6.3.1.1.5.4", "name": "linkUp", "label": "Link Up",
               "description": "Interface de rede voltou a ficar ativa", "severity": "info",
               "icon": "fa-link", "rfc": "RFC 1157 — Generic Trap 3"},
    "authenticationFailure": {"oid": "1.3.6.1.6.3.1.1.5.5", "name": "authenticationFailure",
                               "label": "Authentication Failure",
                               "description": "Falha de autenticação SNMP — community string incorreta",
                               "severity": "critical", "icon": "fa-shield-alt", "rfc": "RFC 1157 — Generic Trap 4"},
    "opticalDegradation": {"oid": "1.3.6.1.4.1.2011.6.128.1.1.2.51", "name": "opticalDegradation",
                            "label": "Optical Degradation",
                            "description": "Sinal óptico RxPower abaixo do limiar mínimo", "severity": "critical",
                            "icon": "fa-satellite-dish", "rfc": "Huawei Enterprise MIB — hwGponOntOpticalInfo"},
    "highTemperature": {"oid": "1.3.6.1.4.1.2011.6.128.1.1.2.52", "name": "highTemperature",
                         "label": "High Temperature",
                         "description": "Temperatura interna acima do limite operacional", "severity": "warning",
                         "icon": "fa-thermometer-full", "rfc": "Huawei Enterprise MIB — hwGponOntTemperature"},
    "highCPU": {"oid": "1.3.6.1.2.1.25.3.3.1.2", "name": "highCPU", "label": "High CPU Load",
                "description": "Utilização de CPU acima do limite configurado", "severity": "warning",
                "icon": "fa-microchip", "rfc": "HOST-RESOURCES-MIB — hrProcessorLoad"},
}

trap_state = {
    "queue": [],
    "counters": {k: 0 for k in TRAP_TYPES},
    "ifStatus": {"eth0": "up", "eth1": "up", "eth2": "down", "wlan0": "up", "wlan1": "up"},
    "flags": {
        "opticalAlarmActive": False,
        "temperatureAlarmActive": False,
        "cpuAlarmActive": False,
        "lastAuthFailAt": 0,
        "coldStartSent": False,
        "onuStatus": {},
        "onuOptical": {},
    },
}


def make_trap(trap_type: str, device: str | None = None, varbinds: dict | None = None) -> dict | None:
    definition = TRAP_TYPES.get(trap_type)
    if not definition:
        return None
    varbinds = varbinds or {}

    trap_state["counters"][trap_type] = trap_state["counters"].get(trap_type, 0) + 1

    trap = {
        "id": f"trap-{trap_type}-{int(time.time() * 1000)}",
        "type": trap_type,
        "oid": definition["oid"],
        "label": definition["label"],
        "description": definition["description"],
        "severity": definition["severity"],
        "icon": definition["icon"],
        "rfc": definition["rfc"],
        "device": device or "Home Gateway HG8145X6",
        "agentAddr": "192.168.1.1",
        "community": "public",
        "timestamp": now_str_seconds(),
        "time": now_str_seconds(),
        "varbinds": varbinds,
        "acknowledged": False,
    }

    trap_state["queue"].insert(0, trap)
    if len(trap_state["queue"]) > 200:
        trap_state["queue"].pop()

    return trap


def generate_startup_traps() -> None:
    """Fila começa vazia — traps são gerados apenas quando anomalias reais ocorrem.
    coldStart e linkUp de boot são omitidos intencionalmente para não poluir a lista
    com eventos técnicos de inicialização do servidor mock."""
    trap_state["flags"]["coldStartSent"] = True


def evaluate_traps(snapshot: dict) -> None:
    optical = snapshot["optical"]
    system = snapshot["system"]
    interfaces = snapshot["interfaces"]
    anomaly = snapshot.get("anomaly")
    flags = trap_state["flags"]

    # ── Trap Óptico ───────────────────────────────────────────────────────────
    if optical["rxPower"] < -22 and not flags["opticalAlarmActive"]:
        flags["opticalAlarmActive"] = True
        make_trap("opticalDegradation", snapshot["device"]["name"], {
            "hwGponOntRxPower": optical["rxPowerRaw"],
            "hwGponOntTxPower": optical["txPowerRaw"],
            "rxPowerDbm": optical["rxPower"],
            "thresholdMin": optical["thresholds"]["rxMin"],
            "ber": optical["ber"],
            "opticalStatus": optical["status"],
        })
    elif optical["rxPower"] >= -20 and flags["opticalAlarmActive"]:
        flags["opticalAlarmActive"] = False
        make_trap("linkUp", snapshot["device"]["name"], {
            "ifDescr": "WAN — PON Uplink (Sinal óptico recuperado)",
            "rxPowerDbm": optical["rxPower"],
            "opticalStatus": "online",
        })

    # ── Trap Temperatura ──────────────────────────────────────────────────────
    if system["temperature"] > 50 and not flags["temperatureAlarmActive"]:
        flags["temperatureAlarmActive"] = True
        make_trap("highTemperature", snapshot["device"]["name"], {
            "temperature": system["temperature"],
            "temperatureRaw": round(system["temperature"] * 256),
            "thresholdCelsius": 70,
            "hwGponOntLocation": snapshot["device"]["location"],
        })
    elif system["temperature"] <= 45 and flags["temperatureAlarmActive"]:
        flags["temperatureAlarmActive"] = False

    # ── Trap CPU ──────────────────────────────────────────────────────────────
    if system["cpu"] > 70 and not flags["cpuAlarmActive"]:
        flags["cpuAlarmActive"] = True
        make_trap("highCPU", snapshot["device"]["name"], {
            "hrProcessorLoad": system["cpu"],
            "memPercent": system["memPercent"],
            "threshold": 80,
        })
    elif system["cpu"] <= 60 and flags["cpuAlarmActive"]:
        flags["cpuAlarmActive"] = False

    # ── Trap LinkDown/LinkUp (mudança de status de interface) ─────────────────
    for iface in interfaces:
        prev = trap_state["ifStatus"].get(iface["name"])
        curr = iface["status"]
        if prev and prev != curr:
            trap_state["ifStatus"][iface["name"]] = curr
            make_trap("linkDown" if curr == "down" else "linkUp", snapshot["device"]["name"], {
                "ifIndex": iface["index"],
                "ifDescr": iface["descr"],
                "ifType": iface["type"],
                "ifAdminStatus": curr,
                "ifOperStatus": curr,
                "ifSpeed": iface["speed"],
            })

    # ── Trap authenticationFailure (ocasional — simula tentativa inválida) ────
    now = time.time() * 1000
    if now - flags["lastAuthFailAt"] > 30000 and random.random() < 0.08:
        flags["lastAuthFailAt"] = now
        make_trap("authenticationFailure", snapshot["device"]["name"], {
            "community": "private",
            "sourceIp": f"192.168.1.{random.randint(1, 254)}",
            "snmpVersion": "v2c",
        })

    # ── Trap coldStart/warmStart via anomalia ─────────────────────────────────
    if anomaly and anomaly.get("type") == "cpuSpike" and random.random() < 0.15:
        make_trap("warmStart", snapshot["device"]["name"], {
            "reason": "Processo watchdog reiniciou o módulo de gerência",
            "sysUpTime": snapshot["device"]["uptimeTicks"],
        })

    # ── Traps por ONU: linkDown/linkUp + degradação óptica individual ─────────
    onus = snapshot.get("topology", {}).get("onus", [])
    for onu in onus:
        prev_status = flags["onuStatus"].get(onu["id"])
        curr_status = onu["status"]

        if prev_status is not None and prev_status != curr_status:
            if curr_status == "offline":
                make_trap("linkDown", f"ONU — {onu['apt']}", {
                    "ifDescr": f"GPON {onu['port']} — {onu['client']}",
                    "ifType": "gpon-onu",
                    "onuSerial": onu["serial"],
                    "onuIp": onu["ip"],
                    "gponPort": onu["gponPort"],
                    "lastSeen": onu["lastSeen"],
                })
            else:
                make_trap("linkUp", f"ONU — {onu['apt']}", {
                    "ifDescr": f"GPON {onu['port']} — {onu['client']} (reconectado)",
                    "ifType": "gpon-onu",
                    "onuSerial": onu["serial"],
                    "onuIp": onu["ip"],
                    "gponPort": onu["gponPort"],
                })
        flags["onuStatus"][onu["id"]] = curr_status

        if curr_status == "online":
            prev_alarm = flags["onuOptical"].get(onu["id"], False)
            rx_level = optical_thresholds.level("rxPower", onu["rxPower"], onu.get("ponMode"))
            is_alarm = rx_level in ("warn", "crit")
            if is_alarm and not prev_alarm:
                make_trap("opticalDegradation", f"ONU — {onu['apt']}", {
                    "hwGponOntRxPower": round(onu["rxPower"] * 100),
                    "rxPowerDbm": onu["rxPower"],
                    "thresholdMin": optical_thresholds.OPTICAL_THRESHOLDS[
                        optical_thresholds.profile_name(onu.get("ponMode"))]["rxPower"]["warnLow"],
                    "opticalStatus": "critical" if rx_level == "crit" else "degraded",
                    "ponMode": onu.get("ponMode"),
                    "onuSerial": onu["serial"],
                    "onuClient": onu["client"],
                    "onuIp": onu["ip"],
                    "gponPort": onu["gponPort"],
                })
            elif not is_alarm and prev_alarm:
                make_trap("linkUp", f"ONU — {onu['apt']}", {
                    "ifDescr": f"GPON {onu['port']} — Sinal óptico recuperado",
                    "rxPowerDbm": onu["rxPower"],
                    "onuSerial": onu["serial"],
                    "opticalStatus": "online",
                })
            flags["onuOptical"][onu["id"]] = is_alarm
        else:
            flags["onuOptical"][onu["id"]] = False


# ── API pública ───────────────────────────────────────────────────────────────
def get_traps(filters: dict | None = None) -> list:
    filters = filters or {}
    traps = list(trap_state["queue"])
    if filters.get("type"):
        traps = [t for t in traps if t["type"] == filters["type"]]
    if filters.get("severity"):
        traps = [t for t in traps if t["severity"] == filters["severity"]]
    if filters.get("unacknowledged"):
        traps = [t for t in traps if not t["acknowledged"]]
    return traps


def acknowledge_traps(ids: list) -> None:
    ids_set = set(ids)
    for t in trap_state["queue"]:
        if t["id"] in ids_set:
            t["acknowledged"] = True


def acknowledge_all_traps() -> None:
    for t in trap_state["queue"]:
        t["acknowledged"] = True


def get_trap_stats() -> dict:
    queue = trap_state["queue"]
    return {
        "total": len(queue),
        "unacknowledged": sum(1 for t in queue if not t["acknowledged"]),
        "critical": sum(1 for t in queue if t["severity"] == "critical" and not t["acknowledged"]),
        "warning": sum(1 for t in queue if t["severity"] == "warning" and not t["acknowledged"]),
        "counters": dict(trap_state["counters"]),
        "lastTrap": queue[0] if queue else None,
    }


def get_trap_types() -> dict:
    return TRAP_TYPES
