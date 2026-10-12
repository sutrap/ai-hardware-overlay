"""Unified GPU interface aggregating NVIDIA and AMD monitors."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .amd_monitor import AmdMonitor
from .nvidia_monitor import NvidiaMonitor


class GpuMonitor:
    """Provides a single ``get_gpu_stats()`` returning a normalized GPU list."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.nvidia = NvidiaMonitor()
        self.amd = AmdMonitor()

    def get_gpu_stats(self) -> List[Dict[str, Optional[float]]]:
        gpus: List[Dict[str, Optional[float]]] = []

        if self.config.get("show_nvidia", True):
            try:
                gpus.extend(self.nvidia.get_gpus())
            except Exception:
                pass

        if self.config.get("show_amd", True):
            try:
                gpus.extend(self.amd.get_gpus())
            except Exception:
                pass

        return gpus

    def close(self) -> None:
        try:
            self.nvidia.close()
        except Exception:
            pass
