"""Slideshow video compositing with fade transitions and Ken Burns effect."""

from pathlib import Path

import numpy as np
from moviepy import (
    AudioFileClip,
    ImageClip,
    VideoClip,
    concatenate_videoclips,
    vfx,
)
from PIL import Image, ImageDraw, ImageFont

_FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux (Debian/Ubuntu)
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",  # Linux (Arch)
    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _label_from_path(path: Path) -> str:
    """Derive label from filename: 'underwater_palace.png' -> 'Underwater Palace'."""
    return path.stem.replace("_", " ").replace("-", " ").title()


def _fit_image(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize and crop image to fill target dimensions."""
    target_aspect = width / height
    src_w, src_h = image.size
    src_aspect = src_w / src_h

    if src_aspect > target_aspect:
        # wider — scale height, crop width
        new_h = height
        new_w = int(src_w * (height / src_h))
    else:
        # taller — scale width, crop height
        new_w = width
        new_h = int(src_h * (width / src_w))

    resized = image.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _render_intro_card(
    prompt: str,
    width: int,
    height: int,
) -> np.ndarray:
    """Render dramatic intro card — dark bg with large centered prompt text."""
    arr = np.full((height, width, 3), (8, 8, 12), dtype=np.float32)

    # vectorized vignette gradient
    yy, xx = np.mgrid[0:height, 0:width]
    dx = (xx - width / 2) / (width / 2)
    dy = (yy - height / 2) / (height / 2)
    dist = np.clip(np.sqrt(dx ** 2 + dy ** 2), 0, 1)
    darken = (20 * dist).astype(np.float32)[..., None]
    arr = np.clip(arr - darken, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    font_size = width // 12
    font = _load_font(font_size)

    # word-wrap
    words = prompt.split()
    lines = []
    current_line = ""
    max_text_width = int(width * 0.75)

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_text_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    text_block = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), text_block, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2

    # thick stroke for dramatic contrast
    stroke_w = max(3, width // 200)
    for sdx in range(-stroke_w, stroke_w + 1):
        for sdy in range(-stroke_w, stroke_w + 1):
            draw.multiline_text(
                (x + sdx, y + sdy), text_block, font=font,
                fill=(0, 0, 0), align="center",
            )
    draw.multiline_text(
        (x, y), text_block, font=font,
        fill=(255, 255, 255), align="center",
    )

    return np.array(img)


def _render_slide_with_label(
    image_path: Path,
    label: str,
    width: int,
    height: int,
) -> np.ndarray:
    """Load image, fit to dimensions, overlay label at bottom."""
    img = Image.open(str(image_path)).convert("RGB")
    img = _fit_image(img, width, height)
    draw = ImageDraw.Draw(img)

    font_size = width // 20
    font = _load_font(font_size)

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = height - text_h - int(height * 0.08)  # 8% from bottom

    # stroke outline for readability
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            draw.text((x + dx, y + dy), label, font=font, fill=(0, 0, 0))
    draw.text((x, y), label, font=font, fill=(255, 255, 255))

    return np.array(img)


def _make_ken_burns_clip(
    frame: np.ndarray,
    duration: float,
    zoom_factor: float,
    fps: int,
) -> VideoClip:
    """Create a clip with slow zoom (Ken Burns) effect."""
    h, w = frame.shape[:2]

    def make_frame(t: float) -> np.ndarray:
        progress = t / duration if duration > 0 else 0
        current_zoom = 1.0 + (zoom_factor - 1.0) * progress
        crop_w = int(w / current_zoom)
        crop_h = int(h / current_zoom)
        x1 = (w - crop_w) // 2
        y1 = (h - crop_h) // 2
        cropped = frame[y1:y1 + crop_h, x1:x1 + crop_w]
        # resize back to original dimensions
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(cropped)
        pil_img = pil_img.resize((w, h), PILImage.LANCZOS)
        return np.array(pil_img)

    return VideoClip(make_frame, duration=duration).with_fps(fps)


def compose_slideshow(
    image_paths: list[Path],
    bgm_path: Path,
    prompt: str,
    output_path: Path,
    seconds_per_slide: float = 3.0,
    intro_duration: float = 3.0,
    fade_duration: float = 0.5,
    ken_burns_zoom: float = 1.15,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    bgm_volume: float = 0.8,
) -> Path:
    """Assemble slideshow: intro card + image slides with fade + ken burns + bgm."""
    if not image_paths:
        raise ValueError("image_paths must not be empty")

    clips = []

    # intro card
    intro_frame = _render_intro_card(prompt, width, height)
    intro_clip = (
        ImageClip(intro_frame)
        .with_duration(intro_duration)
        .with_effects([vfx.CrossFadeOut(fade_duration)])
    )
    clips.append(intro_clip)

    # image slides
    for img_path in image_paths:
        label = _label_from_path(img_path)
        slide_frame = _render_slide_with_label(img_path, label, width, height)
        slide_clip = _make_ken_burns_clip(slide_frame, seconds_per_slide, ken_burns_zoom, fps)
        slide_clip = slide_clip.with_effects([
            vfx.CrossFadeIn(fade_duration),
            vfx.CrossFadeOut(fade_duration),
        ])
        clips.append(slide_clip)

    # concatenate with crossfade overlap
    video = concatenate_videoclips(
        clips,
        method="compose",
        padding=-fade_duration,
    )

    # bgm — must be longer than video, trimmed to match
    bgm = AudioFileClip(str(bgm_path))
    if bgm.duration <= 0:
        bgm.close()
        raise RuntimeError(f"BGM file has zero duration: {bgm_path}")
    if bgm.duration < video.duration:
        bgm.close()
        raise RuntimeError(
            f"BGM ({bgm.duration:.1f}s) is shorter than video ({video.duration:.1f}s). "
            "Use a longer BGM track."
        )
    bgm = bgm.with_duration(video.duration).with_volume_scaled(bgm_volume)

    final = video.with_audio(bgm)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        final.write_videofile(
            str(output_path),
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
    finally:
        final.close()
        bgm.close()
        for clip in clips:
            clip.close()
        video.close()

    return output_path
