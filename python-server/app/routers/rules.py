from fastapi import APIRouter, Body, HTTPException

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/rules")
def list_rules():
    return ok(data=state.get_rules())


@router.post("/api/rules")
def create_rule(body: dict = Body(...)):
    return ok(data=state.add_rule(body))


@router.put("/api/rules/{rule_id}")
def edit_rule(rule_id: int, body: dict = Body(...)):
    updated = state.update_rule(rule_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Não encontrada")
    return ok(data=updated)


@router.put("/api/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int):
    return ok(data=state.toggle_rule(rule_id))


@router.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int):
    state.remove_rule(rule_id)
    return ok(message="Removida")
