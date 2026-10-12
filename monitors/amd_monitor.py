"""AMD GPU monitoring with layered fallbacks.

Linux
   1. ``rocm-smi`` (if present) with JSON output.
   2. ``/sys/class/drm/card*/device`` sysfs walk (vendor id ``0x1002``).
Windows
   PowerShell/WMI ``Win32_VideoController`` for name and total VRAM.
   Live load / used VRAM / temperature are usually not reliably available
   without extra vendor APIs and are therefore reported as ``None`` (n/a).

Nothing here may raise: every probe is guarded and failures yield ``[]``.
"""

from __future__ import annotations

import glob
import json
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

_BYTES_PER_GB = 1024 ** 3
_AMD_VENDOR_ID = "0x1002"
_ROCM_TIMEOUT = 1.5
_POWERSHELL_TIMEOUT = 4.0

_AMD_NAME_TOKENS = (
    "amd",
    "radeon",
    " rx ",
    "rx ",
    "vega",
    "ryzen",
    "firepro",
    "instinct",
    "ati ",
)


def _parse_number(value: Any) -> Optional[float]:
    """Extract the first float from a value like ``"18"`` or ``"67.0 C"``."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
    except Exception:
        return None
    try:
        match = re.search(r"-?\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else None
    except Exception:
        return None


def _first_value(container: Dict[str, Any], *needles: str) -> Optional[Any]:
    """Return the value of the first key containing all ``needles`` (case-insensitive)."""
    for key, value in container.items():
        lowered = str(key).lower()
        if all(needle in lowered for needle in needles):
            return value
    return None


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    except (OSError, ValueError):
        return None


def _read_number(path: str) -> Optional[float]:
    text = _read_text(path)
    return _parse_number(text)


def _which(*names: str) -> Optional[str]:
    for name in names:
        try:
            found = shutil.which(name)
            if found:
                return found
        except Exception:
            continue
    return None


class AmdMonitor:
    """Detects AMD GPUs on Linux and Windows."""

    def __init__(self) -> None:
        try:
            self._system = platform.system().lower()
        except Exception:
            self._system = ""

    def get_gpus(self) -> List[Dict[str, Optional[float]]]:
        try:
            if self._system == "linux":
                return self._linux_gpus()
            if self._system == "windows":
                return self._windows_gpus()
        except Exception:
            return []
        return []

    # ------------------------------------------------------------------ Linux

    def _linux_gpus(self) -> List[Dict[str, Optional[float]]]:
        gpus = self._linux_rocm()
        if gpus:
            return gpus
        return self._linux_sysfs()

    def _linux_rocm(self) -> List[Dict[str, Optional[float]]]:
        tool = _which("rocm-smi")
        if not tool:
            return []

        stdout = self._run(
            [
                tool,
                "--showuse",
                "--showmemuse",
                "--showtemp",
                "--showproductname",
                "--showmeminfo",
                "vram",
                "--json",
            ],
            _ROCM_TIMEOUT,
        )
        data = self._loads_json(stdout)
        if not isinstance(data, dict):
            return []

        gpus: List[Dict[str, Optional[float]]] = []
        for card_key in sorted(data.keys()):
            card = data.get(card_key)
            if not isinstance(card, dict):
                continue
            if not any("gpu use" in k.lower() or "card" in k.lower() for k in card):
                continue
            gpu = self._rocm_card_to_gpu(card)
            if gpu is not None:
                gpus.append(gpu)
        return gpus

    @staticmethod
    def _rocm_card_to_gpu(card: Dict[str, Any]) -> Optional[Dict[str, Optional[float]]]:
        name = (
            _first_value(card, "card series")
            or _first_value(card, "card product name")
            or _first_value(card, "card model")
        )
        if isinstance(name, str) and name.lower().startswith("0x"):
            name = None

        vram_used = _parse_number(_first_value(card, "vram", "used"))
        vram_total = _parse_number(_first_value(card, "vram", "total"))
        if vram_used is None:
            # Older rocm-smi may only expose used bytes as "VRAM Total Used Memory (B)".
            vram_used = _parse_number(_first_value(card, "used memory"))

        temperature = (
            _parse_number(_first_value(card, "temperature", "edge"))
            or _parse_number(_first_value(card, "temperature", "junction"))
            or _parse_number(_first_value(card, "temperature"))
        )

        gpu: Dict[str, Optional[float]] = {
            "vendor": "AMD",
            "name": name or "AMD GPU",
            "load_percent": _parse_number(_first_value(card, "gpu use")),
            "vram_used_gb": (
                round(vram_used / _BYTES_PER_GB, 1) if vram_used is not None else None
            ),
            "vram_total_gb": (
                round(vram_total / _BYTES_PER_GB, 1)
                if vram_total is not None
                else None
            ),
            "temperature_c": temperature,
        }
        return gpu

    def _linux_sysfs(self) -> List[Dict[str, Optional[float]]]:
        gpus: List[Dict[str, Optional[float]]] = []
        try:
            cards = sorted(glob.glob("/sys/class/drm/card[0-9]*"))
        except Exception:
            return gpus

        for card in cards:
            device = os.path.join(card, "device")
            if not os.path.isdir(device):
                continue
            vendor = _read_text(os.path.join(device, "vendor"))
            if not vendor or vendor.strip().lower() != _AMD_VENDOR_ID:
                continue
            gpus.append(self._sysfs_card_to_gpu(device))
        return gpus

    @staticmethod
    def _sysfs_card_to_gpu(device: str) -> Dict[str, Optional[float]]:
        name = _read_text(os.path.join(device, "product_name"))
        if not name:
            device_id = _read_text(os.path.join(device, "device"))
            if device_id:
                name = f"AMD GPU ({device_id})"

        vram_total = _read_number(os.path.join(device, "mem_info_vram_total"))
        vram_used = _read_number(os.path.join(device, "mem_info_vram_used"))

        temperature = None
        for temp_file in sorted(
            glob.glob(os.path.join(device, "hwmon", "hwmon*", "temp1_input"))
        ):
            raw = _read_number(temp_file)
            if raw is not None:
                temperature = round(raw / 1000.0, 1)
                break

        load = _read_number(os.path.join(device, "gpu_busy_percent"))

        return {
            "vendor": "AMD",
            "name": name or "AMD GPU",
            "load_percent": load,
            "vram_used_gb": (
                round(vram_used / _BYTES_PER_GB, 1) if vram_used is not None else None
            ),
            "vram_total_gb": (
                round(vram_total / _BYTES_PER_GB, 1)
                if vram_total is not None
                else None
            ),
            "temperature_c": temperature,
        }

    # ---------------------------------------------------------------- Windows

    def _windows_gpus(self) -> List[Dict[str, Optional[float]]]:
        shell = _which("powershell", "pwsh")
        if not shell:
            return []

        command = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,AdapterRAM | ConvertTo-Json -Compress"
        )
        stdout = self._run([shell, "-NoProfile", "-Command", command], _POWERSHELL_TIMEOUT)
        if not stdout:
            return []

        data = self._loads_json(stdout)
        if data is None:
            return []
        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data
        else:
            return []

        gpus: List[Dict[str, Optional[float]]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("Name")
            if not isinstance(name, str) or not name:
                continue
            if not any(token in name.lower() for token in _AMD_NAME_TOKENS):
                continue

            adapter_ram = _parse_number(entry.get("AdapterRAM"))
            total_gb = (
                round(adapter_ram / _BYTES_PER_GB, 1)
                if adapter_ram is not None
                else None
            )
            gpus.append(
                {
                    "vendor": "AMD",
                    "name": name,
                    "load_percent": None,
                    "vram_used_gb": None,
                    "vram_total_gb": total_gb,
                    "temperature_c": None,
                }
            )
        return gpus

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _run(command: List[str], timeout: float) -> str:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return completed.stdout or ""
        except Exception:
            return ""

    @staticmethod
    def _loads_json(text: str) -> Any:
        if not text:
            return None
        start = text.find("{")
        if start == -1:
            start = text.find("[")
        if start == -1:
            return None
        try:
            return json.loads(text[start:])
        except (ValueError, TypeError):
            return None
