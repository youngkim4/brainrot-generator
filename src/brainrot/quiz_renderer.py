"""Quiz frame rendering with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .captions import _get_font
from .config import VideoConfig
from .quiz_config import QuizType, TriviaQuestion, WYRQuestion


# colors
COLOR_BG_BOX = (0, 0, 0, 180)
COLOR_WHITE = (255, 255, 255, 255)
COLOR_OPTION_BG = (40, 40, 40, 200)
COLOR_OPTION_BORDER = (255, 255, 255, 100)
COLOR_CORRECT = (0, 200, 50, 230)
COLOR_COUNTDOWN_BG = (80, 80, 80, 150)
COLOR_COUNTDOWN_FILL = (255, 80, 80, 220)
COLOR_WYR_A = (50, 120, 255, 200)
COLOR_WYR_B = (255, 80, 50, 200)

# layout
PADDING = 40
OPTION_PADDING = 20
OPTION_MARGIN = 12
QUESTION_AREA_TOP = 0.15  # fraction of height
COUNTDOWN_HEIGHT = 12
COUNTDOWN_Y_FRAC = 0.88


def _wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or [""]


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    frame_width: int,
    fill: tuple[int, ...] = COLOR_WHITE,
) -> int:
    """Draw centered text, return total height used."""
    max_w = frame_width - 2 * PADDING
    lines = _wrap_text(text, font, max_w)
    line_h = font.getbbox("Ay")[3] - font.getbbox("Ay")[1]
    total_h = 0
    for line in lines:
        bbox = font.getbbox(line)
        text_w = bbox[2] - bbox[0]
        x = (frame_width - text_w) // 2
        draw.text((x, y + total_h), line, font=font, fill=fill)
        total_h += line_h + 4
    return total_h


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    fill: tuple[int, ...],
    radius: int = 16,
    outline: tuple[int, ...] | None = None,
) -> None:
    """Rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)


def render_trivia_frame(
    question: TriviaQuestion,
    video: VideoConfig,
    reveal: bool = False,
) -> Image.Image:
    """Render trivia question with options."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    q_font_size = max(16, video.width // 18)
    o_font_size = max(14, video.width // 22)
    q_font = _get_font(q_font_size)
    o_font = _get_font(o_font_size)

    # question background box
    q_top = int(video.height * QUESTION_AREA_TOP)
    max_text_w = video.width - 2 * PADDING

    q_lines = _wrap_text(question.question, q_font, max_text_w - 2 * OPTION_PADDING)
    q_line_h = q_font.getbbox("Ay")[3] - q_font.getbbox("Ay")[1]
    q_block_h = len(q_lines) * (q_line_h + 4) + 2 * OPTION_PADDING

    _draw_rounded_rect(
        draw,
        (PADDING, q_top, video.width - PADDING, q_top + q_block_h),
        fill=COLOR_BG_BOX,
        radius=20,
    )

    # question text
    q_text_y = q_top + OPTION_PADDING
    _draw_text_centered(draw, question.question, q_font, q_text_y, video.width)

    # options
    opt_top = q_top + q_block_h + OPTION_MARGIN * 2
    o_line_h = o_font.getbbox("Ay")[3] - o_font.getbbox("Ay")[1]
    opt_h = o_line_h + 2 * OPTION_PADDING

    labels = ["A", "B", "C", "D"]
    for i, option in enumerate(question.options):
        y = opt_top + i * (opt_h + OPTION_MARGIN)
        bg_color = COLOR_CORRECT if (reveal and i == question.correct) else COLOR_OPTION_BG
        outline = COLOR_OPTION_BORDER

        _draw_rounded_rect(
            draw,
            (PADDING, y, video.width - PADDING, y + opt_h),
            fill=bg_color,
            radius=14,
            outline=outline,
        )

        label = labels[i] if i < len(labels) else str(i + 1)
        text = f"{label}. {option}"
        bbox = o_font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        # left-aligned with padding
        tx = PADDING + OPTION_PADDING
        ty = y + (opt_h - o_line_h) // 2
        draw.text((tx, ty), text, font=o_font, fill=COLOR_WHITE)

    return img


def render_wyr_frame(
    question: WYRQuestion,
    video: VideoConfig,
) -> Image.Image:
    """Render Would You Rather question."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    title_font_size = max(16, video.width // 16)
    opt_font_size = max(14, video.width // 20)
    title_font = _get_font(title_font_size)
    opt_font = _get_font(opt_font_size)

    # title
    title_y = int(video.height * QUESTION_AREA_TOP)
    _draw_text_centered(draw, "Would You Rather...", title_font, title_y, video.width)

    title_line_h = title_font.getbbox("Ay")[3] - title_font.getbbox("Ay")[1]

    # option boxes — stacked vertically
    box_w = video.width - 2 * PADDING
    box_h = int(video.height * 0.18)
    gap = OPTION_MARGIN * 2

    # position below title
    start_y = title_y + title_line_h + PADDING

    for i, (option_text, color) in enumerate([
        (f"A: {question.option_a}", COLOR_WYR_A),
        (f"B: {question.option_b}", COLOR_WYR_B),
    ]):
        y = start_y + i * (box_h + gap)
        _draw_rounded_rect(
            draw,
            (PADDING, y, PADDING + box_w, y + box_h),
            fill=color,
            radius=20,
        )
        # center text in box
        max_w = box_w - 2 * OPTION_PADDING
        lines = _wrap_text(option_text, opt_font, max_w)
        line_h = opt_font.getbbox("Ay")[3] - opt_font.getbbox("Ay")[1]
        text_block_h = len(lines) * (line_h + 4)
        text_y = y + (box_h - text_block_h) // 2
        _draw_text_centered(draw, option_text, opt_font, text_y, video.width)

    return img


def render_countdown_bar(
    video: VideoConfig,
    progress: float,  # 0.0 = full, 1.0 = empty
) -> Image.Image:
    """Horizontal countdown bar overlay."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bar_y = int(video.height * COUNTDOWN_Y_FRAC)
    bar_w = video.width - 2 * PADDING
    fill_w = max(0, int(bar_w * (1.0 - progress)))

    # background
    _draw_rounded_rect(
        draw,
        (PADDING, bar_y, PADDING + bar_w, bar_y + COUNTDOWN_HEIGHT),
        fill=COLOR_COUNTDOWN_BG,
        radius=6,
    )

    # fill
    if fill_w > 0:
        _draw_rounded_rect(
            draw,
            (PADDING, bar_y, PADDING + fill_w, bar_y + COUNTDOWN_HEIGHT),
            fill=COLOR_COUNTDOWN_FILL,
            radius=6,
        )

    return img


def load_character_image(
    path: Path,
    video: VideoConfig,
    target_width_frac: float = 0.20,
) -> Image.Image:
    """Load and scale character PNG to overlay size."""
    char_img = Image.open(path).convert("RGBA")
    target_w = int(video.width * target_width_frac)
    aspect = char_img.height / char_img.width
    target_h = int(target_w * aspect)
    return char_img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def render_question_frame(
    question: TriviaQuestion | WYRQuestion,
    video: VideoConfig,
    reveal: bool = False,
) -> Image.Image:
    """Dispatch to trivia or wyr renderer."""
    if isinstance(question, TriviaQuestion):
        return render_trivia_frame(question, video, reveal=reveal)
    return render_wyr_frame(question, video)
