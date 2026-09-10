import time

from . import mock_engine, trap_engine

_last_snapshot: dict | None = None
_last_snapshot_at: float = 0.0


def get_cached_snapshot() -> dict:
    """Cacheia o último snapshot por até 2s (evita recomputar a cada sub-rota que
    responde ao mesmo poll de 5s do frontend) e dispara a avaliação de traps sempre
    que o cache é renovado — mesmo acoplamento existente no server.js original."""
    global _last_snapshot, _last_snapshot_at
    now = time.time()
    if _last_snapshot is None or now - _last_snapshot_at > 2:
        _last_snapshot = mock_engine.get_snapshot()
        _last_snapshot_at = now
        trap_engine.evaluate_traps(_last_snapshot)
    return _last_snapshot
