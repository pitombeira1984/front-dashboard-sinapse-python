"""Limites ópticos por tecnologia PON — fonte única para tudo que avalia uma ONU
individual: estado "degradado" (mock_engine), traps de degradação óptica
(trap_engine) e cores da UI (exposto ao navegador como
window.SINAPSE_OPTICAL_THRESHOLDS, usado por utils.js/dashboard.js/devices.js/
analysis.js, e aos templates Jinja via a global `optical_color`).

Cada grandeza tem até quatro limites: crit* = limite da norma/fabricante, warn* =
margem de aviso antes dele. A tecnologia vem do `ponMode` da ONU (lido do painel
na ONU real; "GPON" nas simuladas).
"""

OPTICAL_THRESHOLDS = {
    # ITU-T G.984.2 classe B+ — mesmos valores já usados pelo protótipo nas ONUs simuladas.
    "GPON": {
        "rxPower": {"critLow": -27, "warnLow": -24, "critHigh": -8},
        "txPower": {"critLow": 0.5, "warnLow": 1.0, "critHigh": 5.0},
        "temperature": {"warnHigh": 50, "critHigh": 70},
        "voltage": {"critLow": 3.0, "warnLow": 3.1, "warnHigh": 3.5, "critHigh": 3.6},
    },
    # ITU-T G.9807.1 classe N1: Rx sensibilidade -28 dBm / sobrecarga -9 dBm; Tx
    # (upstream 9,95 Gbit/s) +4 a +9 dBm. Temperatura: DDM do módulo óptico, que em
    # ONTs XGS-PON opera tipicamente na faixa de 60-75 °C; alarmes de fabricante
    # costumam ficar em 85-90 °C — confirmar no datasheet do equipamento.
    "XGS-PON": {
        "rxPower": {"critLow": -28, "warnLow": -25, "warnHigh": -10, "critHigh": -9},
        "txPower": {"critLow": 4.0, "warnLow": 4.5, "warnHigh": 8.5, "critHigh": 9.0},
        "temperature": {"warnHigh": 80, "critHigh": 90},
        "voltage": {"critLow": 3.0, "warnLow": 3.1, "warnHigh": 3.5, "critHigh": 3.6},
    },
}

_LEVEL_COLORS = {"crit": "var(--danger-color)", "warn": "var(--warning-color)", "ok": "var(--success-color)"}


def profile_name(pon_mode: str | None) -> str:
    return "XGS-PON" if pon_mode and "XGS" in pon_mode.upper() else "GPON"


def level(metric: str, value, pon_mode: str | None = None) -> str | None:
    """"crit" | "warn" | "ok", ou None se não houver valor/limite para a grandeza."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    limits = OPTICAL_THRESHOLDS[profile_name(pon_mode)].get(metric)
    if not limits:
        return None
    if value < limits.get("critLow", float("-inf")) or value > limits.get("critHigh", float("inf")):
        return "crit"
    if value < limits.get("warnLow", float("-inf")) or value > limits.get("warnHigh", float("inf")):
        return "warn"
    return "ok"


def color(metric: str, value, pon_mode: str | None = None) -> str:
    return _LEVEL_COLORS.get(level(metric, value, pon_mode), "var(--text-primary)")
