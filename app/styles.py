"""Qt stylesheet for the dark HUD overlay."""

from __future__ import annotations

# A stack that resolves to a monospace font on both Windows and Linux.
FONT_FAMILY = (
    "'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', "
    "'Liberation Mono', 'Courier New', monospace"
)


def build_stylesheet(font_size: int = 13) -> str:
    """Return the application stylesheet for the given font size."""
    try:
        font_size = int(font_size)
    except (TypeError, ValueError):
        font_size = 13
    font_size = max(8, min(48, font_size))

    return f"""
    QWidget#Overlay {{
        background-color: rgba(12, 12, 16, 205);
        border: 1px solid rgba(120, 120, 140, 150);
        border-radius: 10px;
    }}
    QLabel#OverlayText {{
        color: #f5f5f5;
        font-family: {FONT_FAMILY};
        font-size: {font_size}px;
        background: transparent;
    }}
    QMenu {{
        background-color: #14141a;
        color: #f5f5f5;
        border: 1px solid #3a3a46;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 4px 22px 4px 22px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: #2a2a38;
    }}
    QMenu::separator {{
        height: 1px;
        background: #3a3a46;
        margin: 4px 8px;
    }}
    """
