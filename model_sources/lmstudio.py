"""LM Studio model discovery via its OpenAI-compatible local API."""

from __future__ import annotations

from typing import Dict, List

try:
    import requests
except Exception:  # pragma: no cover - requests is a hard requirement
    requests = None  # type: ignore[assignment]


LMSTUDIO_V0_URL = "http://localhost:1234/api/v0/models"
LMSTUDIO_URL = "http://localhost:1234/v1/models"
TIMEOUT_SECONDS = 0.5


def get_models(timeout: float = TIMEOUT_SECONDS) -> List[Dict[str, object]]:
    """Return models exposed by a running LM Studio server, else ``[]``.

    Prefers the native REST API (``/api/v0/models``), which reports the loaded
    context length, quantization and architecture per model, and falls back to
    the OpenAI-compatible ``/v1/models`` listing.
    """
    models = _get_models_v0(timeout)
    if models:
        return models
    return _get_models_v1(timeout)


def _get_models_v0(timeout: float) -> List[Dict[str, object]]:
    models: List[Dict[str, object]] = []
    if requests is None:
        return models
    try:
        response = requests.get(LMSTUDIO_V0_URL, timeout=timeout)
        if response.status_code != 200:
            return models
        payload = response.json()
        for entry in payload.get("data", []) or []:
            identifier = entry.get("id")
            if not identifier:
                continue
            model: Dict[str, object] = {"name": str(identifier), "source": "LM Studio"}
            if entry.get("arch"):
                model["family"] = str(entry["arch"])
            if entry.get("quantization"):
                model["quant"] = str(entry["quantization"])
            loaded_ctx = entry.get("loaded_context_length")
            if loaded_ctx:
                try:
                    model["ctx"] = int(loaded_ctx)
                except (TypeError, ValueError):
                    pass
            models.append(model)
    except Exception:
        return []
    return models


def _get_models_v1(timeout: float) -> List[Dict[str, object]]:
    models: List[Dict[str, object]] = []
    if requests is None:
        return models
    try:
        response = requests.get(LMSTUDIO_URL, timeout=timeout)
        if response.status_code != 200:
            return models
        payload = response.json()
        for entry in payload.get("data", []) or []:
            identifier = entry.get("id")
            if identifier:
                models.append({"name": str(identifier), "source": "LM Studio"})
    except Exception:
        return []
    return models
