"""Ollama model discovery via its local HTTP API."""

from __future__ import annotations

from typing import Dict, List

try:
    import requests
except Exception:  # pragma: no cover - requests is a hard requirement
    requests = None  # type: ignore[assignment]


OLLAMA_URL = "http://localhost:11434/api/ps"
TIMEOUT_SECONDS = 0.5


def _device_label(entry: dict) -> str | None:
    """Derive the CPU/GPU offload split for a loaded model.

    Ollama reports the total model size (``size``) and the part resident in VRAM
    (``size_vram``) in bytes, which is what ``ollama ps`` renders as the
    PROCESSOR column, e.g. ``61%/39% CPU/GPU``.
    """
    if "size_vram" not in entry or entry.get("size_vram") is None:
        return None
    try:
        total = float(entry.get("size") or 0)
        vram = float(entry["size_vram"])
    except (TypeError, ValueError):
        return None
    if total <= 0:
        return None
    gpu_percent = max(0, min(100, int(round(vram / total * 100))))
    cpu_percent = 100 - gpu_percent
    if gpu_percent >= 100:
        return "100% GPU"
    if cpu_percent >= 100:
        return "100% CPU"
    return f"{cpu_percent}%/{gpu_percent}% CPU/GPU"


def get_models(timeout: float = TIMEOUT_SECONDS) -> List[Dict[str, object]]:
    """Return currently loaded Ollama models, or ``[]`` if unavailable."""
    models: List[Dict[str, object]] = []
    if requests is None:
        return models
    try:
        response = requests.get(OLLAMA_URL, timeout=timeout)
        if response.status_code != 200:
            return models
        payload = response.json()
        for entry in payload.get("models", []) or []:
            name = entry.get("name") or entry.get("model")
            if not name:
                continue
            model: Dict[str, object] = {"name": str(name), "source": "Ollama"}
            device = _device_label(entry)
            if device:
                model["device"] = device

            # The actual context the loaded instance runs with, NOT the
            # model's maximum (which /api/show reports under model_info).
            context_length = entry.get("context_length")
            if context_length:
                try:
                    model["ctx"] = int(context_length)
                except (TypeError, ValueError):
                    pass

            details = entry.get("details") or {}
            for key, label in (
                ("parameter_size", "params"),
                ("quantization_level", "quant"),
                ("family", "family"),
            ):
                value = details.get(key)
                if value:
                    model[label] = str(value)

            models.append(model)
    except Exception:
        return []
    return models
