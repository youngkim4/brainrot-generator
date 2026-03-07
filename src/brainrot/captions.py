"""Caption rendering."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import CaptionStyle, VideoConfig
from .timestamps import WordTimestamp


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Bold font, fallback default."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _get_vertical_y(video: VideoConfig, style: CaptionStyle, text_height: int) -> int:
    """Y position from style."""
    positions = {
        "top": video.height // 5,
        "center": (video.height - text_height) // 2,
        "bottom": video.height * 4 // 5 - text_height,
    }
    return positions.get(style.position, positions["center"])


def _find_current_word_index(words: list[WordTimestamp], current_time: float) -> int:
    """Active word at time."""
    for i, w in enumerate(words):
        if w.start <= current_time <= w.end:
            return i
        if w.start > current_time:
            return max(0, i - 1)
    return len(words) - 1 if words else 0


def create_single_word_frame(
    word: str,
    video: VideoConfig,
    style: CaptionStyle,
) -> Image.Image:
    """Single word centered on transparent overlay."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))

    if not word:
        return img

    draw = ImageDraw.Draw(img)
    font = _get_font(style.font_size)

    bbox = font.getbbox(word)
    text_w = bbox[2] - bbox[0]
    ref_bbox = font.getbbox("Ay")
    text_h = ref_bbox[3] - ref_bbox[1]

    x = (video.width - text_w) // 2
    y = _get_vertical_y(video, style, text_h)

    # stroke outline
    sw = style.stroke_width
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), word, font=font, fill=style.stroke_color)

    draw.text((x, y), word, font=font, fill=style.highlight_color)

    return img
