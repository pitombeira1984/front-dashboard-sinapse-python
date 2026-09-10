from fastapi import APIRouter, HTTPException

from .. import mock_engine
from ..responses import ok

router = APIRouter()


@router.get("/api/clients")
def list_clients():
    return ok(data=mock_engine.get_clients())


@router.get("/api/clients/{client_id}")
def get_client(client_id: int):
    client = mock_engine.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return ok(data=client)
