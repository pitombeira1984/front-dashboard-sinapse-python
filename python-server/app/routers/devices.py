from fastapi import APIRouter, Body, HTTPException

from .. import discovery, mock_engine, state
from ..responses import ok

router = APIRouter()


@router.get("/api/devices")
def list_devices():
    return ok(data=state.get_devices())


# ── Descoberta Automática (scan real de rede + fingerprint SNMP) ──────────────
@router.get("/api/devices/scan/local-ranges")
def get_local_ranges():
    return ok(data=discovery.local_network_ranges())


@router.post("/api/devices/scan")
def scan_devices(body: dict = Body(...)):
    range_ = body.get("range")
    protocol = body.get("protocol", "snmp")
    if not range_:
        raise HTTPException(status_code=400, detail="range obrigatório")
    try:
        results = discovery.scan_range(range_, protocol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ok(data=results)


@router.post("/api/devices")
def create_device(body: dict = Body(...)):
    if not body.get("name") or not body.get("ip"):
        raise HTTPException(status_code=400, detail="name e ip obrigatórios")
    return ok(data=state.add_device(body))


@router.put("/api/devices/{device_id}")
def edit_device(device_id: int, body: dict = Body(...)):
    updated = state.update_device(device_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return ok(data=updated)


@router.delete("/api/devices/{device_id}")
def delete_device(device_id: int):
    state.remove_device(device_id)
    return ok(message="Removido")


# ── Adicionar OLT/ONU ao monitoramento ─────────────────────────────────────────
@router.post("/api/olts")
def create_olt(body: dict = Body(...)):
    if not body.get("ip"):
        raise HTTPException(status_code=400, detail="ip obrigatório")
    return ok(data=mock_engine.add_olt(body))


@router.post("/api/onus")
def create_onu(body: dict = Body(...)):
    if not body.get("gponPort"):
        raise HTTPException(status_code=400, detail="gponPort obrigatório")
    return ok(data=mock_engine.add_onu(body))
