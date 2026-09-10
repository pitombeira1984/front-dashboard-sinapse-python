import io
import json
import time
from csv import writer as csv_writer
from datetime import datetime

from fastapi import APIRouter, Body
from fastapi.responses import HTMLResponse, Response

from .. import state
from ..responses import ok

router = APIRouter()


@router.get("/api/history")
def list_history():
    return ok(data=state.get_app_history())


@router.post("/api/history")
def create_history(body: dict = Body(...)):
    return ok(data=state.add_history(body))


def _filter_by_period(items: list, period: str | None) -> list:
    if not period or period == "all":
        return items
    days = int(period)
    cutoff = time.time() - days * 86400
    result = []
    for item in items:
        try:
            t = datetime.strptime(item.get("time", ""), "%d/%m/%Y %H:%M")
            if t.timestamp() >= cutoff:
                result.append(item)
        except ValueError:
            result.append(item)  # data não reconhecida -> mantém (paridade com o comportamento original)
    return result


@router.get("/api/history/export.csv")
def export_history_csv(period: str | None = None):
    items = _filter_by_period(state.get_app_history(), period)
    buf = io.StringIO()
    buf.write("﻿")
    w = csv_writer(buf)
    w.writerow(["ID", "Data/Hora", "Evento", "Dispositivo", "Duração", "Ação", "Usuário"])
    for item in items:
        w.writerow([item.get("id"), item.get("time"), item.get("event"), item.get("device"),
                    item.get("duration") or "--", item.get("action") or "--", item.get("user") or "Sistema"])
    filename = f"sinapse-historico-{int(time.time() * 1000)}.csv"
    return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                     headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/history/export.json")
def export_history_json(period: str | None = None):
    items = _filter_by_period(state.get_app_history(), period)
    filename = f"sinapse-historico-{int(time.time() * 1000)}.json"
    return Response(content=json.dumps(items, ensure_ascii=False, indent=2), media_type="application/json",
                     headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/history/export.pdf")
def export_history_pdf(period: str | None = None):
    items = _filter_by_period(state.get_app_history(), period)
    rows = "".join(
        f"<tr><td>{i.get('time')}</td><td>{i.get('event')}</td><td>{i.get('device')}</td>"
        f"<td>{i.get('duration') or '--'}</td><td>{i.get('action') or '--'}</td>"
        f"<td>{i.get('user') or 'Sistema'}</td></tr>"
        for i in items
    )
    html = f"""<html><head><title>SINAPSE — Histórico</title>
    <style>body{{font-family:sans-serif;padding:2rem;}}table{{width:100%;border-collapse:collapse;}}
    th,td{{border:1px solid #ccc;padding:0.5rem;text-align:left;}}th{{background:#f0f0f0;}}</style>
    </head><body>
    <h2>SINAPSE — Histórico de Eventos</h2>
    <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    <table>
        <thead><tr><th>Data/Hora</th><th>Evento</th><th>Dispositivo</th><th>Duração</th><th>Ação</th><th>Usuário</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    </body></html>"""
    return HTMLResponse(content=html)
