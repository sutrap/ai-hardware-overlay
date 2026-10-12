"""Text formatting for the overlay.

All numeric helpers return ``"n/a"`` for ``None`` or unparsable values so a
partially available platform degrades gracefully instead of crashing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

NA = "n/a"


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_percent(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return NA
    return f"{number:.0f}%"


def format_gb(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return NA
    return f"{number:.1f}"


def format_temp(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return NA
    return f"{number:.0f}\u00b0C"


def truncate(text: Any, max_length: Any) -> str:
    try:
        text = "" if text is None else str(text)
    except Exception:
        return NA
    try:
        max_length = int(max_length)
    except (TypeError, ValueError):
        max_length = 60
    if max_length > 0 and len(text) > max_length:
        return text[: max_length - 1] + "\u2026"
    return text


def format_context(value: Any) -> str:
    """Render a token context length compactly: 4096 -> ``4k``, 32768 -> ``32k``."""
    number = _as_float(value)
    if number is None or number <= 0:
        return NA
    k = number / 1024
    if abs(k - round(k)) < 0.05:
        return f"{int(round(k))}k"
    return f"{k:.1f}k"


# Fields selectable via config ``model_detail_fields``, in display order.
DETAIL_FIELDS = {
    "ctx": lambda value: f"ctx {format_context(value)}",
    "quant": str,
    "params": str,
    "family": str,
    "ngl": lambda value: f"ngl {value}",
}


def _format_model_details(model: Dict[str, Any], fields: Any) -> str:
    if not isinstance(fields, list):
        return ""
    parts: List[str] = []
    for field in fields:
        renderer = DETAIL_FIELDS.get(field)
        if renderer is None:
            continue
        value = model.get(field)
        if value is None:
            continue
        rendered = renderer(value)
        if rendered and rendered != NA:
            parts.append(rendered)
    return " \u00b7 ".join(parts)


def _format_models(
    models: List[Dict[str, Any]], config: Dict[str, Any]
) -> List[str]:
    lines = ["Models:"]
    max_length = config.get("max_model_name_length", 60)
    fields = config.get("model_detail_fields")
    for model in models:
        name = truncate(model.get("name", NA), max_length)
        source = model.get("source") or NA
        line = f"- {name} [{source}]"
        device = model.get("device")
        if device:
            line += f" {device}"
        lines.append(line)
        details = _format_model_details(model, fields)
        if details:
            lines.append(f"    {details}")
    return lines


def _format_gpu(index: int, gpu: Dict[str, Any]) -> List[str]:
    name = gpu.get("name") or NA
    lines = [f"GPU {index}: {name}"]
    lines.append(f"Load: {format_percent(gpu.get('load_percent'))}")

    vram_used = _as_float(gpu.get("vram_used_gb"))
    vram_total = _as_float(gpu.get("vram_total_gb"))
    if vram_used is None and vram_total is None:
        lines.append("VRAM: n/a")
    else:
        lines.append(
            f"VRAM: {format_gb(vram_used)} / {format_gb(vram_total)} GB"
        )

    lines.append(f"Temp: {format_temp(gpu.get('temperature_c'))}")
    return lines


def format_snapshot(
    system: Optional[Dict[str, Any]],
    models: Optional[List[Dict[str, Any]]],
    gpus: Optional[List[Dict[str, Any]]],
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Render the complete overlay text for one refresh cycle."""
    config = config or {}
    system = system or {}
    models = models or []
    gpus = gpus or []

    lines: List[str] = ["AI Hardware Overlay", "-------------------"]

    if models:
        lines.extend(_format_models(models, config))
    else:
        lines.append("Model: kein Modell erkannt")

    lines.append("")

    cpu = _as_float(system.get("cpu_percent"))
    lines.append(f"CPU: {format_percent(cpu)}")

    ram_percent = _as_float(system.get("ram_percent"))
    if ram_percent is None:
        lines.append("RAM: n/a")
    else:
        lines.append(
            f"RAM: {format_percent(ram_percent)} | "
            f"{format_gb(system.get('ram_used_gb'))} / "
            f"{format_gb(system.get('ram_total_gb'))} GB"
        )

    lines.append("")

    if not gpus:
        lines.append("GPU: n/a")
    else:
        for index, gpu in enumerate(gpus, start=1):
            lines.extend(_format_gpu(index, gpu))
            if index != len(gpus):
                lines.append("")

    return "\n".join(lines)
