#!/usr/bin/env python3
"""Diagnóstico de acesso à ONU real via login web (fallback ao SNMP, que não está
disponível nesse equipamento). Faz login em /boaform/admin/formLogin e consulta
/boaform/getASPdata/ponGetStatus.

O painel deste aparelho não depende de cookie de sessão pra manter o login (a
própria página trata qualquer resposta sem marcador de erro conhecido como
sucesso — provavelmente controla sessão por IP de origem, não por cookie). Por
isso: se um Set-Cookie vier, usamos; se não vier mas também não houver erro,
seguimos mesmo assim.

Credenciais NUNCA ficam no código — configure python-server/.env:
  ONU_HOST=192.168.100.1
  ONU_USERNAME=seu_usuario_admin
  ONU_PASSWORD=sua_senha_admin

Uso:
  python tools/onu_real_test.py          # uma consulta
  python tools/onu_real_test.py --watch  # consulta a cada 5s (Ctrl+C pra sair)
"""
import re
import sys
import time
from datetime import datetime

import requests

sys.path.insert(0, __file__.rsplit("tools", 1)[0])
from app.config import settings  # noqa: E402

HOST = settings.onu_host
USERNAME = settings.onu_username
PASSWORD = settings.onu_password
WATCH = "--watch" in sys.argv

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


def login() -> requests.cookies.RequestsCookieJar:
    res = requests.post(
        f"http://{HOST}/boaform/admin/formLogin",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    text = res.text

    for marker, message in LOGIN_ERRORS.items():
        if marker in text:
            raise RuntimeError(f'Login falhou: {message} (resposta: "{text.strip()}")')

    if res.cookies:
        return res.cookies

    print("  (sem cookie de sessão — equipamento parece controlar acesso por IP de origem)")
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


def get_pon_status(cookies) -> dict:
    res = requests.get(f"http://{HOST}/boaform/getASPdata/ponGetStatus", cookies=cookies, timeout=10)
    text = res.text
    if "pon_info=" not in text:
        raise RuntimeError(f'Resposta inesperada (provavelmente não autenticado): "{text.strip()[:200]}"')
    return parse_pon_info(text)


def print_status(status: dict) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{ts}] ONU {HOST} — {status['ponMode']} — {status['connectStatus']}")
    print(f"  RxPower: {status['rxPowerDbm']} dBm   TxPower: {status['txPowerDbm']} dBm")
    print(f"  Temperatura: {status['temperatureC']} °C   Tensão: {status['voltageV']} V   Corrente: {status['biasCurrentMa']} mA")
    print(f"  FEC up/down: {status['fecUpstream']}/{status['fecDownstream']}   Erros FEC/HEC: {status['fecErrors']}/{status['hecErrors']}")


def main() -> int:
    if not USERNAME or not PASSWORD:
        print("Defina ONU_HOST, ONU_USERNAME e ONU_PASSWORD em python-server/.env antes de rodar este script.", file=sys.stderr)
        return 1

    print(f"Logando em http://{HOST}...")
    try:
        cookies = login()
        print("Login OK.")
        status = get_pon_status(cookies)
        print_status(status)
    except Exception as err:  # diagnóstico interativo: qualquer falha é reportada e encerra
        print(f"Erro: {err}", file=sys.stderr)
        return 1

    if not WATCH:
        return 0

    print("\nModo --watch: consultando a cada 5s (Ctrl+C pra sair)...")
    try:
        while True:
            time.sleep(5)
            try:
                print_status(get_pon_status(cookies))
            except Exception as err:
                print(f"Erro na consulta: {err}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
