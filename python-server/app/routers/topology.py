from fastapi import APIRouter, HTTPException

from .. import mock_engine
from ..responses import ok
from ..snapshot_cache import get_cached_snapshot

router = APIRouter()


@router.get("/api/topology")
def get_topology():
    return ok(data=get_cached_snapshot()["topology"])


@router.get("/api/onus")
def list_onus(port: str | None = None):
    return ok(data=mock_engine.get_onus(port))


@router.get("/api/onus/{onu_id}")
def get_onu(onu_id: int):
    onu = next((o for o in mock_engine.get_onus() if o["id"] == onu_id), None)
    if not onu:
        raise HTTPException(status_code=404, detail="ONU não encontrada")
    return ok(data=onu)


@router.get("/api/gpon/ports")
def get_gpon_ports():
    return ok(data=mock_engine.get_gpon_ports())


@router.get("/api/gpon/kpis")
def get_gpon_kpis():
    return ok(data=get_cached_snapshot()["gpon"])


@router.get("/api/olts")
def list_olts():
    return ok(data=mock_engine.OLTS)


@router.get("/api/olts/bandwidth")
def get_olts_bandwidth():
    get_cached_snapshot()  # garante tick antes de ler snmp_state["olts"]
    return ok(data=mock_engine.get_olts_bandwidth())
