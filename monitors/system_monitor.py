"""CPU and RAM monitoring via psutil."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import psutil
except Exception:  # pragma: no cover - psutil is a hard requirement
    psutil = None  # type: ignore[assignment]


_BYTES_PER_GB = 1024 ** 3


class SystemMonitor:
    """Collects CPU and memory statistics. Never raises on read errors."""

    def __init__(self) -> None:
        # Prime the non-blocking CPU counter so the first reading is meaningful.
        try:
            if psutil is not None:
                psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Optional[float]]:
        stats: Dict[str, Optional[float]] = {
            "cpu_percent": None,
            "ram_percent": None,
            "ram_used_gb": None,
            "ram_total_gb": None,
        }
        if psutil is None:
            return stats

        try:
            stats["cpu_percent"] = float(psutil.cpu_percent(interval=None))
        except Exception:
            pass

        try:
            memory = psutil.virtual_memory()
            stats["ram_percent"] = float(memory.percent)
            stats["ram_used_gb"] = round(memory.used / _BYTES_PER_GB, 1)
            stats["ram_total_gb"] = round(memory.total / _BYTES_PER_GB, 1)
        except Exception:
            pass

        return stats
