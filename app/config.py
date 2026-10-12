"""Configuration loading and persistence.

The application keeps a single ``config.json`` next to ``main.py``. Missing or
corrupt files fall back to ``DEFAULTS`` so the app always starts. Writes are
atomic (temp file + ``os.replace``) to avoid leaving a truncated config behind.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict


DEFAULTS: Dict[str, Any] = {
    "refresh_interval_ms": 1000,
    "opacity": 0.85,
    "window_x": 50,
    "window_y": 50,
    "font_size": 13,
    "show_ollama": True,
    "show_lmstudio": True,
    "show_llamacpp_processes": True,
    "show_nvidia": True,
    "show_amd": True,
    "max_model_name_length": 60,
    "model_detail_fields": ["ctx", "quant", "params"],
}


def project_root() -> str:
    """Return the project root (the directory that contains ``main.py``)."""
    here = os.path.dirname(os.path.abspath(__file__))  # .../app
    return os.path.dirname(here)


def config_path() -> str:
    """Return the default path of ``config.json`` (next to ``main.py``)."""
    return os.path.join(project_root(), "config.json")


def _coerce(key: str, value: Any) -> Any:
    """Best-effort type coercion of a config value to the default's type."""
    default = DEFAULTS[key]
    try:
        if isinstance(default, bool):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if isinstance(default, int):
            return int(value)
        if isinstance(default, float):
            return float(value)
    except (TypeError, ValueError):
        return default
    return value


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load config, merged over DEFAULTS. Never raises."""
    path = path or config_path()
    config: Dict[str, Any] = dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            for key, value in loaded.items():
                if key in DEFAULTS:
                    config[key] = _coerce(key, value)
                else:
                    config[key] = value
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError, TypeError):
        pass
    return config


def save_config(config: Dict[str, Any], path: str | None = None) -> bool:
    """Atomically write config to disk. Returns True on success."""
    path = path or config_path()
    directory = os.path.dirname(os.path.abspath(path)) or "."
    try:
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".config-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(tmp_path, path)
            return True
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except (OSError, ValueError):
        return False
