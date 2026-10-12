"""Platform and tool detection helpers.

All functions are best-effort and never raise; they are intended for logging,
diagnostics and optional GPU enumeration.
"""

from __future__ import annotations

import platform
import shutil
from typing import Any, Dict, List, Optional


def detect_platform() -> str:
    """Return the lower-case platform name (``linux``/``windows``/``darwin``)."""
    try:
        return platform.system().lower()
    except Exception:
        return "unknown"


def detect_tools() -> Dict[str, bool]:
    """Report whether common external tools are on PATH."""
    result = {"nvidia-smi": False, "rocm-smi": False, "powershell": False}
    try:
        result["nvidia-smi"] = shutil.which("nvidia-smi") is not None
        result["rocm-smi"] = shutil.which("rocm-smi") is not None
        result["powershell"] = (
            shutil.which("powershell") is not None
            or shutil.which("pwsh") is not None
        )
    except Exception:
        pass
    return result


def list_gpus(config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Enumerate GPUs using the unified monitor. Returns ``[]`` on any failure."""
    try:
        from .gpu_monitor import GpuMonitor

        monitor = GpuMonitor(config or {})
        try:
            return monitor.get_gpu_stats()
        finally:
            monitor.close()
    except Exception:
        return []
