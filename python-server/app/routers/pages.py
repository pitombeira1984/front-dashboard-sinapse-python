import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from .. import mock_engine, onu_web_poller, optical_thresholds, state
from ..snapshot_cache import get_cached_snapshot

router = APIRouter()
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
templates.env.globals["optical_color"] = optical_thresholds.color
templates.env.globals["optical_thresholds"] = optical_thresholds.OPTICAL_THRESHOLDS

# Sufixo ?v= nos /static/*.js|css dos templates: muda a cada start do processo
# (inclusive a cada reload do `--reload`), forçando o navegador a baixar JS/CSS
# novos em vez de reaproveitar uma versão antiga do cache.
_STATIC_VERSION = str(int(time.time()))


def _theme(request: Request) -> str:
    return "light" if request.cookies.get("sinapse_theme") == "light" else "dark"


def _base_ctx(request: Request, page: str, title: str) -> dict:
    return {
        "request": request,
        "current_page": page,
        "page_title": title,
        "theme": _theme(request),
        "settings": state.get_settings(),
        "static_version": _STATIC_VERSION,
    }


@router.get("/")
def dashboard(request: Request):
    snap = get_cached_snapshot()
    default_port = "0/1/0"
    onus = mock_engine.get_onus(default_port)
    olt_device = {
        "id": 100, "name": "OLT Huawei MA5800-X2", "ip": "10.0.1.10", "type": "OLT", "status": "online",
        "cpu": snap["system"]["cpu"], "memory": snap["system"]["memPercent"],
        "temperature": snap["system"]["temperature"],
        "onus_active": snap["gpon"]["onusOnline"], "onus_total": snap["gpon"]["onusTotal"],
    }
    devices = [olt_device] + [{**o, "name": f"ONU — {o['apt']}", "type": "ONU"} for o in onus]
    onu_real = onu_web_poller.get_status()
    ctx = _base_ctx(request, "dashboard", "Dashboard")
    ctx.update({
        "alerts": state.get_alerts(),
        "devices": devices,
        "advanced_metrics": state.get_settings().get("advancedMetrics", True),
        "current_gpon_port": default_port,
        "onu_real": onu_real,
        "onu_real_profile": next((o for o in mock_engine.get_onus() if o["id"] == onu_real["onuId"]), None),
    })
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@router.get("/devices")
def devices_page(request: Request):
    ctx = _base_ctx(request, "devices", "Dispositivos")
    ctx.update({"devices": state.get_devices()})
    return templates.TemplateResponse(request, "devices.html", ctx)


@router.get("/alerts")
def alerts_page(request: Request):
    ctx = _base_ctx(request, "alerts", "Alertas")
    ctx.update({
        "alerts": state.get_alerts(),
        "monitoring_params": state.get_monitoring_params(),
        "param_types": state.MONITORING_PARAM_TYPES,
        "current_alert_filter": "all",
    })
    return templates.TemplateResponse(request, "alerts.html", ctx)


@router.get("/analysis")
def analysis_page(request: Request):
    ctx = _base_ctx(request, "analysis", "Análise")
    ctx.update({
        "maintenances": state.get_maintenances(),
        "active_alerts_count": len([a for a in state.get_alerts() if a["severity"] != "resolved"]),
        "current_time_range": "24h",
    })
    return templates.TemplateResponse(request, "analysis.html", ctx)


@router.get("/settings")
def settings_page(request: Request):
    ctx = _base_ctx(request, "settings", "Configurações")
    ctx.update({"s": state.get_settings(), "current_settings_tab": "general"})
    return templates.TemplateResponse(request, "settings.html", ctx)


@router.get("/history")
def history_page(request: Request):
    ctx = _base_ctx(request, "history", "Histórico")
    ctx.update({
        "history": state.get_app_history(),
        "backups": state.get_backups(),
    })
    return templates.TemplateResponse(request, "history.html", ctx)
