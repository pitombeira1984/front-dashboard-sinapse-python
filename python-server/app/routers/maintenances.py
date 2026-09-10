from fastapi import APIRouter, Body

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/maintenances")
def list_maintenances():
    return ok(data=state.get_maintenances())


@router.post("/api/maintenances")
def create_maintenance(body: dict = Body(...)):
    return ok(data=state.add_maintenance(body))


@router.delete("/api/maintenances/{maintenance_id}")
def delete_maintenance(maintenance_id: int):
    state.remove_maintenance(maintenance_id)
    return ok(message="Removido")
