"""Caption rendering with word-by-word highlight animation."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import CaptionStyle, VideoConfig
from .timestamps import WordTimestamp


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a bold font, falling back to default."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _get_vertical_y(video: VideoConfig, style: CaptionStyle, text_height: int) -> int:
    """Calculate Y position based on style.position."""
    positions = {
        "top": video.height // 5,
        "center": (video.height - text_height) // 2,
        "bottom": video.height * 4 // 5 - text_height,
    }
    return positions.get(style.position, positions["center"])


def _find_current_word_index(words: list[WordTimestamp], current_time: float) -> int:
    """Find which word is active at current_time."""
    for i, w in enumerate(words):
        if w.start <= current_time <= w.end:
            return i
        if w.start > current_time:
            return max(0, i - 1)
    return len(words) - 1 if words else 0


def create_caption_frame(
    words: list[WordTimestamp],
    current_time: float,
    video: VideoConfig,
    style: CaptionStyle,
) -> Image.Image:
    """Create a transparent caption overlay for a given timestamp."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))

    if not words:
        return img

    draw = ImageDraw.Draw(img)
    font = _get_font(style.font_size)

    current_idx = _find_current_word_index(words, current_time)

    # Get the group of words to display
    n = style.words_per_group
    group_start = (current_idx // n) * n
    group_end = min(group_start + n, len(words))
    visible_words = words[group_start:group_end]

    if not visible_words:
        return img

    # Measure each word
    word_widths = []
    total_width = 0
    for w in visible_words:
        bbox = font.getbbox(w.word + " ")
        width = bbox[2] - bbox[0]
        word_widths.append(width)
        total_width += width

    text_height = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    x = (video.width - total_width) // 2
    y = _get_vertical_y(video, style, text_height)

    # Draw each word with stroke outline, highlight current
    for w, word_width in zip(visible_words, word_widths):
        is_current = w.start <= current_time <= w.end
        color = style.highlight_color if is_current else style.font_color

        # Stroke
        sw = style.stroke_width
        for dx in range(-sw, sw + 1):
            for dy in range(-sw, sw + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), w.word, font=font, fill=style.stroke_color)

        draw.text((x, y), w.word, font=font, fill=color)
        x += word_width

    return img
