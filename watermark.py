from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}
_MARGIN = 20

_FONT_CANDIDATES = (Path(__file__).parent / "assets" / "fonts" / "NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # noqa: E203


def _anchor_xy(image_size: tuple[int, int], text_size: tuple[int, int], position: str) -> tuple[int, int]:
    width, height = image_size
    text_w, text_h = text_size
    if position == "top-left":
        return _MARGIN, _MARGIN
    if position == "top-right":
        return width - text_w - _MARGIN, _MARGIN
    if position == "bottom-left":
        return _MARGIN, height - text_h - _MARGIN
    if position == "center":
        return (width - text_w) // 2, (height - text_h) // 2
    return width - text_w - _MARGIN, height - text_h - _MARGIN


def apply_text_watermark(
    image_bytes: bytes,
    text: str,
    position: str = "bottom-right",
    opacity: float = 0.6,
    font_size: int = 32,
    color: str = "#FFFFFF",
) -> bytes:
    base = Image.open(BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = None
    for candidate in _FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(str(candidate), font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
    xy = _anchor_xy(base.size, text_size, position if position in POSITIONS else "bottom-right")

    alpha = max(0, min(255, int(opacity * 255)))
    r, g, b = _hex_to_rgb(color)
    draw.text(xy, text, font=font, fill=(r, g, b, alpha))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    out = BytesIO()
    combined.save(out, format="JPEG", quality=92)
    return out.getvalue()
