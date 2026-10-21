# ===== ENGINE DE DADOS MOCK — TOPOGRAFIA GPON =====
# Orange Pi (NMS) -> POP -> OLT -> CTO/Splitter 1:8 -> 8 ONUs -> Clientes
import random
import time
from datetime import datetime, timezone

from . import onu_web_poller, optical_thresholds
from .formatting import now_str_minutes, uptime_to_string


def jitter(base: float, rng: float) -> float:
    return round(base + (random.random() - 0.5) * 2 * rng, 3)


def drift(cur: float, base: float, speed: float = 0.05, rng: float = 0.5) -> float:
    return round(cur + (base - cur) * speed + (random.random() - 0.5) * rng, 3)


def clamp(v: float, mn: float, mx: float) -> float:
    return min(mx, max(mn, v))


# ── Topografia GPON ──────────────────────────────────────────────────────────
GPON_TOPOLOGY = {
    "nms": {"name": "Orange Pi 3B — NMS", "ip": "192.168.1.100", "role": "NMS", "os": "Ubuntu 24.04 LTS"},
    "olt": {"id": "OLT-01", "name": "OLT Huawei MA5800-X2", "ip": "10.0.1.10", "model": "MA5800-X2",
            "firmware": "V100R019C10SPC200", "serial": "HW-OLT-A3F2C100", "port": "0/1/0", "maxONUs": 128},
    "splitter": {"id": "CTO-01", "name": "CTO/Splitter 1:8", "type": "1x8 SC/APC",
                 "location": "Caixa de Emenda — Poste 42", "loss": 3.5},
}

# ── Tabela de OLTs do provedor ───────────────────────────────────────────────
OLTS = [
    {"id": "OLT-01", "name": "OLT-01", "ip": "10.0.1.10", "model": "MA5800-X2", "vendor": "Huawei",
     "capacity": 2500, "location": "POP Central", "maxONUs": 128},
    {"id": "OLT-02", "name": "OLT-02", "ip": "10.0.2.10", "model": "ZXA10 C600", "vendor": "ZTE",
     "capacity": 2500, "location": "POP Bairro Norte", "maxONUs": 128},
    {"id": "OLT-03", "name": "OLT-03", "ip": "10.0.3.10", "model": "7360 FX-4", "vendor": "Nokia",
     "capacity": 10000, "location": "POP Bairro Sul", "maxONUs": 256},
]

# ── Portas GPON disponíveis (todas as OLTs) ──────────────────────────────────
GPON_PORTS = [
    {"id": "0/1/0", "oltId": "OLT-01", "name": "OLT-01 / GPON 0/1/0", "description": "Bloco A — Andares 1 e 2", "maxONUs": 8},
    {"id": "0/1/1", "oltId": "OLT-01", "name": "OLT-01 / GPON 0/1/1", "description": "Bloco A — Andares 2 e 3", "maxONUs": 8},
    {"id": "0/1/2", "oltId": "OLT-01", "name": "OLT-01 / GPON 0/1/2", "description": "Bloco B", "maxONUs": 8},
    {"id": "0/1/3", "oltId": "OLT-01", "name": "OLT-01 / GPON 0/1/3", "description": "Bloco C (reserva)", "maxONUs": 8},
    {"id": "0/2/0", "oltId": "OLT-02", "name": "OLT-02 / GPON 0/2/0", "description": "Zona Norte — Setor 1", "maxONUs": 8},
    {"id": "0/2/1", "oltId": "OLT-02", "name": "OLT-02 / GPON 0/2/1", "description": "Zona Norte — Setor 2", "maxONUs": 8},
    {"id": "0/3/0", "oltId": "OLT-03", "name": "OLT-03 / GPON 0/3/0", "description": "Zona Sul — Setor 1", "maxONUs": 8},
    {"id": "0/3/1", "oltId": "OLT-03", "name": "OLT-03 / GPON 0/3/1", "description": "Zona Sul — Setor 2", "maxONUs": 8},
]

# ── ONUs — distribuídas entre as 3 OLTs ──────────────────────────────────────
ONU_PROFILES = [
    {"id": 1, "client": "João Silva", "apt": "Apto 101", "serial": "HW-ONU-A1B2C301", "ip": "10.0.1.101", "model": "HG8245Q2", "distance": 0.3, "rxBase": -17.2, "gponPort": "0/1/0", "portSlot": 0},
    {"id": 2, "client": "Maria Oliveira", "apt": "Apto 102", "serial": "HW-ONU-A1B2C302", "ip": "10.0.1.102", "model": "HG8245Q2", "distance": 0.5, "rxBase": -18.1, "gponPort": "0/1/0", "portSlot": 1},
    {"id": 3, "client": "Carlos Santos Consultoria Ltda.", "apt": "Apto 103", "serial": "HW-ONU-A1B2C303", "ip": "10.0.1.103", "model": "HG8245Q2", "distance": 0.7, "rxBase": -19.3, "gponPort": "0/1/0", "portSlot": 2},
    {"id": 4, "client": "Ana Costa", "apt": "Apto 201", "serial": "HW-ONU-A1B2C304", "ip": "10.0.1.104", "model": "HG8245Q2", "distance": 0.9, "rxBase": -20.5, "gponPort": "0/1/0", "portSlot": 3},
    {"id": 5, "client": "Clínica Saúde Vida", "apt": "Apto 202", "serial": "HW-ONU-A1B2C305", "ip": "10.0.1.105", "model": "HG8245Q2", "distance": 1.1, "rxBase": -21.8, "gponPort": "0/1/1", "portSlot": 0},
    {"id": 6, "client": "Centro de Ensino Avançado", "apt": "Apto 203", "serial": "HW-ONU-A1B2C306", "ip": "10.0.1.106", "model": "HG8245Q2", "distance": 1.3, "rxBase": -22.4, "gponPort": "0/1/1", "portSlot": 1},
    {"id": 7, "client": "Roberto Lima", "apt": "Apto 204", "serial": "HW-ONU-A1B2C307", "ip": "10.0.1.107", "model": "HG8245Q2", "distance": 1.5, "rxBase": -23.1, "gponPort": "0/1/1", "portSlot": 2},
    {"id": 8, "client": "Fernanda Rocha", "apt": "Apto 301", "serial": "HW-ONU-A1B2C308", "ip": "10.0.1.108", "model": "HG8245Q2", "distance": 1.8, "rxBase": -24.2, "gponPort": "0/1/2", "portSlot": 0},
    {"id": 9, "client": "Lucas Ferreira", "apt": "Casa 01", "serial": "ZTE-ONU-B1C2D301", "ip": "10.0.2.101", "model": "F660", "distance": 0.4, "rxBase": -17.5, "gponPort": "0/2/0", "portSlot": 0},
    {"id": 10, "client": "Beatriz Santos", "apt": "Casa 02", "serial": "ZTE-ONU-B1C2D302", "ip": "10.0.2.102", "model": "F660", "distance": 0.6, "rxBase": -18.8, "gponPort": "0/2/0", "portSlot": 1},
    {"id": 11, "client": "Marcelo Gomes", "apt": "Apto 201", "serial": "ZTE-ONU-B1C2D303", "ip": "10.0.2.103", "model": "F660", "distance": 0.9, "rxBase": -20.2, "gponPort": "0/2/0", "portSlot": 2},
    {"id": 12, "client": "Provedor Norte Ltda.", "apt": "Sala 01", "serial": "ZTE-ONU-B1C2D304", "ip": "10.0.2.104", "model": "F660", "distance": 1.1, "rxBase": -21.4, "gponPort": "0/2/1", "portSlot": 0},
    {"id": 13, "client": "Sirlene Cavalcante", "apt": "Apto 305", "serial": "ZTE-ONU-B1C2D305", "ip": "10.0.2.105", "model": "F660", "distance": 1.3, "rxBase": -22.6, "gponPort": "0/2/1", "portSlot": 1},
    {"id": 14, "client": "Hospital Regional", "apt": "Ala A", "serial": "NOK-ONU-C1D2E301", "ip": "10.0.3.101", "model": "G-010G-T", "distance": 0.5, "rxBase": -16.8, "gponPort": "0/3/0", "portSlot": 0},
    {"id": 15, "client": "Prefeitura Municipal", "apt": "Setor TI", "serial": "NOK-ONU-C1D2E302", "ip": "10.0.3.102", "model": "G-010G-T", "distance": 0.7, "rxBase": -18.3, "gponPort": "0/3/0", "portSlot": 1},
    {"id": 16, "client": "TechCenter Sul", "apt": "Sala 302", "serial": "NOK-ONU-C1D2E303", "ip": "10.0.3.103", "model": "G-010G-T", "distance": 1.0, "rxBase": -20.1, "gponPort": "0/3/0", "portSlot": 2},
    {"id": 17, "client": "Escola Estadual Norte", "apt": "Bloco B", "serial": "NOK-ONU-C1D2E304", "ip": "10.0.3.104", "model": "G-010G-T", "distance": 1.2, "rxBase": -21.5, "gponPort": "0/3/1", "portSlot": 0},
    {"id": 18, "client": "Supermercado Alfa", "apt": "Caixa TI", "serial": "NOK-ONU-C1D2E305", "ip": "10.0.3.105", "model": "G-010G-T", "distance": 1.4, "rxBase": -22.9, "gponPort": "0/3/1", "portSlot": 1},
]


def _make_onu_state(p: dict) -> dict:
    return {
        **p,
        "status": "online",
        "rxPower": p["rxBase"],
        "txPower": 2.5,
        "sfpTemp": round(jitter(45, 3), 1),
        "sfpVoltage": round(jitter(3.3, 0.05), 3),
        "ber": round(random.random() * 5e-11, 15),
        "latency": round(5 + p["distance"] * 3, 1),
        "uptimeTicks": random.randint(0, 864000 * 100),
        "offlineTimer": 0,
        "offlineCooldown": random.random() * 60,
        "degraded": False,
        "lastSeen": now_str_minutes(),
        "history": {
            "rxPower": [jitter(p["rxBase"], 0.4) for _ in range(120)],
            "latency": [jitter(5 + p["distance"] * 3, 1.5) for _ in range(120)],
        },
    }


onu_state = [_make_onu_state(p) for p in ONU_PROFILES]

snmp_state = {
    "ifInOctets": random.randint(0, int(1e10)),
    "ifOutOctets": random.randint(0, int(5e9)),
    "ipInReceives": random.randint(0, int(5e8)),
    "ipOutRequests": random.randint(0, int(5e8)),
    "uptime": random.randint(0, 864000 * 100) + 864000 * 200,
    "cpuBase": 12,
    "memUsed": 230,
    "lastTick": time.time(),
    "history": {"rxPowerAvg": [], "latencyAvg": [], "traffic": [], "onusOnline": []},
    "anomaly": None,
    "anomalyTimer": 0,
    # Banda por OLT: índice 0=OLT-01 (sincronizado), 1=OLT-02, 2=OLT-03 (simulados)
    "olts": [
        {"inRate": 150, "outRate": 55},
        {"inRate": 280, "outRate": 95},
        {"inRate": 620, "outRate": 210},
    ],
}

# Histórico inicial (baseado apenas nas ONUs da OLT-01 para os KPIs principais)
_OLT01_PROFILES = [p for p in ONU_PROFILES if p["gponPort"].startswith("0/1/")]
_avg_rx = sum(p["rxBase"] for p in _OLT01_PROFILES) / len(_OLT01_PROFILES)
_avg_lat = sum(5 + p["distance"] * 3 for p in _OLT01_PROFILES) / len(_OLT01_PROFILES)
for _ in range(120):
    snmp_state["history"]["rxPowerAvg"].append(jitter(_avg_rx, 0.3))
    snmp_state["history"]["latencyAvg"].append(jitter(_avg_lat, 1.5))
    snmp_state["history"]["traffic"].append({"in": jitter(150, 60), "out": jitter(50, 25)})
    snmp_state["history"]["onusOnline"].append(len(_OLT01_PROFILES))


# ── Cadastro de Clientes ─────────────────────────────────────────────────────
_ENDERECO_ALDEOTA = lambda numero, complemento: {
    "rua": "Av. Senador Virgílio Távora", "numero": numero, "complemento": complemento,
    "bairro": "Aldeota", "cidade": "Fortaleza", "estado": "CE", "cep": "60170-251",
}

CLIENT_PROFILES = [
    {"id": 1, "onuId": 1, "nome": "João Silva", "tipo_documento": "cpf", "documento": "123.456.789-01", "telefone": "(85) 9 9801-1011", "email": "joao.silva@email.com", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 101"), "localizacao": {"lat": -3.7372, "lng": -38.5120}, "criticidade": "comum", "categoria": "Residencial", "plano": "100 Mbps", "data_instalacao": "15/03/2023", "contrato": "CTR-2023-001"},
    {"id": 2, "onuId": 2, "nome": "Maria Oliveira", "tipo_documento": "cpf", "documento": "234.567.890-12", "telefone": "(85) 9 9802-1012", "email": "maria.oliveira@email.com", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 102"), "localizacao": {"lat": -3.7374, "lng": -38.5118}, "criticidade": "comum", "categoria": "Residencial", "plano": "200 Mbps", "data_instalacao": "20/04/2023", "contrato": "CTR-2023-002"},
    {"id": 3, "onuId": 3, "nome": "Carlos Santos Consultoria Ltda.", "tipo_documento": "cnpj", "documento": "12.345.678/0001-90", "telefone": "(85) 3301-1234", "email": "ti@carlossantos.com.br", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 103 — Escritório"), "localizacao": {"lat": -3.7376, "lng": -38.5116}, "criticidade": "prioritário", "categoria": "Empresa", "plano": "500 Mbps", "data_instalacao": "10/11/2022", "contrato": "CTR-2022-003"},
    {"id": 4, "onuId": 4, "nome": "Ana Costa", "tipo_documento": "cpf", "documento": "345.678.901-23", "telefone": "(85) 9 9804-1014", "email": "ana.costa@email.com", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 201"), "localizacao": {"lat": -3.7378, "lng": -38.5114}, "criticidade": "comum", "categoria": "Residencial", "plano": "100 Mbps", "data_instalacao": "01/06/2023", "contrato": "CTR-2023-004"},
    {"id": 5, "onuId": 5, "nome": "Clínica Saúde Vida", "tipo_documento": "cnpj", "documento": "23.456.789/0001-01", "telefone": "(85) 3302-5050", "email": "contato@saudevida.med.br", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 202 — Clínica"), "localizacao": {"lat": -3.7380, "lng": -38.5112}, "criticidade": "crítico", "categoria": "Saúde", "plano": "1 Gbps", "data_instalacao": "23/05/2022", "contrato": "CTR-2022-005"},
    {"id": 6, "onuId": 6, "nome": "Centro de Ensino Avançado", "tipo_documento": "cnpj", "documento": "34.567.890/0001-12", "telefone": "(85) 3303-6060", "email": "ti@ensinoavancado.edu.br", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 203 — Instituto"), "localizacao": {"lat": -3.7382, "lng": -38.5110}, "criticidade": "crítico", "categoria": "Educação", "plano": "500 Mbps", "data_instalacao": "14/07/2022", "contrato": "CTR-2022-006"},
    {"id": 7, "onuId": 7, "nome": "Roberto Lima", "tipo_documento": "cpf", "documento": "456.789.012-34", "telefone": "(85) 9 9807-1017", "email": "roberto.lima@email.com", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 204"), "localizacao": {"lat": -3.7384, "lng": -38.5108}, "criticidade": "comum", "categoria": "Residencial", "plano": "300 Mbps", "data_instalacao": "30/09/2023", "contrato": "CTR-2023-007"},
    {"id": 8, "onuId": 8, "nome": "Fernanda Rocha", "tipo_documento": "cpf", "documento": "567.890.123-45", "telefone": "(85) 9 9808-1018", "email": "fernanda.rocha@email.com", "endereco": _ENDERECO_ALDEOTA("1234", "Apto 301"), "localizacao": {"lat": -3.7386, "lng": -38.5106}, "criticidade": "comum", "categoria": "Residencial", "plano": "100 Mbps", "data_instalacao": "08/01/2024", "contrato": "CTR-2024-008"},
]


def get_clients() -> list:
    return CLIENT_PROFILES


def get_client_by_id(client_id: int) -> dict | None:
    return next((c for c in CLIENT_PROFILES if c["id"] == client_id), None)


# ── Tick das ONUs ─────────────────────────────────────────────────────────────
def _push(arr: list, val, limit: int = 120):
    arr.append(val)
    if len(arr) > limit:
        arr.pop(0)


def _is_degraded(onu: dict) -> bool:
    return optical_thresholds.level("rxPower", onu["rxPower"], onu.get("ponMode")) in ("warn", "crit")


def _apply_real_reading(onu: dict, real: dict) -> bool:
    """ONU coberta pelo onu_web_poller: valores reais no lugar da simulação.
    Sem leitura recente (painel inacessível), a ONU é tratada como offline — o que
    dispara o mesmo alerta automático/trap de uma queda simulada.

    TODO: validar com respostas reais quais valores de `connectStatus` indicam link
    PON operacional (ex: estado O5) e usá-lo no lugar de "tem RxPower = online"."""
    from . import state as app_state

    reading = real["reading"]
    is_online = real["fresh"] and reading.get("rxPowerDbm") is not None
    if is_online != (onu["status"] == "online"):
        onu["status"] = "online" if is_online else "offline"
        onu["lastSeen"] = now_str_minutes()
        app_state.trigger_auto_alert("onuOnline" if is_online else "onuOffline", onu)
    if not is_online:
        return False

    onu["rxPower"] = round(reading["rxPowerDbm"], 2)
    if reading.get("txPowerDbm") is not None:
        onu["txPower"] = round(reading["txPowerDbm"], 2)
    if reading.get("temperatureC") is not None:
        onu["sfpTemp"] = round(reading["temperatureC"], 1)
    if reading.get("voltageV") is not None:
        onu["sfpVoltage"] = round(reading["voltageV"], 3)
    # O painel não informa latência nem BER — seguem simulados até haver fonte real.
    onu["latency"] = round(clamp(jitter(5 + onu["distance"] * 3, 1.5), 2, 80), 1)
    if reading.get("ponMode"):
        onu["ponMode"] = reading["ponMode"]
    onu["degraded"] = _is_degraded(onu)
    _push(onu["history"]["rxPower"], onu["rxPower"])
    _push(onu["history"]["latency"], onu["latency"])
    return True


def _tick_onus(elapsed: float) -> int:
    from . import state as app_state

    online_count = 0
    for onu in onu_state:
        onu["uptimeTicks"] += int(elapsed * 100)

        real = onu_web_poller.get_live_reading(onu["id"])
        if real is not None:
            online_count += _apply_real_reading(onu, real)
            continue

        if onu["offlineTimer"] > 0:
            onu["offlineTimer"] -= elapsed
            if onu["offlineTimer"] <= 0:
                onu["status"] = "online"
                onu["offlineTimer"] = 0
                onu["offlineCooldown"] = 30 + random.random() * 60
                onu["lastSeen"] = now_str_minutes()
                app_state.trigger_auto_alert("onuOnline", onu)
        else:
            offline_count = sum(1 for o in onu_state if o["status"] == "offline")
            if onu["status"] == "online" and onu["offlineCooldown"] <= 0 and offline_count < 2 and random.random() < 0.012:
                onu["status"] = "offline"
                onu["offlineTimer"] = 15 + random.random() * 25
                onu["lastSeen"] = now_str_minutes()
                app_state.trigger_auto_alert("onuOffline", onu)
            if onu["offlineCooldown"] > 0:
                onu["offlineCooldown"] -= elapsed

        if onu["status"] == "online":
            online_count += 1
            degrade_chance = random.random()
            if degrade_chance < 0.04:
                target_rx = onu["rxBase"] - (4 + random.random() * 4)
            elif degrade_chance < 0.10:
                target_rx = onu["rxBase"] - (1 + random.random() * 2)
            else:
                target_rx = onu["rxBase"]
            onu["rxPower"] = clamp(drift(onu["rxPower"], target_rx, 0.12, 0.25 + onu["distance"] * 0.1), -30, -10)
            onu["txPower"] = round(clamp(drift(onu["txPower"], 2.5, 0.05, 0.08), 0.5, 5.0), 2)
            temp_spike = (15 + random.random() * 15) if random.random() < 0.03 else 0
            onu["sfpTemp"] = round(clamp(drift(onu["sfpTemp"], 45 + temp_spike, 0.08, 0.5), 25, 85), 1)
            onu["sfpVoltage"] = round(clamp(drift(onu["sfpVoltage"], 3.3, 0.05, 0.003), 2.8, 3.8), 3)
            ber_spike = (random.random() * 1e-7) if random.random() < 0.04 else 0
            onu["ber"] = float(f"{max(0, drift(onu['ber'], 1e-11 + ber_spike, 0.1, 5e-12)):.2e}")
            onu["latency"] = round(clamp(jitter(5 + onu["distance"] * 3, 1.5), 2, 80), 1)
            onu["degraded"] = _is_degraded(onu)
            _push(onu["history"]["rxPower"], onu["rxPower"])
            _push(onu["history"]["latency"], onu["latency"])

    return online_count


def tick() -> dict:
    now = time.time()
    elapsed = now - snmp_state["lastTick"]
    snmp_state["lastTick"] = now
    snmp_state["uptime"] += int(elapsed * 100)

    snmp_state["anomalyTimer"] -= elapsed
    if snmp_state["anomalyTimer"] <= 0:
        if snmp_state["anomaly"]:
            snmp_state["anomaly"] = None
            snmp_state["anomalyTimer"] = 120 + random.random() * 180
        elif random.random() < 0.04:
            snmp_state["anomaly"] = {"type": "cpuSpike", "startedAt": datetime.now(timezone.utc).isoformat()}
            snmp_state["anomalyTimer"] = 15 + random.random() * 30
        else:
            snmp_state["anomalyTimer"] = 30

    cpu_target = 88 + random.random() * 10 if (snmp_state["anomaly"] or {}).get("type") == "cpuSpike" else 12
    snmp_state["cpuBase"] = clamp(drift(snmp_state["cpuBase"], cpu_target, 0.08, 3), 5, 95)
    cpu_now = round(jitter(snmp_state["cpuBase"], 3))
    snmp_state["memUsed"] = clamp(drift(snmp_state["memUsed"], 230, 0.02, 8), 150, 500)

    onus_online = _tick_onus(elapsed)
    online_onus = [o for o in onu_state if o["status"] == "online"]
    avg_rx_power = round(sum(o["rxPower"] for o in online_onus) / len(online_onus), 2) if online_onus else -25
    avg_latency = round(sum(o["latency"] for o in online_onus) / len(online_onus), 1) if online_onus else 50

    olt01_total = sum(1 for o in onu_state if o["gponPort"].startswith("0/1/"))
    olt01_online = sum(1 for o in onu_state if o["gponPort"].startswith("0/1/") and o["status"] == "online")
    in_rate = int(jitter(15000000, 8000000) * elapsed * (olt01_online / max(olt01_total, 1)))
    out_rate = int(jitter(5000000, 3000000) * elapsed * (olt01_online / max(olt01_total, 1)))
    snmp_state["ifInOctets"] = (snmp_state["ifInOctets"] + in_rate) % 4294967295
    snmp_state["ifOutOctets"] = (snmp_state["ifOutOctets"] + out_rate) % 4294967295
    snmp_state["ipInReceives"] = (snmp_state["ipInReceives"] + in_rate // 1400) % 4294967295
    snmp_state["ipOutRequests"] = (snmp_state["ipOutRequests"] + out_rate // 1400) % 4294967295

    if elapsed > 0.5:
        snmp_state["olts"][0]["inRate"] = round(in_rate / 125000, 2)
        snmp_state["olts"][0]["outRate"] = round(out_rate / 125000, 2)
    snmp_state["olts"][1]["inRate"] = round(clamp(drift(snmp_state["olts"][1]["inRate"], 280, 0.05, 30), 10, 2450), 2)
    snmp_state["olts"][1]["outRate"] = round(clamp(drift(snmp_state["olts"][1]["outRate"], 95, 0.05, 15), 5, 2450), 2)
    snmp_state["olts"][2]["inRate"] = round(clamp(drift(snmp_state["olts"][2]["inRate"], 620, 0.05, 80), 10, 9950), 2)
    snmp_state["olts"][2]["outRate"] = round(clamp(drift(snmp_state["olts"][2]["outRate"], 210, 0.05, 40), 5, 9950), 2)

    _push(snmp_state["history"]["rxPowerAvg"], avg_rx_power)
    _push(snmp_state["history"]["latencyAvg"], avg_latency)
    _push(snmp_state["history"]["traffic"], {"in": round(in_rate / 125000, 2), "out": round(out_rate / 125000, 2)})
    _push(snmp_state["history"]["onusOnline"], onus_online)

    # Sync devices
    from . import state as app_state
    olt_dev = app_state.find_device(100)
    if olt_dev:
        olt_dev["cpu"] = cpu_now
        olt_dev["memory"] = round((snmp_state["memUsed"] / 512) * 100)
        olt_dev["temperature"] = round(jitter(48, 2))
        olt_dev["uptime"] = uptime_to_string(snmp_state["uptime"])
        olt_dev["onus_active"] = olt01_online
        olt_dev["onus_total"] = olt01_total
    for onu in onu_state:
        dev = app_state.find_device(onu["id"])
        if dev:
            dev["status"] = onu["status"]
            dev["rxPower"] = onu["rxPower"]
            dev["txPower"] = onu["txPower"]
            dev["sfpTemp"] = onu["sfpTemp"]
            dev["sfpVoltage"] = onu["sfpVoltage"]
            dev["ber"] = onu["ber"]
            dev["latency"] = onu["latency"]
            dev["uptime"] = uptime_to_string(onu["uptimeTicks"])
            dev["ponMode"] = onu.get("ponMode", "GPON")

    return {
        "cpuNow": cpu_now, "inRate": in_rate, "outRate": out_rate,
        "onusOnline": onus_online, "avgRxPower": avg_rx_power, "avgLatency": avg_latency,
    }


def get_olts_bandwidth() -> list:
    result = []
    for i, olt in enumerate(OLTS):
        in_rate = snmp_state["olts"][i]["inRate"]
        out_rate = snmp_state["olts"][i]["outRate"]
        result.append({
            "id": olt["id"], "name": olt["name"], "model": olt["model"], "ip": olt["ip"],
            "capacity": olt["capacity"], "location": olt["location"], "vendor": olt["vendor"],
            "inRate": in_rate, "outRate": out_rate,
            "inPct": round(in_rate / olt["capacity"] * 100, 1),
            "outPct": round(out_rate / olt["capacity"] * 100, 1),
        })
    return result


def _onu_public(o: dict) -> dict:
    return {
        "id": o["id"], "apt": o["apt"], "client": o["client"], "serial": o["serial"], "ip": o["ip"],
        "model": o["model"], "gponPort": o["gponPort"], "port": f"{o['gponPort']}:{o['portSlot']}",
        "status": o["status"], "rxPower": o["rxPower"], "txPower": o["txPower"], "sfpTemp": o["sfpTemp"],
        "sfpVoltage": o["sfpVoltage"], "ber": o["ber"], "latency": o["latency"],
        "distance": f"{o['distance']} km", "uptime": uptime_to_string(o["uptimeTicks"]),
        "degraded": o["degraded"], "lastSeen": o["lastSeen"],
        "source": "real" if onu_web_poller.covers(o["id"]) else "mock",
        "ponMode": o.get("ponMode", "GPON"),
    }


def get_snapshot() -> dict:
    live = tick()
    olt01_total = sum(1 for o in onu_state if o["gponPort"].startswith("0/1/"))
    avail = round((live["onusOnline"] / len(onu_state)) * 100, 2)
    anomaly = snmp_state["anomaly"]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topology": {
            "nms": GPON_TOPOLOGY["nms"],
            "olt": {**GPON_TOPOLOGY["olt"], "cpu": live["cpuNow"],
                    "memory": round((snmp_state["memUsed"] / 512) * 100),
                    "uptime": uptime_to_string(snmp_state["uptime"])},
            "splitter": GPON_TOPOLOGY["splitter"],
            "onus": [_onu_public(o) for o in onu_state],
        },
        "device": {"name": "OLT Huawei MA5800-X2", "model": "MA5800-X2", "firmware": GPON_TOPOLOGY["olt"]["firmware"],
                    "serial": GPON_TOPOLOGY["olt"]["serial"], "uptime": uptime_to_string(snmp_state["uptime"]),
                    "uptimeTicks": snmp_state["uptime"], "location": "POP — Av. Principal, 1234",
                    "contact": "ti@provedor.com.br"},
        "system": {"cpu": live["cpuNow"], "memUsed": round(snmp_state["memUsed"]), "memTotal": 512,
                    "memPercent": round((snmp_state["memUsed"] / 512) * 100), "temperature": jitter(48, 2)},
        "optical": {"rxPower": live["avgRxPower"], "txPower": jitter(2.5, 0.15),
                     "rxPowerRaw": round(live["avgRxPower"] * 100), "txPowerRaw": 250,
                     "temperature": jitter(45, 2), "voltage": jitter(3295, 15),
                     "status": "online" if live["onusOnline"] >= 6 else ("degraded" if live["onusOnline"] >= 4 else "critical"),
                     "thresholds": {"rxMin": -27, "rxMax": -5, "txMin": 0.5, "txMax": 5},
                     "ber": float(f"{random.random() * 1e-10:.2e}")},
        "gpon": {"onusOnline": live["onusOnline"], "onusTotal": len(onu_state),
                  "onusOffline": len(onu_state) - live["onusOnline"], "avgRxPower": live["avgRxPower"],
                  "avgLatency": live["avgLatency"], "availability": avail,
                  "splitterLoss": GPON_TOPOLOGY["splitter"]["loss"]},
        "interfaces": [
            {"index": 1, "name": "gpon0/1/0", "descr": "GPON Uplink — OLT Porta 0/1/0", "type": "gpon",
             "speed": "2.5 Gbps", "status": "up", "inOctets": snmp_state["ifInOctets"],
             "outOctets": snmp_state["ifOutOctets"], "inRate": round(live["inRate"] / 125000, 2),
             "outRate": round(live["outRate"] / 125000, 2), "inErrors": 0, "outErrors": 0},
            {"index": 2, "name": "ge0/0/0", "descr": "Uplink GbE — Core Router", "type": "ethernet",
             "speed": "1 Gbps", "status": "up", "inRate": jitter(80, 40), "outRate": jitter(30, 15)},
        ],
        "anomaly": ({**anomaly, "description": f"CPU OLT em {live['cpuNow']}% — atualização de tabela MAC",
                     "severity": "warning"} if anomaly else None),
        "ip": {"wan": "189.112.xx.xx", "gateway": "189.112.xx.1", "dns1": "8.8.8.8", "dns2": "1.1.1.1",
               "inPackets": snmp_state["ipInReceives"], "outPackets": snmp_state["ipOutRequests"]},
        "wifi": {"band24": {"clients": 0}, "band5": {"clients": 0}},
    }


def get_history() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "points": len(snmp_state["history"]["rxPowerAvg"]),
        "intervalSeconds": 5,
        "rxPower": list(snmp_state["history"]["rxPowerAvg"]),
        "latency": list(snmp_state["history"]["latencyAvg"]),
        "traffic": list(snmp_state["history"]["traffic"]),
        "onusOnline": list(snmp_state["history"]["onusOnline"]),
        "onuRxHistory": [{"id": o["id"], "apt": o["apt"], "client": o["client"], "current": o["rxPower"],
                           "ponMode": o.get("ponMode", "GPON"), "history": list(o["history"]["rxPower"])} for o in onu_state],
    }


def get_onus(port: str | None = None) -> list:
    all_onus = [_onu_public(o) for o in onu_state]
    return [o for o in all_onus if o["gponPort"] == port] if port else all_onus


def get_gpon_ports() -> list:
    by_port: dict = {}
    for o in onu_state:
        p = o["gponPort"]
        entry = by_port.setdefault(p, {"online": 0, "total": 0, "rxSum": 0, "rxCount": 0, "latSum": 0, "latCount": 0})
        entry["total"] += 1
        if o["status"] == "online":
            entry["online"] += 1
            entry["rxSum"] += o["rxPower"]
            entry["rxCount"] += 1
            entry["latSum"] += o["latency"]
            entry["latCount"] += 1

    result = []
    for p in GPON_PORTS:
        s = by_port.get(p["id"], {"online": 0, "total": 0, "rxSum": 0, "rxCount": 0, "latSum": 0, "latCount": 0})
        result.append({
            **p,
            "onusOnline": s["online"], "onusTotal": s["total"],
            "avgRxPower": round(s["rxSum"] / s["rxCount"], 2) if s["rxCount"] else None,
            "avgLatency": round(s["latSum"] / s["latCount"], 1) if s["latCount"] else None,
        })
    return result


def add_olt(data: dict) -> dict:
    from . import state as app_state

    idx = len(OLTS)
    olt_id = data.get("id") or f"OLT-{idx + 1:02d}"
    olt = {
        "id": olt_id, "name": data.get("name") or olt_id, "ip": data["ip"],
        "model": data.get("model") or "Unknown", "vendor": data.get("vendor") or "Unknown",
        "capacity": int(data.get("capacity") or 2500), "location": data.get("location") or "Não especificado",
        "maxONUs": 128,
    }
    OLTS.append(olt)
    port_slot = len(OLTS)
    port_id = f"0/{port_slot}/0"
    GPON_PORTS.append({"id": port_id, "oltId": olt_id, "name": f"{olt_id} / GPON {port_id}",
                        "description": "Porta principal", "maxONUs": 8})
    snmp_state["olts"].append({"inRate": 0, "outRate": 0})
    dev = {
        "id": app_state.next_device_id(), "name": data.get("name") or f"{olt_id} — {olt['model']}", "ip": olt["ip"], "type": "OLT",
        "status": "online", "cpu": 0, "memory": 0, "temperature": 0, "onus_active": 0, "onus_total": 0,
        "vendor": olt["vendor"], "location": olt["location"], "firmware": "Unknown", "uptime": "0d 00:00:00",
    }
    app_state.appState["devices"].append(dev)
    app_state.add_history({"event": f"OLT Adicionada — {olt_id}", "device": olt_id, "duration": "--",
                            "action": f"IP: {olt['ip']}", "user": "admin", "type": "device"})
    return dev


def add_onu(data: dict) -> dict:
    from . import state as app_state

    new_id = max([o["id"] for o in ONU_PROFILES], default=0) + 1
    port_slot = sum(1 for p in ONU_PROFILES if p["gponPort"] == data["gponPort"])
    profile = {
        "id": new_id, "client": data.get("client") or "Novo Cliente",
        "apt": data.get("apt") or f"Unidade {new_id}", "serial": data.get("serial") or f"NEW-ONU-{new_id:06d}",
        "ip": data.get("ip") or "", "model": data.get("model") or "HG8245Q2",
        "distance": float(data.get("distance") or 0.5), "rxBase": -18,
        "gponPort": data["gponPort"], "portSlot": port_slot,
    }
    ONU_PROFILES.append(profile)
    onu_state.append({
        **profile, "status": "online", "rxPower": profile["rxBase"], "txPower": 2.5,
        "sfpTemp": round(jitter(45, 3), 1), "sfpVoltage": round(jitter(3.3, 0.05), 3),
        "ber": round(random.random() * 5e-11, 15), "latency": round(5 + profile["distance"] * 3, 1),
        "uptimeTicks": 0, "offlineTimer": 0, "offlineCooldown": 0, "degraded": False,
        "lastSeen": now_str_minutes(),
        "history": {
            "rxPower": [jitter(profile["rxBase"], 0.4) for _ in range(120)],
            "latency": [jitter(5 + profile["distance"] * 3, 1.5) for _ in range(120)],
        },
    })
    dev = {
        "id": new_id, "name": f"ONU — {profile['apt']}", "client": profile["client"], "apt": profile["apt"],
        "ip": profile["ip"], "serial": profile["serial"], "model": profile["model"], "type": "ONU",
        "status": "online", "rxPower": profile["rxBase"], "txPower": 2.5,
        "latency": round(5 + profile["distance"] * 3, 1), "distance": f"{profile['distance']} km",
        "uptime": "0d 00:00:00", "gponPort": profile["gponPort"], "port": f"{profile['gponPort']}:{profile['portSlot']}",
    }
    app_state.appState["devices"].append(dev)
    app_state.add_history({"event": f"ONU Adicionada — {profile['apt']}", "device": profile["serial"],
                            "duration": "--", "action": f"Porta {profile['gponPort']} • IP: {profile['ip']}",
                            "user": "admin", "type": "device"})
    return dev
