# ===== ESTADO DA APLICAÇÃO (em memória, reseta ao reiniciar o processo) =====
# Espelha appState do mock-engine.js original, mais duas entidades que antes só
# existiam no localStorage do navegador (monitoring_params, maintenances) — agora
# vivem aqui, no mesmo padrão de todo o resto do estado da aplicação.
import time

from . import mock_engine
from .formatting import now_str_minutes

_last_id = 0


def _gen_id() -> int:
    global _last_id
    candidate = int(time.time() * 1000)
    if candidate <= _last_id:
        candidate = _last_id + 1
    _last_id = candidate
    return candidate


def next_device_id() -> int:
    return _gen_id()


def _seed_devices() -> list:
    devices = [
        {"id": 100, "name": "OLT-01 — MA5800-X2", "ip": "10.0.1.10", "type": "OLT", "status": "online",
         "cpu": 12, "memory": 45, "temperature": 48, "onus_active": 8, "onus_total": 8, "vendor": "Huawei",
         "location": "POP Central", "firmware": "V100R019C10SPC200", "uptime": "0d 00:00:00"},
        {"id": 200, "name": "OLT-02 — ZXA10 C600", "ip": "10.0.2.10", "type": "OLT", "status": "online",
         "cpu": 8, "memory": 38, "temperature": 45, "onus_active": 5, "onus_total": 5, "vendor": "ZTE",
         "location": "POP Bairro Norte", "firmware": "V1.2.3", "uptime": "0d 00:00:00"},
        {"id": 300, "name": "OLT-03 — 7360 FX-4", "ip": "10.0.3.10", "type": "OLT", "status": "online",
         "cpu": 15, "memory": 52, "temperature": 51, "onus_active": 5, "onus_total": 5, "vendor": "Nokia",
         "location": "POP Bairro Sul", "firmware": "FP4R1.2.1", "uptime": "0d 00:00:00"},
    ]
    for p in mock_engine.ONU_PROFILES:
        devices.append({
            "id": p["id"], "name": f"ONU — {p['apt']}", "client": p["client"], "apt": p["apt"],
            "ip": p["ip"], "serial": p["serial"], "model": p["model"], "type": "ONU",
            "status": "online", "rxPower": p["rxBase"], "txPower": 2.5,
            "latency": round(5 + p["distance"] * 3, 1), "distance": f"{p['distance']} km",
            "uptime": "0d 00:00:00", "gponPort": p["gponPort"], "port": f"{p['gponPort']}:{p['portSlot']}",
        })
    return devices


# ── Catálogo de tipos de parâmetro de monitoramento ───────────────────────────
# Espelha TRAP_TYPES do trap_engine.py — mesmos parâmetros, configuráveis pelo operador.
# Mantido também em static/js/alerts.js (mesmo catálogo, para montar o modal no navegador).
MONITORING_PARAM_TYPES = {
    "opticalDegradation": {"label": "Sinal Óptico (RxPower)", "icon": "fa-satellite-dish", "hasThreshold": True,
                            "operator": "<", "unit": "dBm", "defaultThreshold": -24, "defaultSeverity": "critical",
                            "description": "Dispara quando RxPower cai abaixo do limiar. Valor típico de operação: acima de -22 dBm.",
                            "dataKey": "avgRxPower"},
    "highTemperature": {"label": "Temperatura Alta", "icon": "fa-thermometer-full", "hasThreshold": True,
                         "operator": ">", "unit": "°C", "defaultThreshold": 65, "defaultSeverity": "warning",
                         "description": "Dispara quando a temperatura interna ultrapassa o limiar operacional.",
                         "dataKey": "temperature"},
    "highCPU": {"label": "CPU Alta", "icon": "fa-microchip", "hasThreshold": True, "operator": ">", "unit": "%",
                "defaultThreshold": 80, "defaultSeverity": "warning",
                "description": "Dispara quando a utilização de CPU ultrapassa o limiar por tempo configurado.",
                "dataKey": "cpu"},
    "latencyHigh": {"label": "Latência Alta", "icon": "fa-clock", "hasThreshold": True, "operator": ">", "unit": "ms",
                     "defaultThreshold": 50, "defaultSeverity": "warning",
                     "description": "Dispara quando a latência média das ONUs supera o limiar configurado.",
                     "dataKey": "avgLatency"},
    "onuOffline": {"label": "ONU Offline", "icon": "fa-network-wired", "hasThreshold": False,
                   "defaultSeverity": "critical",
                   "description": "Dispara quando uma ou mais ONUs passam para o estado offline.",
                   "dataKey": "onusOnline"},
    "linkDown": {"label": "Link Down", "icon": "fa-unlink", "hasThreshold": False, "defaultSeverity": "critical",
                 "description": "Dispara quando uma interface de rede fica inativa (via SNMP Trap).", "dataKey": None},
    "highBandwidth": {"label": "Saturação de Banda", "icon": "fa-tachometer-alt", "hasThreshold": True,
                       "operator": ">", "unit": "%", "defaultThreshold": 85, "defaultSeverity": "warning",
                       "description": "Dispara quando a utilização de banda supera o limiar configurado.",
                       "dataKey": "bandwidthPercent"},
    "authenticationFailure": {"label": "Falha de Autenticação SNMP", "icon": "fa-shield-alt", "hasThreshold": False,
                               "defaultSeverity": "critical",
                               "description": "Dispara quando ocorre falha de autenticação SNMP (via Trap).",
                               "dataKey": None},
}

appState = {
    "devices": _seed_devices(),
    "alerts": [
        {"id": _gen_id(), "title": "Sistema GPON Inicializado",
         "description": f"3 OLTs ativas — {len(mock_engine.ONU_PROFILES)} ONUs monitoradas",
         "severity": "info", "time": now_str_minutes(), "device": "SINAPSE-NMS", "source": "system"},
    ],
    "rules": [
        {"id": 1, "name": "ONU Offline", "condition": "ONU status = offline",
         "action": "Alerta Dashboard + Telegram", "severity": "critical", "active": True},
        {"id": 2, "name": "Sinal Óptico Crítico", "condition": "RxPower < -27 dBm (ITU G.984)",
         "action": "SMS + Email + Telegram", "severity": "critical", "active": True},
        {"id": 3, "name": "Sinal Óptico Baixo", "condition": "RxPower < -24 dBm",
         "action": "Alerta Dashboard + Telegram", "severity": "warning", "active": True},
        {"id": 4, "name": "Latência Alta", "condition": "Latência > 50ms por 5 min",
         "action": "Email + Telegram", "severity": "warning", "active": True},
        {"id": 5, "name": "CPU OLT Alta", "condition": "CPU OLT > 80%", "action": "Email",
         "severity": "warning", "active": True},
    ],
    "history": [
        {"id": _gen_id(), "event": "OLT-01 MA5800-X2 Online", "device": "OLT-01", "time": now_str_minutes(),
         "duration": "--", "action": "Boot automático", "user": "Sistema", "type": "system"},
        {"id": _gen_id(), "event": "OLT-02 ZXA10 C600 Online", "device": "OLT-02", "time": now_str_minutes(),
         "duration": "--", "action": "Boot automático", "user": "Sistema", "type": "system"},
        {"id": _gen_id(), "event": "OLT-03 7360 FX-4 Online", "device": "OLT-03", "time": now_str_minutes(),
         "duration": "--", "action": "Boot automático", "user": "Sistema", "type": "system"},
        {"id": _gen_id(), "event": f"{len(mock_engine.ONU_PROFILES)} ONUs Registradas", "device": "SINAPSE-NMS",
         "time": now_str_minutes(), "duration": "--", "action": "Descoberta GPON — 3 OLTs",
         "user": "Sistema", "type": "device"},
        {"id": _gen_id(), "event": "Topografia Carregada", "device": "SINAPSE Node", "time": now_str_minutes(),
         "duration": "--", "action": "NMS → 3 POPs → 3 OLTs → ONUs", "user": "Sistema", "type": "system"},
    ],
    "backups": [],
    "settings": {
        "nodeName": "SINAPSE-Node-01", "timezone": "America/Fortaleza (UTC-3)", "language": "Português (Brasil)",
        "pollingInterval": "5 minutos", "dataRetention": "6 meses", "advancedMetrics": True,
        "notifyEmail": True, "notifyTelegram": True, "notifySMS": False,
        "email": "ti@provedor.com.br", "ip": "192.168.1.100", "mask": "255.255.255.0",
        "gateway": "192.168.1.1", "dns1": "8.8.8.8", "dns2": "8.8.4.4",
    },
    "monitoringParams": [
        {"id": 1, "name": "Degradação Óptica Crítica", "paramType": "opticalDegradation", "target": "all",
         "operator": "<", "threshold": -27, "unit": "dBm", "duration": 0, "severity": "critical",
         "action": "Email + SMS + Telegram", "active": True, "triggerCount": 0, "lastTriggered": None},
        {"id": 2, "name": "Sinal Óptico Baixo", "paramType": "opticalDegradation", "target": "all",
         "operator": "<", "threshold": -24, "unit": "dBm", "duration": 0, "severity": "warning",
         "action": "Alerta Dashboard + Telegram", "active": True, "triggerCount": 0, "lastTriggered": None},
        {"id": 3, "name": "CPU Alta", "paramType": "highCPU", "target": "all", "operator": ">", "threshold": 80,
         "unit": "%", "duration": 5, "severity": "warning", "action": "Email", "active": True,
         "triggerCount": 0, "lastTriggered": None},
        {"id": 4, "name": "Temperatura Alta", "paramType": "highTemperature", "target": "all", "operator": ">",
         "threshold": 65, "unit": "°C", "duration": 0, "severity": "warning", "action": "Email + Telegram",
         "active": True, "triggerCount": 0, "lastTriggered": None},
        {"id": 5, "name": "Latência Alta", "paramType": "latencyHigh", "target": "all", "operator": ">",
         "threshold": 50, "unit": "ms", "duration": 5, "severity": "warning", "action": "Email + Telegram",
         "active": True, "triggerCount": 0, "lastTriggered": None},
        {"id": 6, "name": "ONU Offline", "paramType": "onuOffline", "target": "all", "operator": None,
         "threshold": None, "unit": None, "duration": 0, "severity": "critical",
         "action": "Alerta Dashboard + Telegram", "active": True, "triggerCount": 0, "lastTriggered": None},
    ],
    "maintenances": [],
}

_condition_start_map: dict = {}


def find_device(device_id: int) -> dict | None:
    return next((d for d in appState["devices"] if d["id"] == device_id), None)


def trigger_auto_alert(event_type: str, onu: dict) -> None:
    if event_type == "onuOffline":
        title = f"ONU Offline — {onu['apt']}"
        if any(a["title"] == title and a["severity"] != "resolved" for a in appState["alerts"]):
            return
        description = f"{onu['client']} • {onu['ip']} • Porta {onu['gponPort']}:{onu['portSlot']}"
        appState["alerts"].insert(0, {"id": _gen_id(), "title": title, "source": "auto", "description": description,
                                       "severity": "critical", "time": now_str_minutes(), "device": "OLT-01"})
        add_history({"event": f"Alerta Gerado — {title}", "device": "OLT-01", "duration": "--",
                      "action": description, "user": "Sistema", "type": "alert"})
    if event_type == "onuOnline":
        title = f"ONU Offline — {onu['apt']}"
        if any(a["title"] == title and a["severity"] != "resolved" for a in appState["alerts"]):
            add_history({"event": f"Alerta Resolvido Automaticamente — {title}", "device": "OLT-01",
                          "duration": "--", "action": f"{onu['apt']} voltou a ficar online",
                          "user": "Sistema", "type": "alert"})
        appState["alerts"] = [
            {**a, "severity": "resolved", "resolvedAt": now_str_minutes()} if a["title"] == title else a
            for a in appState["alerts"]
        ]


# ── CRUD Dispositivos ─────────────────────────────────────────────────────────
def get_devices() -> list:
    return appState["devices"]


def add_device(d: dict) -> dict:
    item = {**d, "id": next_device_id(), "status": d.get("status") or "online"}
    appState["devices"].append(item)
    add_history({"event": "Dispositivo Adicionado", "device": d.get("name"), "duration": "--",
                  "action": f"IP: {d.get('ip')}", "user": "admin", "type": "device"})
    return item


def update_device(device_id: int, fields: dict) -> dict | None:
    for i, d in enumerate(appState["devices"]):
        if d["id"] == device_id:
            appState["devices"][i] = {**d, **fields}
            return appState["devices"][i]
    return None


def remove_device(device_id: int) -> None:
    d = find_device(device_id)
    appState["devices"] = [x for x in appState["devices"] if x["id"] != device_id]
    if d:
        add_history({"event": "Dispositivo Removido", "device": d.get("name"), "duration": "--",
                      "action": f"IP: {d.get('ip')}", "user": "admin", "type": "device"})


# ── CRUD Alertas ──────────────────────────────────────────────────────────────
def get_alerts() -> list:
    return appState["alerts"]


def resolve_alert(alert_id: int) -> None:
    a = next((x for x in appState["alerts"] if x["id"] == alert_id), None)
    appState["alerts"] = [
        {**x, "severity": "resolved", "resolvedAt": now_str_minutes()} if x["id"] == alert_id else x
        for x in appState["alerts"]
    ]
    if a:
        add_history({"event": f"Alerta Resolvido — {a['title']}", "device": a.get("device") or "Rede",
                      "duration": "--", "action": a.get("description") or "--", "user": "admin", "type": "alert"})


def ignore_alert(alert_id: int) -> None:
    a = next((x for x in appState["alerts"] if x["id"] == alert_id), None)
    appState["alerts"] = [x for x in appState["alerts"] if x["id"] != alert_id]
    if a:
        add_history({"event": f"Alerta Removido — {a['title']}", "device": a.get("device") or "Rede",
                      "duration": "--", "action": a.get("description") or "--", "user": "admin", "type": "alert"})


def add_alert(a: dict) -> dict:
    item = {**a, "id": _gen_id(), "time": now_str_minutes()}
    appState["alerts"].insert(0, item)
    add_history({"event": f"Alerta Gerado — {item.get('title')}", "device": item.get("device") or "Rede",
                  "duration": "--", "action": item.get("description") or "--", "user": "Sistema", "type": "alert"})
    return item


# ── CRUD Regras (legado) ───────────────────────────────────────────────────────
def get_rules() -> list:
    return appState["rules"]


def add_rule(r: dict) -> dict:
    item = {**r, "id": _gen_id(), "active": True}
    appState["rules"].append(item)
    return item


def update_rule(rule_id: int, fields: dict) -> dict | None:
    for i, r in enumerate(appState["rules"]):
        if r["id"] == rule_id:
            appState["rules"][i] = {**r, **fields}
            return appState["rules"][i]
    return None


def toggle_rule(rule_id: int) -> dict | None:
    for i, r in enumerate(appState["rules"]):
        if r["id"] == rule_id:
            appState["rules"][i] = {**r, "active": not r["active"]}
            return appState["rules"][i]
    return None


def remove_rule(rule_id: int) -> None:
    appState["rules"] = [r for r in appState["rules"] if r["id"] != rule_id]


# ── Histórico ─────────────────────────────────────────────────────────────────
def get_app_history() -> list:
    return appState["history"]


def add_history(item: dict) -> dict:
    entry = {**item, "id": _gen_id(), "time": now_str_minutes()}
    appState["history"].insert(0, entry)
    return entry


# ── Backups ───────────────────────────────────────────────────────────────────
def get_backups() -> list:
    return appState["backups"]


def create_backup() -> dict:
    import copy
    import random
    from datetime import datetime

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Hh%M")
    snap = {
        "id": _gen_id(), "filename": f"backup-{date_str}_{time_str}.zip",
        "date": f"{date_str} {now.strftime('%H:%M')}", "size": f"{(random.random() * 2 + 0.5):.1f} MB",
        "devices": copy.deepcopy(appState["devices"]), "alerts": copy.deepcopy(appState["alerts"]),
        "rules": copy.deepcopy(appState["rules"]), "settings": copy.deepcopy(appState["settings"]),
        "history": copy.deepcopy(appState["history"]),
    }
    appState["backups"].insert(0, snap)
    appState["backups"] = appState["backups"][:10]
    add_history({"event": "Backup Criado", "device": "SINAPSE Node", "duration": "--",
                  "action": snap["filename"], "user": "admin", "type": "backup"})
    return snap


def restore_backup(backup_id: int) -> bool:
    b = next((x for x in appState["backups"] if x["id"] == backup_id), None)
    if not b:
        return False
    appState["devices"] = b["devices"]
    appState["alerts"] = b["alerts"]
    appState["rules"] = b["rules"]
    appState["settings"] = b["settings"]
    if b.get("history"):
        appState["history"] = b["history"]
    return True


def remove_backup(backup_id: int) -> None:
    appState["backups"] = [b for b in appState["backups"] if b["id"] != backup_id]


# ── Configurações ─────────────────────────────────────────────────────────────
def get_settings() -> dict:
    return appState["settings"]


def save_settings(s: dict) -> dict:
    appState["settings"] = {**appState["settings"], **s}
    return appState["settings"]


# ── Parâmetros de Monitoramento (antes só no localStorage do navegador) ───────
def get_monitoring_params() -> list:
    return appState["monitoringParams"]


def add_monitoring_param(p: dict) -> dict:
    item = {**p, "id": _gen_id(), "triggerCount": 0, "lastTriggered": None}
    appState["monitoringParams"].append(item)
    return item


def update_monitoring_param(param_id: int, fields: dict) -> dict | None:
    for i, p in enumerate(appState["monitoringParams"]):
        if p["id"] == param_id:
            appState["monitoringParams"][i] = {**p, **fields}
            return appState["monitoringParams"][i]
    return None


def toggle_monitoring_param(param_id: int) -> dict | None:
    for i, p in enumerate(appState["monitoringParams"]):
        if p["id"] == param_id:
            appState["monitoringParams"][i] = {**p, "active": not p["active"]}
            return appState["monitoringParams"][i]
    return None


def remove_monitoring_param(param_id: int) -> None:
    appState["monitoringParams"] = [p for p in appState["monitoringParams"] if p["id"] != param_id]
    _condition_start_map.pop(param_id, None)


def _record_monitoring_param_trigger(param_id: int) -> None:
    for i, p in enumerate(appState["monitoringParams"]):
        if p["id"] == param_id:
            appState["monitoringParams"][i] = {**p, "triggerCount": (p.get("triggerCount") or 0) + 1,
                                                 "lastTriggered": time.time() * 1000}


def evaluate_monitoring_params(data: dict) -> None:
    """Avalia os parâmetros de monitoramento ativos contra os dados de telemetria em
    tempo real, chamada a cada ciclo de /api/metrics/live (equivalente ao antigo
    evaluateMonitoringParams do navegador, agora rodando no servidor)."""
    if not data:
        return
    now_ms = time.time() * 1000
    for param in [p for p in appState["monitoringParams"] if p["active"]]:
        definition = MONITORING_PARAM_TYPES.get(param["paramType"])
        if not definition or not definition["dataKey"]:
            continue  # Tipos event-based (linkDown, authFailure) dependem de Trap

        value = data.get(definition["dataKey"])
        if value is None:
            continue

        condition_met = False
        if definition["hasThreshold"]:
            threshold = param["threshold"]
            if param["operator"] == "<":
                condition_met = value < threshold
            elif param["operator"] == ">":
                condition_met = value > threshold
        elif param["paramType"] == "onuOffline":
            total = data.get("onusTotal") or 0
            condition_met = total > 0 and value < total

        if condition_met:
            if param["id"] not in _condition_start_map:
                _condition_start_map[param["id"]] = now_ms
            elapsed_ms = now_ms - _condition_start_map[param["id"]]
            duration_ms = (param.get("duration") or 0) * 60 * 1000
            if elapsed_ms < duration_ms:
                continue
            if param.get("lastTriggered") and now_ms - param["lastTriggered"] < 300000:
                continue

            description = (f"Valor atual: {value}{param['unit']} (limiar: {param['operator']} "
                            f"{param['threshold']}{param['unit']})") if definition["hasThreshold"] else \
                f"Condição detectada em: {'todos os dispositivos' if param['target'] == 'all' else param['target']}"

            add_alert({"title": param["name"], "description": description, "severity": param["severity"],
                       "device": "Rede" if param["target"] == "all" else param["target"]})
            _record_monitoring_param_trigger(param["id"])
        else:
            _condition_start_map.pop(param["id"], None)


# ── Manutenções (antes só no localStorage do navegador) ───────────────────────
def get_maintenances() -> list:
    return appState["maintenances"]


def add_maintenance(item: dict) -> dict:
    new_item = {**item, "id": _gen_id(), "status": "agendado"}
    appState["maintenances"].insert(0, new_item)
    add_history({"event": "Manutenção Agendada", "device": item.get("device"),
                  "duration": item.get("duration") or "--",
                  "action": item.get("description") or "Manutenção programada", "user": "admin",
                  "type": "maintenance"})
    return new_item


def remove_maintenance(maintenance_id: int) -> None:
    appState["maintenances"] = [m for m in appState["maintenances"] if m["id"] != maintenance_id]
