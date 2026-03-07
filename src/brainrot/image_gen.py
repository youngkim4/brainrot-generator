"""AI image generation via Gemini."""

import json
import os
import re
from io import BytesIO
from pathlib import Path

from PIL import Image

# cinematic prompt template — structured like a cinematographer's brief
_IMAGE_PROMPT_TEMPLATE = (
    "{subject}, {setting_detail}. "
    "Hyper-realistic digital art, cinematic lighting with volumetric fog, "
    "dramatic rim lighting, shallow depth of field, "
    "rich saturated color palette, 8K UHD, "
    "vertical 9:16 composition, centered subject, "
    "dreamlike and awe-inspiring atmosphere"
)

_SUBJECT_GEN_PROMPT = """\
You are a creative director for viral TikTok slideshows.

Given this question prompt: "{prompt}"

Generate exactly {count} visually stunning, fantastical concepts that would \
make viewers stop scrolling. Each concept should be:
- Specific and vivid (not generic)
- Visually dramatic and cinematic
- Unique from each other (vary environments, moods, color palettes)
- The kind of thing that makes someone say "I want to live there" or "I want that"

For each concept, provide:
- "subject": a short label (2-4 words) for display on screen
- "setting_detail": a vivid 1-sentence scene description with specific \
colors, materials, lighting, and atmosphere

Return ONLY a JSON array, no other text. Example:
[
  {{"subject": "Crystal Cavern Palace", "setting_detail": "a vast underground \
palace carved from luminous amethyst crystals, bioluminescent pools casting \
purple and teal reflections on cathedral-height ceilings"}},
  {{"subject": "Floating Sky Garden", "setting_detail": "a lush garden \
suspended among clouds at golden hour, cascading waterfalls dissolving into \
mist below, warm amber light filtering through giant flowering vines"}}
]
"""


def generate_subjects(
    prompt: str,
    count: int = 6,
    model: str = "gemini-3.1-flash-image-preview",
) -> list[dict[str, str]]:
    """Use Gemini text generation to create subject concepts."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is required")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=[_SUBJECT_GEN_PROMPT.format(prompt=prompt, count=count)],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
        ),
    )

    raw = response.text.strip()
    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    try:
        subjects = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini returned invalid JSON: {e}\nRaw: {raw[:300]}") from e
    if not isinstance(subjects, list) or len(subjects) < 2:
        raise RuntimeError(f"Expected list of subjects, got: {raw[:200]}")

    for i, item in enumerate(subjects[:count]):
        if not isinstance(item, dict) or "subject" not in item:
            raise RuntimeError(f"Subject {i} missing 'subject' key: {item!r}")

    return subjects[:count]


def _build_image_prompt(subject: str, setting_detail: str) -> str:
    """Build cinematic image prompt from subject and setting detail."""
    return _IMAGE_PROMPT_TEMPLATE.format(
        subject=subject,
        setting_detail=setting_detail,
    )


def generate_images(
    prompt: str,
    subjects: list[dict[str, str]],
    output_dir: Path,
    model: str = "gemini-3.1-flash-image-preview",
) -> list[Path]:
    """Generate images for each subject using Gemini.

    Args:
        prompt: context prompt, e.g. "Where would you live?"
        subjects: list of dicts with "subject" and "setting_detail" keys
        output_dir: where to save generated images
        model: Gemini model ID

    Returns:
        list of saved image paths, named after subjects
    """
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is required")

    client = genai.Client(api_key=api_key)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for entry in subjects:
        label = entry["subject"]
        detail = entry.get("setting_detail", label)
        image_prompt = _build_image_prompt(label, detail)

        response = client.models.generate_content(
            model=model,
            contents=[image_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        saved = False
        for part in response.parts:
            if part.inline_data is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                safe_name = re.sub(r"[^\w\-]", "_", label.lower())[:64]
                file_path = (output_dir / f"{safe_name}.png").resolve()
                if not str(file_path).startswith(str(output_dir.resolve())):
                    raise RuntimeError(f"Unsafe path from label: {label!r}")
                image.save(str(file_path))
                paths.append(file_path)
                saved = True
                break

        if not saved:
            raise RuntimeError(f"Gemini returned no image for: {label}")

    return paths


def load_images_from_dir(image_dir: Path) -> list[Path]:
    """Load existing images from a directory, sorted alphabetically."""
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    paths = sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in extensions
    )
    if not paths:
        raise FileNotFoundError(f"No images found in {image_dir}")
    return paths
