"""Detect llama.cpp / KoboldCpp style processes and their ``.gguf`` models.

Only the basename of a ``.gguf`` file is reported, never the full path.
Unreadable or vanished processes are skipped silently.

Matching is deliberately precise: the ``llama`` keyword is matched with word
boundaries against the process name / argv[0] (so ``ollama`` does NOT match),
while a ``.gguf`` argument is detected anywhere on the command line.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Set, Tuple

try:
    import psutil
except Exception:  # pragma: no cover - psutil is a hard requirement
    psutil = None  # type: ignore[assignment]


# Matches llama-server, llama-cli, koboldcpp and a bare "llama" binary, but not
# substrings such as "ollama".
_NAME_PATTERN = re.compile(r"\b(llama-server|llama-cli|koboldcpp|llama)\b", re.IGNORECASE)

# Context-size CLI options: `-c`, `--ctx-size`, `--ctx`, `--context-length`.
_CTX_OPTIONS = ("-c", "--ctx-size", "--ctx", "--context-size", "--context-length")
_NGL_OPTIONS = ("-ngl", "--n-gpu-layers", "--gpu-layers")

_QUANT_PATTERN = re.compile(
    r"(?:[^a-zA-Z0-9]|^)([a-z]?q\d+(?:_[a-z0-9]+)*|bf16|f(?:p)?(?:8|16|32|64))(?:[^a-zA-Z0-9]|$)",
    re.IGNORECASE,
)
_PARAMS_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?x)?\d+(?:\.\d+)?[bB]\b")


def _basename(value: str) -> str:
    try:
        return os.path.basename(value)
    except Exception:
        return value


def _int_option(cmdline: list, names: tuple) -> Optional[int]:
    """Return the integer value of the first CLI option in ``names``."""
    for index, token in enumerate(cmdline):
        for name in names:
            if token == name:
                if index + 1 < len(cmdline):
                    try:
                        return int(cmdline[index + 1])
                    except (TypeError, ValueError):
                        return None
            elif token.startswith(name + "="):
                try:
                    return int(token.split("=", 1)[1])
                except (TypeError, ValueError):
                    return None
    return None


def _model_meta_from_gguf(filename: str) -> Dict[str, str]:
    """Best-effort quantization and parameter size from a .gguf basename."""
    meta: Dict[str, str] = {}
    base = _basename(filename)

    quant_match = _QUANT_PATTERN.search(base)
    if quant_match:
        meta["quant"] = quant_match.group(1).upper()

    params_match = _PARAMS_PATTERN.search(base)
    if params_match:
        meta["params"] = params_match.group(0).upper()

    return meta


def get_models() -> List[Dict[str, object]]:
    models: List[Dict[str, object]] = []
    if psutil is None:
        return models

    seen: Set[Tuple[str, str]] = set()
    try:
        iterator = psutil.process_iter(["name", "cmdline"])
    except Exception:
        return models

    for process in iterator:
        try:
            info = process.info
            name = str(info.get("name") or "")
            cmdline = info.get("cmdline") or []
        except Exception:
            continue

        try:
            argv0 = _basename(str(cmdline[0])) if cmdline else ""
            identity = f"{name} {argv0}"
            match = _NAME_PATTERN.search(identity)

            found_gguf = [
                _basename(str(part))
                for part in cmdline
                if str(part).lower().endswith(".gguf")
            ]

            if not found_gguf and match is None:
                continue

            ctx = _int_option(cmdline, _CTX_OPTIONS)
            ngl = _int_option(cmdline, _NGL_OPTIONS)

            if found_gguf:
                for filename in found_gguf:
                    key = ("llama.cpp", filename)
                    if key not in seen:
                        seen.add(key)
                        model: Dict[str, object] = {
                            "name": filename,
                            "source": "llama.cpp",
                        }
                        _merge_meta(model, _model_meta_from_gguf(filename), ctx, ngl)
                        models.append(model)
                continue

            keyword = match.group(1).lower() if match else ""
            source = "koboldcpp" if keyword == "koboldcpp" else "llama.cpp"
            label = _basename(name) or argv0 or source
            key = (source, label)
            if key not in seen:
                seen.add(key)
                model = {"name": label, "source": source}
                _merge_meta(model, {}, ctx, ngl)
                models.append(model)
        except Exception:
            continue

    return models


def _merge_meta(
    model: Dict[str, object],
    meta: Dict[str, str],
    ctx: Optional[int],
    ngl: Optional[int],
) -> None:
    """Reflect the parsed context/GPU layers and file-derived meta on ``model``."""
    model.update(meta)
    if ctx is not None:
        model["ctx"] = ctx
    if ngl is not None:
        model["ngl"] = ngl
