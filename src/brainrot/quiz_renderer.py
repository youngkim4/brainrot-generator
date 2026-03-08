"""Quiz frame rendering with Pillow — Dark/Neon TikTok style."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .captions import _get_font
from .config import VideoConfig
from .quiz_config import TriviaQuestion, WYRQuestion


# -- Dark/Neon color palette --
COLOR_CARD_BG = (26, 26, 46, 220)
COLOR_CARD_BORDER = (74, 74, 106, 255)
COLOR_OPTION_BG = (45, 45, 68, 230)
COLOR_OPTION_BORDER = (74, 74, 106, 200)
COLOR_WHITE = (255, 255, 255, 255)
COLOR_GREY_TEXT = (156, 163, 175, 255)
COLOR_BADGE_BG = (124, 58, 237, 255)  # vivid purple
COLOR_CORRECT_BORDER = (34, 197, 94, 255)
COLOR_CORRECT_GLOW = (34, 197, 94, 30)
COLOR_CORRECT_TINT = (34, 197, 94, 40)
COLOR_DIMMED_BG = (30, 30, 50, 230)
COLOR_DIMMED_TEXT = (160, 160, 180, 200)
COLOR_COUNTDOWN_TRACK = (31, 31, 58, 255)
COLOR_COUNTDOWN_PURPLE = (124, 58, 237, 255)
COLOR_COUNTDOWN_PINK = (236, 72, 153, 255)
COLOR_COUNTDOWN_RED = (239, 68, 68, 255)
COLOR_COUNTDOWN_ORANGE = (249, 115, 22, 255)
COLOR_SHADOW = (0, 0, 0, 128)
COLOR_WYR_A = (50, 120, 255, 220)
COLOR_WYR_B = (255, 80, 50, 220)
COLOR_PROGRESS_FILLED = (124, 58, 237, 255)
COLOR_PROGRESS_CURRENT = (167, 139, 250, 255)
COLOR_PROGRESS_EMPTY = (74, 74, 106, 150)

# -- TikTok safe zones --
SAFE_TOP = 150
SAFE_BOTTOM = 440
SAFE_RIGHT = 120
SAFE_LEFT = 60

# -- layout --
PADDING = 80
OPTION_PADDING = 20
OPTION_GAP = 24
CARD_RADIUS = 24
OPTION_RADIUS = 16
BADGE_SIZE = 48
COUNTDOWN_HEIGHT = 20
COUNTDOWN_RADIUS = 10
PROGRESS_DOT_SIZE = 12
PROGRESS_DOT_GAP = 8
SHADOW_OFFSET = 2
TEXT_OUTLINE_WIDTH = 2


def _scale(value: int, video: VideoConfig) -> int:
    """Scale a 1080-based pixel value to current resolution."""
    return max(1, int(value * video.width / 1080))


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


def _text_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    """Line height for a font."""
    bbox = font.getbbox("Ay")
    return bbox[3] - bbox[1]


def _text_width(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont
) -> int:
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def _draw_text_outlined(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, ...] = COLOR_WHITE,
    outline_width: int = TEXT_OUTLINE_WIDTH,
    outline_color: tuple[int, ...] = (0, 0, 0, 200),
) -> None:
    """Draw text with dark outline for readability over gameplay."""
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_text_centered_outlined(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    frame_width: int,
    fill: tuple[int, ...] = COLOR_WHITE,
    max_width: int | None = None,
) -> int:
    """Draw centered text with outline, return total height used."""
    mw = max_width or (frame_width - 2 * _scale(PADDING, VideoConfig(width=frame_width)))
    lines = _wrap_text(text, font, mw)
    line_h = _text_height(font)
    total_h = 0
    for line in lines:
        tw = _text_width(line, font)
        x = (frame_width - tw) // 2
        _draw_text_outlined(draw, (x, y + total_h), line, font, fill=fill)
        total_h += line_h + 4
    return total_h


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    fill: tuple[int, ...],
    radius: int = 16,
    outline: tuple[int, ...] | None = None,
    outline_width: int = 2,
) -> None:
    """Rounded rectangle with optional outline."""
    draw.rounded_rectangle(
        xy, radius=radius, fill=fill, outline=outline, width=outline_width
    )


def _draw_shadow_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int = 16,
    offset: int = 4,
    shadow_color: tuple[int, ...] = (0, 0, 0, 80),
) -> None:
    """Draw a shadow behind a rounded rect."""
    x1, y1, x2, y2 = xy
    _draw_rounded_rect(
        draw,
        (x1 + offset, y1 + offset, x2 + offset, y2 + offset),
        fill=shadow_color,
        radius=radius,
    )


def _draw_glow_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    glow_color: tuple[int, ...],
    radius: int = 16,
    layers: int = 3,
) -> None:
    """Draw expanding glow layers behind a rect."""
    x1, y1, x2, y2 = xy
    for i in range(layers, 0, -1):
        expand = i * 3
        _draw_rounded_rect(
            draw,
            (x1 - expand, y1 - expand, x2 + expand, y2 + expand),
            fill=glow_color,
            radius=radius + expand,
        )


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    letter: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    size: int,
    bg_color: tuple[int, ...] = COLOR_BADGE_BG,
) -> None:
    """Draw a colored circle badge with a letter."""
    r = size // 2
    draw.ellipse(
        (cx - r, cy - r, cx + r, cy + r),
        fill=bg_color,
    )
    tw = _text_width(letter, font)
    th = _text_height(font)
    draw.text(
        (cx - tw // 2, cy - th // 2),
        letter,
        font=font,
        fill=COLOR_WHITE,
    )


def _draw_progress_dots(
    draw: ImageDraw.ImageDraw,
    video: VideoConfig,
    current: int,
    total: int,
    y: int,
) -> None:
    """Draw progress dots showing which question we're on."""
    dot_size = _scale(PROGRESS_DOT_SIZE, video)
    dot_gap = _scale(PROGRESS_DOT_GAP, video)
    total_w = total * dot_size + (total - 1) * dot_gap
    start_x = (video.width - total_w) // 2

    for i in range(total):
        cx = start_x + i * (dot_size + dot_gap) + dot_size // 2
        cy = y + dot_size // 2
        r = dot_size // 2

        if i < current:
            color = COLOR_PROGRESS_FILLED
        elif i == current:
            color = COLOR_PROGRESS_CURRENT
        else:
            color = COLOR_PROGRESS_EMPTY

        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)


def render_trivia_frame(
    question: TriviaQuestion,
    video: VideoConfig,
    reveal: bool = False,
    question_index: int = 0,
    total_questions: int = 1,
) -> Image.Image:
    """Render trivia question — Dark/Neon style."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = _scale(PADDING, video)
    opt_pad = _scale(OPTION_PADDING, video)
    opt_gap = _scale(OPTION_GAP, video)
    badge_sz = _scale(BADGE_SIZE, video)
    safe_top = _scale(SAFE_TOP, video)
    card_r = _scale(CARD_RADIUS, video)
    opt_r = _scale(OPTION_RADIUS, video)

    content_w = video.width - 2 * pad

    q_font_size = max(16, video.width // 16)
    o_font_size = max(14, video.width // 20)
    badge_font_size = max(12, video.width // 28)
    num_font_size = max(12, video.width // 30)
    q_font = _get_font(q_font_size)
    o_font = _get_font(o_font_size)
    badge_font = _get_font(badge_font_size)
    num_font = _get_font(num_font_size)

    # -- progress dots --
    dots_y = safe_top
    _draw_progress_dots(draw, video, question_index, total_questions, dots_y)

    # -- question number --
    num_y = dots_y + _scale(PROGRESS_DOT_SIZE, video) + _scale(16, video)
    num_text = f"Question {question_index + 1} of {total_questions}"
    _draw_text_centered_outlined(
        draw, num_text, num_font, num_y, video.width, fill=COLOR_GREY_TEXT
    )
    num_h = _text_height(num_font)

    # -- question card --
    card_top = num_y + num_h + _scale(20, video)
    inner_w = content_w - 2 * opt_pad
    q_lines = _wrap_text(question.question, q_font, inner_w)
    q_line_h = _text_height(q_font)
    q_block_h = len(q_lines) * (q_line_h + 4) + 2 * opt_pad

    card_rect = (pad, card_top, pad + content_w, card_top + q_block_h)

    _draw_shadow_rect(draw, card_rect, radius=card_r)
    _draw_rounded_rect(
        draw, card_rect,
        fill=COLOR_CARD_BG, radius=card_r,
        outline=COLOR_CARD_BORDER,
    )

    q_text_y = card_top + opt_pad
    _draw_text_centered_outlined(
        draw, question.question, q_font, q_text_y, video.width, max_width=inner_w
    )

    # -- option boxes --
    opt_top = card_top + q_block_h + opt_gap * 2
    o_line_h = _text_height(o_font)
    opt_h = max(o_line_h + 2 * opt_pad, badge_sz + opt_pad)

    labels = ["A", "B", "C", "D"]
    for i, option in enumerate(question.options):
        y = opt_top + i * (opt_h + opt_gap)
        opt_rect = (pad, y, pad + content_w, y + opt_h)

        is_correct = i == question.correct

        if reveal and is_correct:
            # green glow behind correct answer
            _draw_glow_rect(draw, opt_rect, COLOR_CORRECT_GLOW, radius=opt_r)
            _draw_rounded_rect(
                draw, opt_rect,
                fill=COLOR_CORRECT_TINT, radius=opt_r,
                outline=COLOR_CORRECT_BORDER, outline_width=3,
            )
            text_color = COLOR_WHITE
        elif reveal:
            # dim wrong answers
            _draw_rounded_rect(
                draw, opt_rect,
                fill=COLOR_DIMMED_BG, radius=opt_r,
                outline=COLOR_OPTION_BORDER,
            )
            text_color = COLOR_DIMMED_TEXT
        else:
            _draw_shadow_rect(draw, opt_rect, radius=opt_r, offset=2)
            _draw_rounded_rect(
                draw, opt_rect,
                fill=COLOR_OPTION_BG, radius=opt_r,
                outline=COLOR_OPTION_BORDER,
            )
            text_color = COLOR_WHITE

        # letter badge
        badge_cx = pad + opt_pad + badge_sz // 2
        badge_cy = y + opt_h // 2
        badge_color = COLOR_CORRECT_BORDER if (reveal and is_correct) else COLOR_BADGE_BG
        label = labels[i] if i < len(labels) else str(i + 1)
        _draw_badge(draw, badge_cx, badge_cy, label, badge_font, badge_sz, badge_color)

        # option text
        text_x = pad + opt_pad + badge_sz + opt_pad
        text_y = y + (opt_h - o_line_h) // 2
        _draw_text_outlined(draw, (text_x, text_y), option, o_font, fill=text_color)

        # checkmark on correct reveal
        if reveal and is_correct:
            check_x = pad + content_w - opt_pad - _scale(24, video)
            check_cy = y + opt_h // 2
            cs = _scale(10, video)
            draw.line(
                [(check_x, check_cy), (check_x + cs, check_cy + cs),
                 (check_x + cs * 3, check_cy - cs)],
                fill=COLOR_CORRECT_BORDER, width=max(2, _scale(3, video)),
            )

    return img


def render_wyr_frame(
    question: WYRQuestion,
    video: VideoConfig,
    question_index: int = 0,
    total_questions: int = 1,
) -> Image.Image:
    """Render Would You Rather — Dark/Neon style."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = _scale(PADDING, video)
    opt_pad = _scale(OPTION_PADDING, video)
    safe_top = _scale(SAFE_TOP, video)
    card_r = _scale(CARD_RADIUS, video)

    title_font_size = max(16, video.width // 14)
    opt_font_size = max(14, video.width // 18)
    num_font_size = max(12, video.width // 30)
    title_font = _get_font(title_font_size)
    opt_font = _get_font(opt_font_size)
    num_font = _get_font(num_font_size)

    content_w = video.width - 2 * pad

    # -- progress dots --
    dots_y = safe_top
    _draw_progress_dots(draw, video, question_index, total_questions, dots_y)

    # -- question number --
    num_y = dots_y + _scale(PROGRESS_DOT_SIZE, video) + _scale(16, video)
    num_text = f"Question {question_index + 1} of {total_questions}"
    _draw_text_centered_outlined(
        draw, num_text, num_font, num_y, video.width, fill=COLOR_GREY_TEXT
    )
    num_h = _text_height(num_font)

    # -- title --
    title_y = num_y + num_h + _scale(20, video)
    title_h = _draw_text_centered_outlined(
        draw, "Would You Rather...", title_font, title_y, video.width
    )

    # -- option boxes (stacked, large) --
    box_h = int(video.height * 0.18)
    gap = _scale(OPTION_GAP, video) * 2
    start_y = title_y + title_h + _scale(30, video)

    for i, (option_text, color) in enumerate([
        (f"A: {question.option_a}", COLOR_WYR_A),
        (f"B: {question.option_b}", COLOR_WYR_B),
    ]):
        y = start_y + i * (box_h + gap)
        box_rect = (pad, y, pad + content_w, y + box_h)

        _draw_shadow_rect(draw, box_rect, radius=card_r, offset=4)
        _draw_rounded_rect(draw, box_rect, fill=color, radius=card_r)

        # center text in box
        max_w = content_w - 2 * opt_pad
        lines = _wrap_text(option_text, opt_font, max_w)
        line_h = _text_height(opt_font)
        text_block_h = len(lines) * (line_h + 4)
        text_y = y + (box_h - text_block_h) // 2
        _draw_text_centered_outlined(
            draw, option_text, opt_font, text_y, video.width, max_width=max_w
        )

    return img


def render_countdown_bar(
    video: VideoConfig,
    progress: float,  # 0.0 = full, 1.0 = empty
) -> Image.Image:
    """Gradient countdown bar — purple-to-pink, turns red when low."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = _scale(PADDING, video)
    bar_h = _scale(COUNTDOWN_HEIGHT, video)
    bar_r = _scale(COUNTDOWN_RADIUS, video)
    content_w = video.width - 2 * pad

    # position above the bottom safe zone
    bar_y = video.height - _scale(SAFE_BOTTOM, video) - bar_h - _scale(20, video)

    fill_w = max(0, int(content_w * (1.0 - progress)))

    # track
    _draw_rounded_rect(
        draw,
        (pad, bar_y, pad + content_w, bar_y + bar_h),
        fill=COLOR_COUNTDOWN_TRACK,
        radius=bar_r,
    )

    # gradient fill
    if fill_w > bar_r * 2:
        # draw pixel columns for gradient
        low_time = progress > 0.75
        for x in range(fill_w):
            t = x / max(1, fill_w - 1)
            if low_time:
                # red → orange gradient
                r = int(COLOR_COUNTDOWN_RED[0] + t * (COLOR_COUNTDOWN_ORANGE[0] - COLOR_COUNTDOWN_RED[0]))
                g = int(COLOR_COUNTDOWN_RED[1] + t * (COLOR_COUNTDOWN_ORANGE[1] - COLOR_COUNTDOWN_RED[1]))
                b = int(COLOR_COUNTDOWN_RED[2] + t * (COLOR_COUNTDOWN_ORANGE[2] - COLOR_COUNTDOWN_RED[2]))
            else:
                # purple → pink gradient
                r = int(COLOR_COUNTDOWN_PURPLE[0] + t * (COLOR_COUNTDOWN_PINK[0] - COLOR_COUNTDOWN_PURPLE[0]))
                g = int(COLOR_COUNTDOWN_PURPLE[1] + t * (COLOR_COUNTDOWN_PINK[1] - COLOR_COUNTDOWN_PURPLE[1]))
                b = int(COLOR_COUNTDOWN_PURPLE[2] + t * (COLOR_COUNTDOWN_PINK[2] - COLOR_COUNTDOWN_PURPLE[2]))
            draw.line(
                [(pad + x, bar_y + 1), (pad + x, bar_y + bar_h - 1)],
                fill=(r, g, b, 240),
            )

        # rounded ends — redraw as rounded rect over the gradient
        _draw_rounded_rect(
            draw,
            (pad, bar_y, pad + fill_w, bar_y + bar_h),
            fill=(0, 0, 0, 0),
            radius=bar_r,
            outline=(0, 0, 0, 0),
        )
    elif fill_w > 0:
        # too small for gradient, solid color
        color = COLOR_COUNTDOWN_RED if progress > 0.75 else COLOR_COUNTDOWN_PURPLE
        _draw_rounded_rect(
            draw,
            (pad, bar_y, pad + fill_w, bar_y + bar_h),
            fill=color,
            radius=bar_r,
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
    question_index: int = 0,
    total_questions: int = 1,
) -> Image.Image:
    """Dispatch to trivia or wyr renderer."""
    if isinstance(question, TriviaQuestion):
        return render_trivia_frame(
            question, video, reveal=reveal,
            question_index=question_index, total_questions=total_questions,
        )
    return render_wyr_frame(
        question, video,
        question_index=question_index, total_questions=total_questions,
    )
