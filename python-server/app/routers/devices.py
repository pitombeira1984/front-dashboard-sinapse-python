from fastapi import APIRouter, Body, HTTPException

from .. import discovery, mock_engine, snmp_poller, state
from ..responses import ok

router = APIRouter()


def _with_snmp(body: dict, current: dict | None = None) -> dict:
    """Normaliza o campo `snmp` do corpo. Community "***" (valor mascarado devolvido
    pela API) mantém a community já cadastrada."""
    if "snmp" not in body:
        return body
    raw = body["snmp"]
    if isinstance(raw, dict) and raw.get("community") == "***" and current and isinstance(current.get("snmp"), dict):
        raw = {**raw, "community": current["snmp"].get("community")}
    try:
        return {**body, "snmp": snmp_poller.normalize_config(raw)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"snmp inválido: {exc}")


def _find_or_404(device_id: int) -> dict:
    device = state.find_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return device


@router.get("/api/devices")
def list_devices():
    return ok(data=[snmp_poller.public_device(d) for d in state.get_devices()])


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
    return ok(data=snmp_poller.public_device(state.add_device(_with_snmp(body))))


@router.put("/api/devices/{device_id}")
def edit_device(device_id: int, body: dict = Body(...)):
    updated = state.update_device(device_id, _with_snmp(body, _find_or_404(device_id)))
    return ok(data=snmp_poller.public_device(updated))


@router.delete("/api/devices/{device_id}")
def delete_device(device_id: int):
    state.remove_device(device_id)
    return ok(message="Removido")


# ── Telemetria SNMP real (app/snmp_poller.py) ─────────────────────────────────
@router.get("/api/devices/{device_id}/snmp")
def get_device_snmp(device_id: int):
    device = _find_or_404(device_id)
    if not snmp_poller.snmp_config(device):
        raise HTTPException(status_code=404, detail="Dispositivo sem SNMP configurado")
    return ok(data={"device": snmp_poller.public_device(device), "result": snmp_poller.get_result(device_id)})


@router.post("/api/devices/{device_id}/snmp/poll")
def poll_device_snmp(device_id: int):
    """Leitura imediata, fora do ciclo — usada pelo botão "Testar Conexão"."""
    device = _find_or_404(device_id)
    if not snmp_poller.snmp_config(device):
        raise HTTPException(status_code=404, detail="Dispositivo sem SNMP configurado")
    snmp_poller.poll_now(device)
    return ok(data={"device": snmp_poller.public_device(device), "result": snmp_poller.get_result(device_id)})


@router.get("/api/snmp-poller/status")
def snmp_poller_status():
    return ok(data=snmp_poller.get_status())


# ── Adicionar OLT/ONU ao monitoramento ─────────────────────────────────────────
@router.post("/api/olts")
def create_olt(body: dict = Body(...)):
    if not body.get("ip"):
        raise HTTPException(status_code=400, detail="ip obrigatório")
    return ok(data=snmp_poller.public_device(mock_engine.add_olt(_with_snmp(body))))


@router.post("/api/onus")
def create_onu(body: dict = Body(...)):
    if not body.get("gponPort"):
        raise HTTPException(status_code=400, detail="gponPort obrigatório")
    return ok(data=mock_engine.add_onu(body))
