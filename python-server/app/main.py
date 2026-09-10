from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import trap_engine
from .config import ALLOWED_ORIGINS
from .routers import (
    alerts, backups, clients, device, devices, history, maintenances,
    monitoring_params, pages, rules, settings, status, topology, traps,
)

# Resolvidos a partir do arquivo, não do diretório de trabalho do processo —
# assim `static/`/`templates/` são encontrados independente de onde o
# `uvicorn app.main:app` é lançado (localmente ou no Railway).
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="SINAPSE Mock Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"ok": False, "error": "Requisição inválida", "detail": exc.errors()})


# ── Páginas (Jinja2) ────────────────────────────────────────────────────────
app.include_router(pages.router)

# ── API ───────────────────────────────────────────────────────────────────
app.include_router(status.router)
app.include_router(device.router)
app.include_router(traps.router)
app.include_router(topology.router)
app.include_router(clients.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(rules.router)
app.include_router(monitoring_params.router)
app.include_router(maintenances.router)
app.include_router(history.router)
app.include_router(backups.router)
app.include_router(settings.router)


@app.on_event("startup")
def _startup():
    trap_engine.generate_startup_traps()
    print("")
    print("SINAPSE — Mock SNMP Server (Python/FastAPI)")
    print("Modo: Mock (dados simulados)")
    print("Topografia: 3 OLTs -> 8 Portas -> 18 ONUs")
