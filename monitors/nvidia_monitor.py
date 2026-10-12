"""NVIDIA GPU monitoring via NVML (nvidia-ml-py).

Every NVML call is wrapped so a missing package, a missing driver or a missing
GPU degrades to ``None``/empty results instead of raising.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

try:
    import pynvml  # provided by the nvidia-ml-py package
except Exception:  # pragma: no cover - optional dependency
    pynvml = None  # type: ignore[assignment]


_BYTES_PER_GB = 1024 ** 3


class NvidiaMonitor:
    """Enumerates NVIDIA GPUs through NVML."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._available = False
        self._inited = False
        self._count = 0
        self._handles: List[Any] = []

        if pynvml is None:
            return

        try:
            pynvml.nvmlInit()
            self._inited = True
            self._count = int(pynvml.nvmlDeviceGetCount())
            self._handles = [
                pynvml.nvmlDeviceGetHandleByIndex(index)
                for index in range(self._count)
            ]
            self._available = self._count > 0
        except Exception:
            self._available = False
            self._shutdown()

    @property
    def available(self) -> bool:
        return self._available

    def get_gpus(self) -> List[Dict[str, Optional[float]]]:
        if not self._available:
            return []
        gpus: List[Dict[str, Optional[float]]] = []
        with self._lock:
            for index, handle in enumerate(self._handles):
                gpus.append(self._gpu_info(handle))
        return gpus

    def _gpu_info(self, handle: Any) -> Dict[str, Optional[float]]:
        info: Dict[str, Optional[float]] = {
            "vendor": "NVIDIA",
            "name": None,
            "load_percent": None,
            "vram_used_gb": None,
            "vram_total_gb": None,
            "temperature_c": None,
        }

        try:
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            info["name"] = str(name)
        except Exception:
            pass

        try:
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            info["load_percent"] = float(utilization.gpu)
        except Exception:
            pass

        try:
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["vram_used_gb"] = round(memory.used / _BYTES_PER_GB, 1)
            info["vram_total_gb"] = round(memory.total / _BYTES_PER_GB, 1)
        except Exception:
            pass

        try:
            info["temperature_c"] = float(
                pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            )
        except Exception:
            pass

        return info

    def _shutdown(self) -> None:
        if pynvml is None or not self._inited:
            return
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
        finally:
            self._inited = False

    def close(self) -> None:
        with self._lock:
            self._shutdown()
        self._available = False
        self._handles = []
