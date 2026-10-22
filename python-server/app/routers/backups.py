from fastapi import APIRouter, HTTPException

from .. import snmp_poller, state
from ..responses import ok

router = APIRouter()


@router.get("/api/backups")
def list_backups():
    # Snapshots incluem os dispositivos — esconde a community SNMP deles também.
    return ok(data=[{**b, "devices": [snmp_poller.public_device(d) for d in b["devices"]]}
                    for b in state.get_backups()])


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
