from fastapi import APIRouter, Body, HTTPException

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/monitoring-params")
def list_params():
    return ok(data=state.get_monitoring_params())


@router.post("/api/monitoring-params")
def create_param(body: dict = Body(...)):
    return ok(data=state.add_monitoring_param(body))


@router.put("/api/monitoring-params/{param_id}")
def edit_param(param_id: int, body: dict = Body(...)):
    updated = state.update_monitoring_param(param_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return ok(data=updated)


@router.put("/api/monitoring-params/{param_id}/toggle")
def toggle_param(param_id: int):
    return ok(data=state.toggle_monitoring_param(param_id))


@router.delete("/api/monitoring-params/{param_id}")
def delete_param(param_id: int):
    state.remove_monitoring_param(param_id)
    return ok(message="Removido")
