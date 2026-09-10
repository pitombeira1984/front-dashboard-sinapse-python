from datetime import datetime


def now_str_minutes() -> str:
    """Equivalente a nowStr() do mock-engine.js: 'DD/MM/AAAA HH:MM'."""
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def now_str_seconds() -> str:
    """Equivalente a nowStr() do trap-engine.js: 'DD/MM/AAAA HH:MM:SS'."""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def uptime_to_string(ticks: float) -> str:
    """ticks em centésimos de segundo -> 'Xd HH:MM:SS'."""
    s = int(ticks // 100)
    days = s // 86400
    hours = (s % 86400) // 3600
    minutes = (s % 3600) // 60
    seconds = s % 60
    return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
