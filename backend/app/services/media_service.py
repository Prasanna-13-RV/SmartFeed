from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from app.config import settings


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(settings.font_path, size=size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    words = text.split()
    lines = []
    current = []

    for word in words:
        trial = " ".join(current + [word])
        width = draw.textbbox((0, 0), trial, font=font)[2]
        if width <= max_width:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return "\n".join(lines[:5])


def generate_instagram_image(post: dict) -> str:
    output_dir = Path(settings.output_dir) / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    canvas = Image.new("RGB", (1080, 1080), color=(20, 28, 40))
    draw = ImageDraw.Draw(canvas)

    # Reusable branded template blocks for all generated posts.
    draw.rectangle([(0, 0), (1080, 250)], fill=(233, 84, 32))
    draw.rectangle([(0, 820), (1080, 1080)], fill=(15, 18, 28))

    title_font = _load_font(56)
    badge_font = _load_font(38)

    draw.text((60, 70), "SMARTFEED", fill="white", font=badge_font)
    wrapped = _wrap_text(draw, post["title"], title_font, 950)
    draw.multiline_text((60, 310), wrapped, fill="white", font=title_font, spacing=12)
    draw.text((60, 900), f"#{post['category']}  |  @{post['assigned_platform']}", fill=(205, 210, 222), font=badge_font)

    out_path = output_dir / f"{post['rss_id']}.jpg"
    canvas.save(out_path, quality=92)
    return str(out_path)


def generate_youtube_short(post: dict, image_path: str, audio_path: Optional[str] = None) -> str:
    output_dir = Path(settings.output_dir) / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)

    video_path = output_dir / f"{post['rss_id']}.mp4"

    cmd = [
        settings.ffmpeg_binary,
        "-y",
        "-loop",
        "1",
        "-i",
        image_path,
    ]

    if audio_path and os.path.exists(audio_path):
        cmd += ["-i", audio_path]

    cmd += [
        "-vf",
        "scale=1080:1080, pad=1080:1920:0:420:color=black",
        "-t",
        "12",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
    ]

    if audio_path and os.path.exists(audio_path):
        cmd += ["-shortest", "-c:a", "aac"]
    else:
        cmd += ["-an"]

    cmd.append(str(video_path))

    subprocess.run(cmd, check=True)
    return str(video_path)
