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
import sys
import time
from datetime import datetime

sys.path.insert(0, __file__.rsplit("tools", 1)[0])
from app.config import settings  # noqa: E402
from app.onu_web_poller import get_pon_status, login as _login  # noqa: E402

HOST = settings.onu_host
USERNAME = settings.onu_username
PASSWORD = settings.onu_password
WATCH = "--watch" in sys.argv


def login():
    cookies = _login(HOST, USERNAME, PASSWORD)
    if not cookies:
        print("  (sem cookie de sessão — equipamento parece controlar acesso por IP de origem)")
    return cookies


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
        status = get_pon_status(HOST, cookies)
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
                print_status(get_pon_status(HOST, cookies))
            except Exception as err:
                print(f"Erro na consulta: {err}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
