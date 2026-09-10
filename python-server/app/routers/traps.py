from fastapi import APIRouter, Body, HTTPException

from .. import trap_engine

router = APIRouter()


@router.get("/api/traps")
def list_traps(type: str | None = None, severity: str | None = None,
               unacknowledged: bool | None = None, limit: int | None = None):
    filters = {}
    if type:
        filters["type"] = type
    if severity:
        filters["severity"] = severity
    if unacknowledged:
        filters["unacknowledged"] = True
    result = trap_engine.get_traps(filters)
    if limit:
        result = result[:limit]
    return {"ok": True, "count": len(result), "data": result}


@router.get("/api/traps/stats")
def traps_stats():
    return {"ok": True, "data": trap_engine.get_trap_stats()}


@router.get("/api/traps/types")
def traps_types():
    return {"ok": True, "data": trap_engine.get_trap_types()}


@router.put("/api/traps/acknowledge")
def acknowledge(body: dict = Body(...)):
    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids deve ser um array")
    trap_engine.acknowledge_traps(ids)
    return {"ok": True, "message": f"{len(ids)} trap(s) reconhecido(s)"}


@router.put("/api/traps/acknowledge-all")
def acknowledge_all():
    trap_engine.acknowledge_all_traps()
    return {"ok": True, "message": "Todos os traps reconhecidos"}
