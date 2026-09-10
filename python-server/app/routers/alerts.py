from fastapi import APIRouter, Body

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/alerts/all")
def list_all_alerts():
    return ok(data=state.get_alerts())


@router.post("/api/alerts/add")
def add_alert(body: dict = Body(...)):
    return ok(data=state.add_alert(body))


@router.put("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    state.resolve_alert(alert_id)
    return ok(message="Resolvido")


@router.delete("/api/alerts/{alert_id}")
def delete_alert(alert_id: int):
    state.ignore_alert(alert_id)
    return ok(message="Removido")
