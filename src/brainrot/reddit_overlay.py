"""Reddit post card overlay for video intros."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import VideoConfig


_SUBREDDITS = [
    "r/UnresolvedMysteries",
    "r/TrueCrime",
    "r/UnsolvedMysteries",
    "r/TrueCrimeDiscussion",
    "r/mystery",
    "r/ColdCases",
    "r/WithoutATrace",
]

_USERNAME_PREFIXES = [
    "case_files_", "cold_case_", "true_crime_", "unsolved_",
    "detective_", "forensic_", "missing_", "research_",
]

# reddit dark mode colors
_CARD_BG = (33, 33, 36, 250)
_TEXT_PRIMARY = (215, 218, 220)
_TEXT_SECONDARY = (129, 131, 132)
_ACCENT = (255, 69, 0)
_BORDER = (52, 53, 54)


def _generate_username() -> str:
    prefix = random.choice(_USERNAME_PREFIXES)
    suffix = "".join(random.choices(string.digits, k=random.randint(3, 6)))
    return f"u/{prefix}{suffix}"


def _generate_title(story_text: str) -> str:
    """Extract first sentence as post title."""
    if not story_text:
        return "Untitled"
    # find earliest sentence-ending punctuation
    indices = [story_text.find(c) for c in ".!?"]
    valid = [i for i in indices if i != -1]
    if valid:
        idx = min(valid)
        title = story_text[: idx + 1].strip()
        if len(title) > 100:
            title = title[:97] + "..."
        return title
    return story_text[:80].strip() + "..."


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        paths = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        paths = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines or ["Untitled"]


@dataclass(frozen=True)
class _CardLayout:
    """Pre-computed card dimensions."""

    s: float
    card_w: int
    card_x: int
    pad_x: int
    pad_y: int
    vote_bar_w: int
    content_x: int
    content_w: int
    sub_h: int
    meta_h: int
    title_line_h: int
    bottom_h: int


def _compute_layout(video: VideoConfig) -> _CardLayout:
    s = video.width / 1080.0
    card_w = int(video.width * 0.80)
    card_x = (video.width - card_w) // 2
    pad_x = int(28 * s)
    pad_y = int(24 * s)
    vote_bar_w = int(52 * s)
    content_x = pad_x + vote_bar_w + int(16 * s)
    content_w = card_w - content_x - pad_x
    return _CardLayout(
        s=s, card_w=card_w, card_x=card_x,
        pad_x=pad_x, pad_y=pad_y,
        vote_bar_w=vote_bar_w, content_x=content_x, content_w=content_w,
        sub_h=int(32 * s), meta_h=int(28 * s),
        title_line_h=int(46 * s), bottom_h=int(36 * s),
    )


def _draw_vote_bar(
    draw: ImageDraw.ImageDraw, layout: _CardLayout, y: int, upvotes: str,
    font_votes: ImageFont.ImageFont,
) -> None:
    """Draw upvote arrow, count, downvote arrow."""
    s = layout.s
    arrow_size = int(10 * s)
    arrow_cx = layout.pad_x + layout.vote_bar_w // 2
    arrow_y = y + int(6 * s)

    # upvote
    draw.polygon(
        [(arrow_cx, arrow_y),
         (arrow_cx - arrow_size, arrow_y + arrow_size),
         (arrow_cx + arrow_size, arrow_y + arrow_size)],
        fill=_ACCENT,
    )
    # count
    vote_bbox = font_votes.getbbox(upvotes)
    vote_w = vote_bbox[2] - vote_bbox[0]
    draw.text(
        (arrow_cx - vote_w // 2, arrow_y + arrow_size + int(6 * s)),
        upvotes, font=font_votes, fill=_TEXT_PRIMARY,
    )
    # downvote
    down_y = arrow_y + arrow_size + int(32 * s)
    draw.polygon(
        [(arrow_cx, down_y + arrow_size),
         (arrow_cx - arrow_size, down_y),
         (arrow_cx + arrow_size, down_y)],
        fill=_TEXT_SECONDARY,
    )


def _draw_content(
    draw: ImageDraw.ImageDraw, layout: _CardLayout, y: int,
    subreddit: str, meta: str, title_lines: list[str], bottom_text: str,
    font_sub: ImageFont.ImageFont, font_meta: ImageFont.ImageFont,
    font_title: ImageFont.ImageFont,
) -> None:
    """Draw subreddit, meta, title, and bottom bar."""
    s = layout.s
    x = layout.content_x

    draw.text((x, y), subreddit, font=font_sub, fill=_TEXT_PRIMARY)
    y += layout.sub_h + int(4 * s)

    draw.text((x, y), meta, font=font_meta, fill=_TEXT_SECONDARY)
    y += layout.meta_h + int(14 * s)

    for line in title_lines:
        draw.text((x, y), line, font=font_title, fill=_TEXT_PRIMARY)
        y += layout.title_line_h

    y += int(18 * s)
    draw.text((x, y), bottom_text, font=font_meta, fill=_TEXT_SECONDARY)


def create_reddit_card(
    story_text: str,
    video: VideoConfig,
    subreddit: str | None = None,
    username: str | None = None,
    title: str | None = None,
) -> Image.Image:
    """Render a Reddit dark-mode post card."""
    img = Image.new("RGBA", (video.width, video.height), (0, 0, 0, 0))
    layout = _compute_layout(video)
    s = layout.s

    subreddit = subreddit or random.choice(_SUBREDDITS)
    username = username or _generate_username()
    title = title or _generate_title(story_text)
    upvotes = f"{random.randint(5, 85)}.{random.randint(1, 9)}k"
    meta = f"Posted by {username} · {random.randint(1, 14)}d ago"
    bottom_text = f"{random.randint(200, 3500)} Comments   Share   Save"

    font_sub = _get_font(int(26 * s), bold=True)
    font_meta = _get_font(int(22 * s))
    font_title = _get_font(int(36 * s), bold=True)
    font_votes = _get_font(int(22 * s), bold=True)

    title_lines = _wrap_text(title, font_title, layout.content_w)

    card_h = (
        layout.pad_y + layout.sub_h + int(4 * s) + layout.meta_h + int(14 * s)
        + layout.title_line_h * len(title_lines) + int(18 * s)
        + layout.bottom_h + layout.pad_y
    )
    card_y = int(video.height * 0.22)

    card = Image.new("RGBA", (layout.card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    radius = int(8 * s)
    draw.rounded_rectangle(
        [(0, 0), (layout.card_w - 1, card_h - 1)],
        radius=radius, fill=_CARD_BG, outline=_BORDER,
        width=max(1, int(1.5 * s)),
    )

    y = layout.pad_y
    _draw_vote_bar(draw, layout, y, upvotes, font_votes)
    _draw_content(
        draw, layout, y, subreddit, meta, title_lines, bottom_text,
        font_sub, font_meta, font_title,
    )

    img.paste(card, (layout.card_x, card_y), card)
    return img
