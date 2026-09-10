from datetime import datetime

from fastapi import APIRouter

from .. import mock_engine, state
from ..oids import OIDs
from ..responses import ok
from ..snapshot_cache import get_cached_snapshot

router = APIRouter()


@router.get("/api/device")
def get_device():
    return ok(data=get_cached_snapshot())


@router.get("/api/device/optical")
def get_device_optical():
    snap = get_cached_snapshot()
    return ok(device=snap["device"]["name"], data=snap["optical"])


@router.get("/api/device/system")
def get_device_system():
    snap = get_cached_snapshot()
    return ok(device=snap["device"]["name"], data=snap["system"])


@router.get("/api/device/wifi")
def get_device_wifi():
    snap = get_cached_snapshot()
    return ok(device=snap["device"]["name"], data=snap["wifi"])


@router.get("/api/device/interfaces")
def get_device_interfaces():
    snap = get_cached_snapshot()
    return ok(device=snap["device"]["name"], data=snap["interfaces"])


@router.get("/api/device/history")
def get_device_history():
    return ok(data=mock_engine.get_history())


@router.get("/api/metrics/live")
def get_metrics_live(port: str | None = None):
    snap = get_cached_snapshot()

    if port:
        port_onus = mock_engine.get_onus(port)
        online_onus = [o for o in port_onus if o["status"] == "online"]
        onus_online = len(online_onus)
        onus_total = len(port_onus)
        avg_rx_power = round(sum(o["rxPower"] for o in online_onus) / len(online_onus), 2) if online_onus else None
        avg_latency = round(sum(o["latency"] for o in online_onus) / len(online_onus), 1) if online_onus else None
        availability = round((onus_online / onus_total) * 100, 2) if onus_total else 100
    else:
        gpon = snap.get("gpon", {})
        onus_online = gpon.get("onusOnline", 0)
        onus_total = gpon.get("onusTotal", 8)
        avg_rx_power = gpon.get("avgRxPower", 0)
        avg_latency = gpon.get("avgLatency", 0)
        availability = gpon.get("availability", 100)

    interfaces = snap["interfaces"]
    data = {
        "timestamp": snap["timestamp"],
        "cpu": snap["system"]["cpu"],
        "memPercent": snap["system"]["memPercent"],
        "temperature": snap["system"]["temperature"],
        "rxPower": snap["optical"]["rxPower"],
        "txPower": snap["optical"]["txPower"],
        "opticalStatus": snap["optical"]["status"],
        "wanInRate": interfaces[0]["inRate"] if interfaces else 0,
        "wanOutRate": interfaces[0]["outRate"] if interfaces else 0,
        "wifiClients": snap["wifi"]["band24"]["clients"] + snap["wifi"]["band5"]["clients"],
        "onusOnline": onus_online,
        "onusTotal": onus_total,
        "avgRxPower": avg_rx_power,
        "avgLatency": avg_latency,
        "availability": availability,
        "uptime": snap["device"]["uptime"],
        "anomaly": snap["anomaly"],
    }

    # Avaliação server-side dos Parâmetros de Monitoramento configurados pelo operador
    # (equivalente ao antigo evaluateMonitoringParams do navegador).
    state.evaluate_monitoring_params(data)

    return ok(data=data)


@router.get("/api/alerts")
def get_computed_alerts():
    snap = get_cached_snapshot()
    alerts = []

    if snap["optical"]["rxPower"] < snap["optical"]["thresholds"]["rxMin"] + 3:
        alerts.append({
            "id": f"optical-rx-{int(datetime.now().timestamp() * 1000)}",
            "severity": "critical" if snap["optical"]["rxPower"] < snap["optical"]["thresholds"]["rxMin"] else "warning",
            "title": "Sinal Óptico Baixo",
            "description": f"RxPower: {snap['optical']['rxPower']} dBm (mínimo: {snap['optical']['thresholds']['rxMin']} dBm)",
            "device": snap["device"]["name"],
            "oid": OIDs["gpon"]["onuRxPower"],
            "value": snap["optical"]["rxPowerRaw"],
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    if snap["system"]["cpu"] > 80:
        alerts.append({
            "id": f"cpu-{int(datetime.now().timestamp() * 1000)}",
            "severity": "critical" if snap["system"]["cpu"] > 90 else "warning",
            "title": "CPU Elevada",
            "description": f"CPU em {snap['system']['cpu']}%",
            "device": snap["device"]["name"],
            "oid": OIDs["host"]["hrProcessorLoad"],
            "value": snap["system"]["cpu"],
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    if snap["system"]["temperature"] > 70:
        alerts.append({
            "id": f"temp-{int(datetime.now().timestamp() * 1000)}",
            "severity": "warning",
            "title": "Temperatura Elevada",
            "description": f"Sistema em {snap['system']['temperature']:.1f}°C",
            "device": snap["device"]["name"],
            "oid": OIDs["gpon"]["onuTemperature"],
            "value": round(snap["system"]["temperature"] * 256),
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    if snap["anomaly"]:
        alerts.append({
            "id": f"anomaly-{snap['anomaly']['startedAt']}",
            "severity": snap["anomaly"]["severity"],
            "title": "Anomalia Detectada",
            "description": snap["anomaly"]["description"],
            "device": snap["device"]["name"],
            "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    return ok(count=len(alerts), data=alerts)


@router.get("/api/oids")
def get_oids():
    return ok(data=OIDs)
