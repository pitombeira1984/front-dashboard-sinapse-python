from fastapi import APIRouter, Body

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/settings")
def get_settings():
    return ok(data=state.get_settings())


@router.put("/api/settings")
def put_settings(body: dict = Body(...)):
    return ok(data=state.save_settings(body))
