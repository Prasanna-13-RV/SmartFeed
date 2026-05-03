from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import requests as _rq
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent

_FONT_CANDIDATES = [
    Path(settings.font_path),
    _PROJECT_ROOT / "assets" / "fonts" / "Montserrat-Regular.ttf",
    Path("../assets/fonts/Montserrat-Regular.ttf"),
    # Linux (Render / Docker with fonts-liberation)
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    # Windows fallbacks
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/calibrib.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int, max_lines: int = 5) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(" ".join(current))
    return lines[:max_lines]


def _draw_centered(draw, text: str, y: int, font, fill, canvas_w: int) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (canvas_w - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, fill=fill, font=font)


def _overlay(canvas: Image.Image, x: int, y: int, w: int, h: int,
             color: tuple = (0, 0, 0), alpha: int = 150) -> Image.Image:
    """Composite a semi-transparent colored rectangle over the canvas region."""
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([(x, y), (x + w, y + h)], fill=(*color, alpha))
    return Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")


def _fetch_rss_image(url: str, size: tuple[int, int]) -> Optional[Image.Image]:
    """Download and smart-crop RSS image to exact target size. Returns None on failure."""
    if not url:
        return None
    try:
        resp = _rq.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        img_w, img_h = img.size
        tw, th = size
        scale = max(tw / img_w, th / img_h)
        nw, nh = int(img_w * scale), int(img_h * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        top = (nh - th) // 2
        return img.crop((left, top, left + tw, top + th))
    except Exception as e:
        print(f"[media] RSS image fetch failed: {e}")
        return None


# ─────────────────────────────────────────────────
#  INSTAGRAM TEMPLATES  (1080 × 1080)
# ─────────────────────────────────────────────────

def _ig_dark(post: dict, out_path: Path) -> None:
    """Template 1 — Dark Bold (orange accent, RSS photo strip)"""
    W, H = 1080, 1080
    FOOTER_TOP = H - 110
    canvas = Image.new("RGB", (W, H), (18, 22, 38))

    rss_img = _fetch_rss_image(post.get("image_url", ""), (W, 310))
    has_img = rss_img is not None
    if has_img:
        canvas.paste(rss_img, (0, 215))
        canvas = _overlay(canvas, 0, 215, W, 310, (18, 22, 38), 155)

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (W, 210)], fill=(210, 55, 15))
    draw.rectangle([(0, 210), (W, 218)], fill=(255, 100, 40))
    draw.rectangle([(0, FOOTER_TOP), (W, H)], fill=(10, 12, 22))

    brand_font = _load_font(56)
    _draw_centered(draw, "SMARTFEED", 72, brand_font, "white", W)

    cat_font = _load_font(28)
    cat_text = f"  #{post.get('category', 'news').upper()}  "
    cb = draw.textbbox((0, 0), cat_text, font=cat_font)
    cw = cb[2] - cb[0] + 24
    ch = cb[3] - cb[1] + 24
    cat_y = 540 if has_img else 240
    pill_x = (W - cw) // 2
    draw.rounded_rectangle([(pill_x, cat_y), (pill_x + cw, cat_y + ch)], radius=14, fill=(255, 100, 40))
    _draw_centered(draw, cat_text, cat_y + 8, cat_font, "white", W)

    title_font = _load_font(46)
    title_lines = _wrap_text(draw, post["title"], title_font, W - 100, max_lines=3)
    y = cat_y + ch + 18
    for line in title_lines:
        _draw_centered(draw, line, y, title_font, (255, 255, 255), W)
        y += 56

    desc = (post.get("description") or "").strip()
    if desc:
        y += 10
        draw.rectangle([(W // 2 - 80, y), (W // 2 + 80, y + 3)], fill=(255, 100, 40))
        y += 16
        desc_font = _load_font(24)
        line_h = 32
        max_desc = max(1, min(5, (FOOTER_TOP - 20 - y) // line_h))
        for line in _wrap_text(draw, desc, desc_font, W - 120, max_lines=max_desc):
            _draw_centered(draw, line, y, desc_font, (190, 198, 215), W)
            y += line_h

    canvas.save(str(out_path), quality=95)


def _ig_light(post: dict, out_path: Path) -> None:
    """Template 2 — Light Clean (white background, blue accent)"""
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), (248, 250, 255))

    rss_img = _fetch_rss_image(post.get("image_url", ""), (W, 370))
    has_img = rss_img is not None
    if has_img:
        canvas.paste(rss_img, (0, 0))
        canvas = _overlay(canvas, 0, 0, W, 370, (248, 250, 255), 40)

    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0, 0), (W, 8)], fill=(37, 99, 235))
    if has_img:
        draw.rectangle([(0, 370), (W, 378)], fill=(37, 99, 235))

    content_y = 398 if has_img else 90
    brand_font = _load_font(40)
    _draw_centered(draw, "SMARTFEED", content_y, brand_font, (37, 99, 235), W)

    cat_font = _load_font(28)
    cat_text = f"  #{post.get('category', 'news').upper()}  "
    cb = draw.textbbox((0, 0), cat_text, font=cat_font)
    cw = cb[2] - cb[0] + 24
    ch = cb[3] - cb[1] + 24
    cat_y = content_y + 58
    pill_x = (W - cw) // 2
    draw.rounded_rectangle([(pill_x, cat_y), (pill_x + cw, cat_y + ch)], radius=14, fill=(37, 99, 235))
    _draw_centered(draw, cat_text, cat_y + 8, cat_font, "white", W)

    title_font = _load_font(52)
    title_lines = _wrap_text(draw, post["title"], title_font, W - 100, max_lines=4)
    y = cat_y + ch + 28
    for line in title_lines:
        _draw_centered(draw, line, y, title_font, (15, 23, 42), W)
        y += 64

    y += 10
    draw.rectangle([(W // 2 - 60, y), (W // 2 + 60, y + 3)], fill=(37, 99, 235))
    y += 22

    desc = (post.get("description") or "").strip()
    if desc and y < 960:
        desc_font = _load_font(28)
        for line in _wrap_text(draw, desc, desc_font, W - 120, max_lines=5):
            _draw_centered(draw, line, y, desc_font, (75, 85, 115), W)
            y += 40

    draw.rectangle([(0, H - 8), (W, H)], fill=(37, 99, 235))
    canvas.save(str(out_path), quality=95)


def _ig_photo(post: dict, out_path: Path) -> None:
    """Template 3 — Photo Overlay (RSS image as full background)"""
    W, H = 1080, 1080
    canvas = Image.new("RGB", (W, H), (20, 20, 30))

    rss_img = _fetch_rss_image(post.get("image_url", ""), (W, H))
    if rss_img:
        canvas.paste(rss_img, (0, 0))

    canvas = _overlay(canvas, 0, 0, W, H, (0, 0, 0), 165)
    canvas = _overlay(canvas, 0, 0, W, 240, (0, 0, 0), 80)
    canvas = _overlay(canvas, 0, H - 140, W, 140, (0, 0, 0), 100)

    draw = ImageDraw.Draw(canvas)
    ACCENT = (233, 69, 96)

    brand_font = _load_font(48)
    smart_bbox = draw.textbbox((60, 60), "SMART", font=brand_font)
    draw.text((60, 60), "SMART", fill="white", font=brand_font)
    draw.text((smart_bbox[2], 60), "FEED", fill=ACCENT, font=brand_font)

    cat_font = _load_font(30)
    cat_text = f"#{post.get('category', 'news').upper()}"
    cb = draw.textbbox((0, 0), cat_text, font=cat_font)
    cw, ch = cb[2] - cb[0] + 24, cb[3] - cb[1] + 24
    draw.rounded_rectangle([(60, 138), (60 + cw, 138 + ch)], radius=12, fill=ACCENT)
    draw.text((72, 144), cat_text, fill="white", font=cat_font)

    title_font = _load_font(56)
    title_lines = _wrap_text(draw, post["title"], title_font, W - 100, max_lines=4)
    y = 340
    for line in title_lines:
        _draw_centered(draw, line, y, title_font, (255, 255, 255), W)
        y += 70

    y += 16
    draw.rectangle([(W // 2 - 80, y), (W // 2 + 80, y + 3)], fill=ACCENT)
    y += 22

    desc = (post.get("description") or "").strip()
    if desc:
        desc_font = _load_font(30)
        for line in _wrap_text(draw, desc, desc_font, W - 120, max_lines=5):
            _draw_centered(draw, line, y, desc_font, (220, 225, 235), W)
            y += 42

    canvas.save(str(out_path), quality=95)


def generate_instagram_image(post: dict, template: int = 1) -> str:
    output_dir = Path(settings.output_dir) / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{post['rss_id']}.jpg"
    if template == 2:
        _ig_light(post, out_path)
    elif template == 3:
        _ig_photo(post, out_path)
    else:
        _ig_dark(post, out_path)
    return str(out_path)


# ─────────────────────────────────────────────────
#  YOUTUBE TEMPLATES  (1080 × 1920 — Shorts 9:16)
# ─────────────────────────────────────────────────

def _yt_photo(post: dict, out_path: Path) -> None:
    """Video template — 9:16 Shorts format, full RSS image bg, text centred in lower half"""
    W, H = 1080, 1920
    ACCENT = (255, 100, 40)  # orange

    canvas = Image.new("RGB", (W, H), (20, 20, 30))

    rss_img = _fetch_rss_image(post.get("image_url", ""), (W, H))
    if rss_img:
        canvas.paste(rss_img, (0, 0))

    # Uniform dark overlay
    canvas = _overlay(canvas, 0, 0, W, H, (0, 0, 0), 185)
    # Extra darkening at top (brand area)
    canvas = _overlay(canvas, 0, 0, W, 260, (0, 0, 0), 80)
    # Heavier gradient in lower half where text lives
    canvas = _overlay(canvas, 0, H // 2, W, H // 2, (0, 0, 0), 60)
    canvas = _overlay(canvas, 0, H - 120, W, 120, (0, 0, 0), 80)

    draw = ImageDraw.Draw(canvas)

    # ── Brand top-left ──
    brand_font = _load_font(64)
    smart_bbox = draw.textbbox((64, 60), "SMART", font=brand_font)
    draw.text((64, 60), "SMART", fill="white", font=brand_font)
    draw.text((smart_bbox[2], 60), "FEED", fill=ACCENT, font=brand_font)

    # ── Category pill below brand ──
    cat_font = _load_font(36)
    cat_text = f"#{post.get('category', 'news').upper()}"
    cb = draw.textbbox((0, 0), cat_text, font=cat_font)
    cw, ch = cb[2] - cb[0] + 32, cb[3] - cb[1] + 22
    draw.rounded_rectangle([(64, 162), (64 + cw, 162 + ch)], radius=14, fill=ACCENT)
    draw.text((80, 169), cat_text, fill="white", font=cat_font)

    # ── Content block — vertically centred in the lower two-thirds ──
    title_font = _load_font(72)
    title_lines = _wrap_text(draw, post["title"], title_font, W - 120, max_lines=5)
    title_line_h = 90
    title_block_h = len(title_lines) * title_line_h

    desc = (post.get("description") or "").strip()
    desc_font = _load_font(38)
    desc_line_h = 58
    desc_lines = _wrap_text(draw, desc, desc_font, W - 140, max_lines=6) if desc else []
    desc_block_h = len(desc_lines) * desc_line_h

    divider_h = 36
    content_h = title_block_h + divider_h + desc_block_h

    # Centre content in the middle zone (between category pill bottom and near bottom)
    content_top = H // 2 - 80
    content_bottom = H - 140
    available = content_bottom - content_top
    y = content_top + max(0, (available - content_h) // 2)

    # ── Title ──
    for line in title_lines:
        _draw_centered(draw, line, y, title_font, (255, 255, 255), W)
        y += title_line_h

    # ── Divider ──
    y += 16
    draw.rectangle([(W // 2 - 100, y), (W // 2 + 100, y + 4)], fill=ACCENT)
    y += 24

    # ── Description ──
    for line in desc_lines:
        _draw_centered(draw, line, y, desc_font, (220, 225, 235), W)
        y += desc_line_h

    canvas.save(str(out_path), quality=95)


def _yt_navy(post: dict, out_path: Path) -> None:
    # routes to photo template
    _yt_photo(post, out_path)


def _yt_breaking(post: dict, out_path: Path) -> None:
    # kept for compatibility — routes to photo template
    _yt_photo(post, out_path)


def generate_youtube_image(post: dict, template: int = 1) -> str:
    output_dir = Path(settings.output_dir) / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    img_path = output_dir / f"{post['rss_id']}_yt.jpg"
    if template == 2:
        _yt_breaking(post, img_path)
    else:
        _yt_navy(post, img_path)
    return str(img_path)


def generate_youtube_short(post: dict, template: int = 1, audio_path: Optional[str] = None) -> str:
    """Generate 1080x1920 MP4 with optional background audio.

    Uses ``ffmpeg -loop 1`` to turn the static image into a video instead of
    loading all frames into memory via imageio, keeping RAM well under 512 MB.
    """
    import shutil as _shutil
    import subprocess as _subprocess
    import time as _time

    yt_image_path = generate_youtube_image(post, template=template)
    output_dir = Path(settings.output_dir) / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    _nonce = int(_time.time() * 1000)
    video_path = output_dir / f"{post['rss_id']}_{_nonce}.mp4"
    silent_path = output_dir / f"{post['rss_id']}_{_nonce}_silent.mp4"

    # Resolve ffmpeg binary
    ffmpeg_bin = settings.ffmpeg_binary
    if not _shutil.which(ffmpeg_bin) and not Path(ffmpeg_bin).is_file():
        try:
            import imageio_ffmpeg as _ioff  # type: ignore
            ffmpeg_bin = _ioff.get_ffmpeg_exe()
            print(f"[media] Using imageio-ffmpeg bundled binary: {ffmpeg_bin}")
        except Exception:
            ffmpeg_bin = None

    if not ffmpeg_bin:
        print("[media] ffmpeg not available — returning YouTube image")
        return yt_image_path

    # Pick audio: use provided path, or pick randomly from assets/audio/
    resolved_audio: Optional[Path] = None
    if audio_path and Path(audio_path).exists():
        resolved_audio = Path(audio_path)
    else:
        audio_dir = _PROJECT_ROOT / "assets" / "audio"
        audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
        if audio_files:
            import random as _random
            _random.shuffle(audio_files)
            resolved_audio = audio_files[0]

    try:
        # ── Step 1: create silent video from static image (memory-efficient) ──
        # ffmpeg -loop 1 reads one frame and streams it for -t seconds;
        # it never allocates a frame buffer per output frame.
        out_target = str(silent_path) if resolved_audio else str(video_path)
        silent_cmd = [
            ffmpeg_bin, "-y",
            "-loop", "1",
            "-i", str(yt_image_path),
            "-t", "10",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
                   "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            out_target,
        ]
        result = _subprocess.run(silent_cmd, capture_output=True)
        if result.returncode != 0:
            print(f"[media] ffmpeg image→video failed: {result.stderr.decode(errors='replace')}")
            return yt_image_path

        # ── Step 2: mix in background audio (optional) ──
        if resolved_audio:
            import random as _rnd
            # Probe audio duration so we pick a valid random start point
            probe = _subprocess.run(
                [ffmpeg_bin, "-i", str(resolved_audio)],
                capture_output=True, text=True,
            )
            duration = 60  # safe default if probe fails
            for line in probe.stderr.splitlines():
                if "Duration" in line:
                    try:
                        t = line.split("Duration:")[1].split(",")[0].strip()
                        h, m, s = t.split(":")
                        duration = int(h) * 3600 + int(m) * 60 + float(s)
                    except Exception:
                        pass

            max_start = max(0, int(duration) - 10)
            start = _rnd.randint(0, max_start)

            mix_cmd = [
                ffmpeg_bin, "-y",
                "-ss", str(start),
                "-i", str(resolved_audio),
                "-t", "10",
                "-i", str(silent_path),
                "-map", "1:v", "-map", "0:a",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                "-filter:a", "volume=0.35",
                str(video_path),
            ]
            mix_result = _subprocess.run(mix_cmd, capture_output=True)
            if mix_result.returncode == 0:
                silent_path.unlink(missing_ok=True)
                print(f"[media] Audio mixed: {resolved_audio.name} (start={start}s)")
            else:
                print("[media] ffmpeg audio mix failed, using silent video")
                silent_path.rename(video_path)

        print(f"[media] YouTube Short saved: {video_path}")
        return str(video_path)

    except Exception as e:
        import traceback
        print(f"[media] Video generation failed: {e}")
        traceback.print_exc()
        return yt_image_path


