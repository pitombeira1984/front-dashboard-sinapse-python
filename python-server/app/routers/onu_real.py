from fastapi import APIRouter

from .. import onu_web_poller
from ..responses import ok

router = APIRouter()


@router.get("/api/onu-real/status")
def get_onu_real_status():
    return ok(data=onu_web_poller.get_status())
