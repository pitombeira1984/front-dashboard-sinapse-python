from fastapi import APIRouter, HTTPException

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/backups")
def list_backups():
    return ok(data=state.get_backups())


@router.post("/api/backups")
def create_backup():
    return ok(data=state.create_backup())


@router.post("/api/backups/{backup_id}/restore")
def restore_backup(backup_id: int):
    result = state.restore_backup(backup_id)
    if not result:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return ok(message="Restaurado")


@router.delete("/api/backups/{backup_id}")
def delete_backup(backup_id: int):
    state.remove_backup(backup_id)
    return ok(message="Removido")
