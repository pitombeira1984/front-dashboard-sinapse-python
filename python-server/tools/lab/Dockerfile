# Simulador SNMP genérico (snmpsim-lextudio) para o laboratório do SINAPSE.
# A mesma imagem serve qualquer dispositivo simulado — o que muda é o dataset
# copiado via DATASET_DIR (build arg), ver docker-compose.yml.
#
# Por que uma imagem própria em vez do venv isolado de tools/lab-venv/:
# snmpsim-lextudio arrasta pysnmp-lextudio 6.x, incompatível com o
# pysnmp-lextudio 5.x que o resto do python-server usa (ver README). Rodar em
# container elimina esse conflito de dependências sem precisar de um segundo
# venv no host, e permite subir vários dispositivos simulados (IPs distintos
# na rede docker) ao mesmo tempo.
FROM python:3.12-slim

RUN pip install --no-cache-dir snmpsim-lextudio==1.1.1

ARG DATASET_DIR=datasets/olt
COPY ${DATASET_DIR} /data

EXPOSE 161/udp

CMD ["snmpsim-command-responder", "--data-dir=/data", "--agent-udpv4-endpoint=0.0.0.0:161", "--process-user=nobody", "--process-group=nogroup"]
