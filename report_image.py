from __future__ import annotations

import textwrap
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_WIDTH = 1080
_BG = (18, 20, 26)
_HEADING = (255, 255, 255)
_SUBHEADING = (140, 190, 255)
_BODY = (225, 225, 230)
_MARGIN = 80
_WRAP_WIDTH = 46

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_FONT_CANDIDATES = {
    False: (_FONT_DIR / "NotoSans-Regular.ttf", "DejaVuSans.ttf"),
    True: (_FONT_DIR / "NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf"),
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_weekly_card(
    next_number: int,
    next_bracket: int,
    completion_wins: list[str],
    progress_wins: list[str],
) -> bytes:
    closing_week = next_number - 1

    heading_font = _font(52, bold=True)
    sub_font = _font(34, bold=True)
    label_font = _font(28, bold=True)
    body_font = _font(30)

    # Lay out as (text, font, color, gap-after) blocks, wrapping bullets first,
    # so the canvas height can be sized to the actual content instead of a
    # fixed guess.
    blocks: list[tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont, tuple[int, int, int], int]] = []
    blocks.append(("It's Monday once more", heading_font, _HEADING, 20))
    blocks.append((f"Good luck with week {next_number} [{next_bracket}]", sub_font, _SUBHEADING, 70))
    blocks.append((f"Week {closing_week} feats:", heading_font, _HEADING, 50))
    blocks.append(("Completion wins // Closing loops", label_font, _SUBHEADING, 25))
    for win in completion_wins:
        for line in textwrap.wrap(f"- {win}", width=_WRAP_WIDTH) or [f"- {win}"]:
            blocks.append((line, body_font, _BODY, 10))
    blocks.append(("", body_font, _BODY, 35))
    blocks.append(("Progress wins // Moving something forward", label_font, _SUBHEADING, 25))
    for win in progress_wins:
        for line in textwrap.wrap(f"- {win}", width=_WRAP_WIDTH) or [f"- {win}"]:
            blocks.append((line, body_font, _BODY, 10))

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    y = _MARGIN
    for text, font, _, gap in blocks:
        line_height = measure.textbbox((0, 0), text or "Ag", font=font)[3]
        y += line_height + gap
    height = y + _MARGIN

    image = Image.new("RGB", (_WIDTH, height), _BG)
    draw = ImageDraw.Draw(image)
    y = _MARGIN
    for text, font, color, gap in blocks:
        line_height = draw.textbbox((0, 0), text or "Ag", font=font)[3]
        if text:
            draw.text((_MARGIN, y), text, font=font, fill=color)
        y += line_height + gap

    out = BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()
