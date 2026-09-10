import time
from datetime import datetime, timezone

from fastapi import APIRouter

from ..responses import ok

router = APIRouter()
_started_at = time.time()


@router.get("/api/status")
def get_status():
    return ok(
        server="SINAPSE Mock Server",
        version="1.1.0",
        mode="mock",
        uptime=time.time() - _started_at,
        timestamp=datetime.now(timezone.utc).isoformat(),
        message="Servidor mock ativo. Substitua mock_engine.py por um agente SNMP real quando o hardware estiver disponível.",
    )
