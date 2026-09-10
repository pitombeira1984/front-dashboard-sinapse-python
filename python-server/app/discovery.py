"""Motor de descoberta automática de rede (Devices -> Escanear Rede).

Para cada host de um range CIDR, tenta um GET SNMP de sysDescr + sysObjectID
(fingerprint) e/ou um ping ICMP (liveness), classificando o dispositivo via
app.oids.VENDOR_PROFILES. Reaproveita o mesmo padrão pysnmp.hlapi usado em
tools/snmp_test.py, mas com uma única community configurada (sem brute-force)
e em paralelo (ThreadPoolExecutor), já que aqui é preciso varrer uma faixa
inteira, não testar um único IP manualmente.
"""
from __future__ import annotations

import ipaddress
import platform
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from pysnmp.hlapi import (
    CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine,
    UdpTransportTarget, getCmd,
)

from .config import settings
from .oids import VENDOR_PROFILES, classify_vendor

SYS_DESCR_OID = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID_OID = "1.3.6.1.2.1.1.2.0"


def local_network_range() -> dict:
    """Palpite de faixa CIDR pra pré-preencher o campo "Faixa de IP" da UI, pra
    quem não sabe de cabeça a sub-rede da própria rede. Descobre o IP local
    através de uma rota de saída (truque clássico: um "connect" UDP não chega
    a enviar nada, só força o SO a resolver por qual interface ele sairia) e
    assume máscara /24, o caso mais comum em LANs domésticas/pequenas — não
    há como saber a máscara real sem depender de uma lib externa (netifaces/
    psutil, fora do requirements.txt). É só um ponto de partida editável, não
    uma garantia."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
    except OSError:
        local_ip = "127.0.0.1"

    network = ipaddress.ip_interface(f"{local_ip}/24").network
    return {"ip": local_ip, "range": str(network)}


def local_network_ranges() -> list[dict]:
    """Todas as sub-redes locais dignas de escanear de uma vez — não só a
    "principal" (`local_network_range`). Máquinas com mais de uma interface
    (LAN real + adaptadores virtuais de VPN/WSL/Docker) têm mais de um IP;
    descobertos via `socket.gethostbyname_ex` (funciona no Windows sem
    depender de netifaces/psutil, que não estão no requirements.txt — em
    hosts Linux com /etc/hosts atípico pode não retornar nada além do IP
    principal, daí o fallback abaixo). Sempre inclui `127.0.0.0/24`: é onde
    os dispositivos simulados do laboratório (ver tools/lab/) costumam ficar
    publicados. Deduplicado por rede /24."""
    primary = local_network_range()
    ips = [primary["ip"]]
    try:
        _, _, extra_ips = socket.gethostbyname_ex(socket.gethostname())
        ips.extend(extra_ips)
    except OSError:
        pass

    seen: dict[str, str] = {}
    for ip in ips:
        if ip.startswith("127."):
            continue
        network = str(ipaddress.ip_interface(f"{ip}/24").network)
        seen.setdefault(network, ip)

    ranges = [{"ip": ip, "range": rng} for rng, ip in seen.items()]
    ranges.append({"ip": "127.0.0.1", "range": "127.0.0.0/24"})
    return ranges


def _expand_range(range_str: str) -> list[str]:
    try:
        network = ipaddress.ip_network(range_str, strict=False)
    except ValueError as exc:
        raise ValueError(f"Faixa de IP inválida: {range_str}") from exc
    return [str(ip) for ip in network.hosts()]


def _expand_ranges(ranges_str: str) -> list[str]:
    """Aceita uma ou mais faixas CIDR separadas por vírgula — permite escanear
    a LAN real e o loopback do laboratório (ou qualquer outra combinação de
    redes) numa passada só, em vez de uma varredura por vez."""
    parts = [p.strip() for p in ranges_str.split(",") if p.strip()]
    if not parts:
        raise ValueError("Faixa de IP inválida: vazia")

    hosts: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for ip in _expand_range(part):
            if ip not in seen:
                seen.add(ip)
                hosts.append(ip)

    if len(hosts) > settings.scan_max_hosts:
        raise ValueError(
            f"Faixa muito ampla ({len(hosts)} hosts no total) — máximo permitido é "
            f"{settings.scan_max_hosts}. Use faixas menores ou escaneie menos redes de uma vez."
        )
    return hosts


def _snmp_probe(ip: str) -> dict | None:
    """GET de sysDescr + sysObjectID num único round-trip. Retorna None se o
    host não respondeu SNMP dentro do timeout/community configurados."""
    iterator = getCmd(
        SnmpEngine(),
        CommunityData(settings.snmp_community, mpModel=1),
        UdpTransportTarget((ip, 161), timeout=settings.snmp_timeout, retries=settings.snmp_retries),
        ContextData(),
        ObjectType(ObjectIdentity(SYS_DESCR_OID)),
        ObjectType(ObjectIdentity(SYS_OBJECT_ID_OID)),
    )
    error_indication, error_status, _error_index, var_binds = next(iterator)
    if error_indication or error_status or len(var_binds) < 2:
        return None
    return {"sysDescr": str(var_binds[0][1]), "sysObjectId": str(var_binds[1][1])}


def _ping(ip: str) -> float | None:
    """Ping via utilitário do SO (sem precisar de socket raw/privilégio admin).
    Retorna latência aproximada em ms, ou None se não respondeu."""
    is_windows = platform.system() == "Windows"
    timeout_ms = max(int(settings.snmp_timeout * 1000), 200)
    cmd = (
        ["ping", "-n", "1", "-w", str(timeout_ms), ip]
        if is_windows
        else ["ping", "-c", "1", "-W", str(max(int(settings.snmp_timeout), 1)), ip]
    )
    start = time.monotonic()
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=settings.snmp_timeout + 1)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return round((time.monotonic() - start) * 1000, 1)


def _unknown_ping_result(ip: str, latency_ms: float) -> dict:
    return {
        "ip": ip, "status": "online", "latency_ms": latency_ms,
        "sysDescr": None, "sysObjectId": None,
        "vendor_key": None, "vendor_label": "Desconhecido — sem SNMP",
        "device_type": "Desconhecido", "suggested_name": f"Dispositivo ({ip})",
        "oid_groups": [],
    }


def _probe_host(ip: str, protocol: str) -> dict | None:
    if protocol == "ping":
        latency_ms = _ping(ip)
        return _unknown_ping_result(ip, latency_ms) if latency_ms is not None else None

    snmp_result = _snmp_probe(ip)
    if snmp_result is None:
        return None

    latency_ms = _ping(ip) if protocol == "both" else None

    vendor_key = classify_vendor(snmp_result["sysDescr"], snmp_result["sysObjectId"])
    profile = VENDOR_PROFILES[vendor_key]
    return {
        "ip": ip, "status": "online", "latency_ms": latency_ms,
        "sysDescr": snmp_result["sysDescr"], "sysObjectId": snmp_result["sysObjectId"],
        "vendor_key": vendor_key, "vendor_label": profile["label"],
        "device_type": profile["device_type"],
        "suggested_name": f"{profile['label']} ({ip})",
        "oid_groups": profile["oid_groups"],
    }


def scan_range(range_str: str, protocol: str = "snmp") -> list[dict]:
    if protocol not in ("ping", "snmp", "both"):
        raise ValueError(f"Protocolo inválido: {protocol}")

    hosts = _expand_ranges(range_str)
    if not hosts:
        return []

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=settings.scan_max_workers) as pool:
        futures = {pool.submit(_probe_host, ip, protocol): ip for ip in hosts}
        for future in as_completed(futures):
            device = future.result()
            if device is not None:
                results.append(device)

    results.sort(key=lambda d: tuple(int(octet) for octet in d["ip"].split(".")))
    return results
