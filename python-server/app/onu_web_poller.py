"""Poller da ONU real via painel web (/boaform), integrado ao servidor.

Mesmo fluxo de tools/onu_real_test.py (login em /boaform/admin/formLogin e leitura
de /boaform/getASPdata/ponGetStatus — esse equipamento não expõe SNMP), mas rodando
numa thread de fundo: a última leitura fica em memória e o mock_engine passa a usar
os valores reais no lugar dos simulados para a ONU de ONU_POLLER_ONU_ID. Todas as
demais ONUs continuam simuladas.

Desligado por padrão (ONU_POLLER_ENABLED=false) — sem hardware na rede, o servidor
se comporta exatamente como antes.
"""
import re
import threading
import time

import requests

from .config import settings

# Marcadores que o próprio JS do painel (Login_control.js) trata como falha.
# Qualquer resposta que não contenha nenhum desses é tratada como sucesso.
LOGIN_ERRORS = {
    "PW_OR_NAME_FALSE": "Usuário ou senha incorretos",
    "LOGINED_ERROR_3": "Bloqueado temporariamente por tentativas incorretas",
    "ANOTHER_USER_LOGINED": "Outro usuário já está logado",
    "ADMINISTRATOR_ONLY": "Acesso restrito a administrador",
    "DEFAULT_ERROR": "Erro desconhecido de login",
    "DEFAULT_PASSWD": "Senha padrão de fábrica ainda ativa (o equipamento exige troca)",
}

# Após falha de login (credencial errada, bloqueio, outro admin logado), espera bem
# mais que o intervalo normal antes de tentar de novo — insistir a cada poucos
# segundos pode disparar o bloqueio por tentativas (LOGINED_ERROR_3) do equipamento.
LOGIN_RETRY_BACKOFF_S = 300


class OnuLoginError(RuntimeError):
    pass


class OnuNotAuthenticatedError(RuntimeError):
    pass


def login(host: str, username: str, password: str) -> requests.cookies.RequestsCookieJar:
    """O painel normalmente não devolve cookie (parece liberar acesso por IP de
    origem); se vier um, é repassado nas leituras seguintes."""
    res = requests.post(
        f"http://{host}/boaform/admin/formLogin",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    text = res.text
    for marker, message in LOGIN_ERRORS.items():
        if marker in text:
            raise OnuLoginError(f'Login falhou: {message} (resposta: "{text.strip()}")')
    return res.cookies


def parse_pon_info(raw: str) -> dict:
    eq_idx = raw.find("=")
    payload = raw if eq_idx == -1 else raw[eq_idx + 1:]

    fields = {}
    for pair in payload.split("&"):
        if not pair or "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        fields[key] = value

    def num(key):
        match = re.search(r"-?[\d.]+", fields.get(key, "")) if fields.get(key) else None
        return float(match.group(0)) if match else None

    return {
        "ponMode": fields.get("pon_mode"),
        "connectStatus": fields.get("pon_connect_status"),
        "fecUpstream": fields.get("pon-fec-us-state"),
        "fecDownstream": fields.get("pon-fec-ds-state"),
        "fecErrors": num("fec-errors"),
        "hecErrors": num("hec-errors"),
        "packetsDropped": num("packets-dropped"),
        "temperatureC": num("temperature"),
        "voltageV": num("voltage"),
        "txPowerDbm": num("tx-power"),
        "rxPowerDbm": num("rx-power"),
        "biasCurrentMa": num("bias-current"),
        "bytesSent": num("bytes-sent"),
        "bytesReceived": num("bytes-received"),
    }


def get_pon_status(host: str, cookies) -> dict:
    res = requests.get(f"http://{host}/boaform/getASPdata/ponGetStatus", cookies=cookies, timeout=10)
    text = res.text
    if "pon_info=" not in text:
        raise OnuNotAuthenticatedError(f'Resposta inesperada (provavelmente não autenticado): "{text.strip()[:200]}"')
    return parse_pon_info(text)


# ── Poller em background ──────────────────────────────────────────────────────
_lock = threading.Lock()
_stop = threading.Event()
_thread: threading.Thread | None = None
_state = {
    "lastReading": None,
    "lastReadingAt": 0.0,
    "lastError": None,
    "lastErrorAt": 0.0,
}


def _poll_loop() -> None:
    cookies = None
    logged_in = False
    while not _stop.is_set():
        wait = settings.onu_poller_interval
        try:
            if not logged_in:
                cookies = login(settings.onu_host, settings.onu_username, settings.onu_password)
                logged_in = True
            try:
                reading = get_pon_status(settings.onu_host, cookies)
            except OnuNotAuthenticatedError:
                # Sessão (por IP) expirou — um re-login e uma nova tentativa no mesmo ciclo.
                cookies = login(settings.onu_host, settings.onu_username, settings.onu_password)
                reading = get_pon_status(settings.onu_host, cookies)
            with _lock:
                _state["lastReading"] = reading
                _state["lastReadingAt"] = time.time()
                _state["lastError"] = None
        except (requests.RequestException, OnuLoginError, OnuNotAuthenticatedError) as err:
            logged_in = False
            if isinstance(err, OnuLoginError):
                wait = max(wait, LOGIN_RETRY_BACKOFF_S)
            with _lock:
                _state["lastError"] = str(err)
                _state["lastErrorAt"] = time.time()
        _stop.wait(wait)


def start() -> None:
    global _thread
    if not settings.onu_poller_enabled or _thread is not None:
        return
    if not settings.onu_username or not settings.onu_password:
        with _lock:
            _state["lastError"] = "ONU_USERNAME/ONU_PASSWORD não definidos no .env — poller não iniciado"
            _state["lastErrorAt"] = time.time()
        return
    _stop.clear()
    _thread = threading.Thread(target=_poll_loop, name="onu-web-poller", daemon=True)
    _thread.start()


def stop() -> None:
    global _thread
    _stop.set()
    _thread = None


def covers(onu_id: int) -> bool:
    return settings.onu_poller_enabled and onu_id == settings.onu_poller_onu_id


def get_live_reading(onu_id: int) -> dict | None:
    """Leitura real para a ONU mapeada, ou None quando o poller não cobre essa ONU
    ou ainda não concluiu a primeira tentativa (a simulação segue até lá, para não
    gerar um alerta de "ONU Offline" falso no boot do servidor).

    "fresh" = última leitura bem-sucedida há no máximo 3 intervalos de polling."""
    if not covers(onu_id):
        return None
    with _lock:
        reading = _state["lastReading"]
        reading_at = _state["lastReadingAt"]
        has_error = _state["lastError"] is not None
    if reading is None and not has_error:
        return None
    fresh = reading is not None and time.time() - reading_at <= settings.onu_poller_interval * 3
    return {"fresh": fresh, "reading": reading or {}}


def get_status() -> dict:
    with _lock:
        snapshot = dict(_state)
    age = time.time() - snapshot["lastReadingAt"] if snapshot["lastReading"] is not None else None
    return {
        "enabled": settings.onu_poller_enabled,
        "running": _thread is not None and _thread.is_alive(),
        "host": settings.onu_host,
        "onuId": settings.onu_poller_onu_id,
        "intervalSeconds": settings.onu_poller_interval,
        "fresh": age is not None and age <= settings.onu_poller_interval * 3,
        "ageSeconds": round(age, 1) if age is not None else None,
        **snapshot,
    }
