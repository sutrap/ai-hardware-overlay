"""Aggregate all enabled model sources into one deduplicated list."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from . import llamacpp_process, lmstudio, ollama


class ModelDetector:
    """Collects models from every source enabled in the configuration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}

    def get_models(self) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []

        if self.config.get("show_ollama", True):
            results.extend(self._safe(ollama.get_models))
        if self.config.get("show_lmstudio", True):
            results.extend(self._safe(lmstudio.get_models))
        if self.config.get("show_llamacpp_processes", True):
            results.extend(self._safe(llamacpp_process.get_models))

        seen: set = set()
        deduplicated: List[Dict[str, str]] = []
        for model in results:
            key = (model.get("name"), model.get("source"))
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(model)
        return deduplicated

    @staticmethod
    def _safe(func: Callable[[], List[Dict[str, str]]]) -> List[Dict[str, str]]:
        try:
            result = func()
            return result if isinstance(result, list) else []
        except Exception:
            return []
