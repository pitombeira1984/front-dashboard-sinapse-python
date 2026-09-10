#!/usr/bin/env python3
"""Sobe o snmpsim simulando um OLT Huawei MA5800 (dataset em public.snmprec),
para o SINAPSE escanear via Descoberta Automática (Devices -> Escanear Rede).

IMPORTANTE: rode isso com o Python do venv ISOLADO tools/lab-venv/.venv, nunca
com o venv principal do python-server, e nunca com o venv DENTRO de tools/lab/
(o data_dir abaixo escaneia recursivamente tudo que estiver ali, inclusive um
venv, e acaba indexando os arquivos de amostra que o pacote snmpsim instala
como se fossem dispositivos simulados extras). snmpsim-lextudio arrasta
pysnmp-lextudio 6.x como dependência, incompatível com o pysnmp-lextudio 5.x
que o resto do app usa (ver python-server/README.md).

Uso:
  tools/lab-venv/.venv/Scripts/python.exe tools/lab/run_olt_sim.py [host:port]

Exemplos:
  tools/lab-venv/.venv/Scripts/python.exe tools/lab/run_olt_sim.py
  tools/lab-venv/.venv/Scripts/python.exe tools/lab/run_olt_sim.py 192.168.100.26:161
"""
import asyncio
import sys
from pathlib import Path

endpoint = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:1161"
data_dir = str(Path(__file__).resolve().parent)

# Sem um loop asyncio corrente, o carrier UDP do pysnmp-lextudio 5.x quebra em
# Python 3.12+ (asyncio.get_event_loop() sem loop ativo dá RuntimeError).
# Criar um loop antes de chamar o responder contorna isso.
asyncio.set_event_loop(asyncio.new_event_loop())

sys.argv = [
    "snmpsim-command-responder",
    f"--data-dir={data_dir}",
    f"--agent-udpv4-endpoint={endpoint}",
]

from snmpsim.commands.responder import main  # noqa: E402

main()
