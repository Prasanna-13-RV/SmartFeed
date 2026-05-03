"""clip_service.py

Download YouTube videos via yt-dlp, split into short clips, and convert each
clip to portrait/Shorts format (1080×1920) with a title label overlay.
The original download and raw split files are removed after processing.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List

import imageio_ffmpeg
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

# All clips live under generated/videos/clips/<video_id>/
CLIPS_DIR = Path(settings.output_dir) / "videos" / "clips"

# Shorts canvas
SHORTS_W, SHORTS_H = 1080, 1920

# Resolve ffmpeg: use the configured binary if it's on PATH, otherwise
# fall back to the binary bundled with imageio-ffmpeg.
def _get_ffmpeg() -> str:
    import shutil
    if shutil.which(settings.ffmpeg_binary):
        return settings.ffmpeg_binary
    return imageio_ffmpeg.get_ffmpeg_exe()

_FFMPEG = _get_ffmpeg()

# Safe YouTube video-ID pattern  (11 chars, alphanumeric + - _)
_YT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent.parent

_FONT_CANDIDATES = [
    _PROJECT_ROOT / "assets" / "fonts" / "Montserrat-Regular.ttf",
    Path(settings.font_path).resolve(),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/calibrib.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
]


def _load_pillow_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _make_label_png(label: str, out_path: Path) -> None:
    """
    Render a dark semi-transparent bar (SHORTS_W × 100 px) with white
    centred text using Pillow and save it as a PNG with an alpha channel.
    This avoids all ffmpeg drawtext / fontconfig / escaping issues.
    """
    bar_w, bar_h = SHORTS_W, 100
    img = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 0))
    # dark semi-transparent fill
    bar = Image.new("RGBA", (bar_w, bar_h), (0, 0, 0, 165))
    img = Image.alpha_composite(img, bar)

    draw = ImageDraw.Draw(img)
    font = _load_pillow_font(42)

    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = max((bar_w - tw) // 2, 10)
    y = (bar_h - th) // 2

    # subtle shadow
    draw.text((x + 2, y + 2), label, fill=(0, 0, 0, 200), font=font)
    # main white text
    draw.text((x, y), label, fill=(255, 255, 255, 255), font=font)

    img.save(str(out_path), "PNG")


# Player clients that bypass YouTube bot-detection without cookies.
# tv_embedded is an embedded TV client; ios uses the Apple app context.
_YT_CLIENTS = ["tv_embedded", "ios", "android"]


def _yt_base_opts() -> dict:
    """Common yt-dlp options applied to every request."""
    opts: dict = {
        "quiet": True,
        "extractor_args": {"youtube": {"player_client": _YT_CLIENTS}},
    }
    cookies = settings.yt_cookies_file
    if cookies and Path(cookies).exists():
        opts["cookiefile"] = cookies
    return opts


    """Raise ValueError if video_id contains path-traversal characters."""
    if not _YT_ID_RE.match(video_id):
        raise ValueError(f"Unsafe video_id: {video_id!r}")


def _split_video(source: Path, clip_dir: Path, clip_duration: int) -> List[Path]:
    """
    Split *source* into fixed-duration clips (stream-copy, fast).
    Files are written to clip_dir/raw_N.mp4 (1-based).
    """
    clip_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = str(clip_dir / "raw_%d.mp4")

    result = subprocess.run(
        [
            _FFMPEG, "-y",
            "-i", str(source),
            "-c", "copy",
            "-map", "0",
            "-segment_time", str(clip_duration),
            "-segment_start_number", "1",
            "-f", "segment",
            "-reset_timestamps", "1",
            output_pattern,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split failed:\n{result.stderr}")

    return sorted(
        clip_dir.glob("raw_*.mp4"),
        key=lambda p: int(p.stem.split("_")[1]),
    )


def _to_shorts(
    src: Path,
    dst: Path,
    label: str,
) -> None:
    """
    Re-encode *src* as a 1080×1920 Shorts clip with a label bar at the top.

    Pipeline:
      1. Pillow renders the label bar as a transparent PNG (no ffmpeg escaping).
      2. ffmpeg scales/pads the video to 1080×1920, then composites the PNG
         over the top using the `overlay` filter.
    """
    label_png = src.parent / f"_label_{src.stem}.png"
    _make_label_png(label, label_png)

    scale_pad = (
        f"scale={SHORTS_W}:{SHORTS_H}:force_original_aspect_ratio=decrease,"
        f"pad={SHORTS_W}:{SHORTS_H}:(ow-iw)/2:(oh-ih)/2:black"
    )

    # Overlay the label bar 50 px from the top
    result = subprocess.run(
        [
            _FFMPEG, "-y",
            "-i", str(src),
            "-i", str(label_png),
            "-filter_complex", f"[0:v]{scale_pad}[bg];[bg][1:v]overlay=0:50",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(dst),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    label_png.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg shorts conversion failed:\n{result.stderr}")


def _auto_clip_duration(total_seconds: int) -> int:
    """
    Pick either 60 s or 45 s per clip:
    - Videos ≤ 60 s are kept as a single clip (no splitting needed).
    - Otherwise pick whichever candidate leaves the smallest remainder.
      When both leave the same remainder, prefer the longer clip (fewer clips).
    """
    if total_seconds <= 60:
        return total_seconds  # single clip

    candidates = [60, 45]
    # Sort key: (remainder ascending, clip_size descending) → fewer clips wins ties
    return min(candidates, key=lambda d: (total_seconds % d, -d))


def process_youtube_url(url: str, clip_duration: int | None = None) -> dict:
    """
    Download the YouTube video at *url*, split it into short clips, convert
    each clip to Shorts format (1080×1920 with title label), delete all
    intermediate files, and return::

        {
            "video_id": "<yt-id>",
            "title": "<video title>",
            "video_duration": <total seconds>,
            "clip_duration": <seconds used>,
            "links": ["http://…/video/<id>/1", …]
        }

    When *clip_duration* is ``None`` the duration is read from YouTube
    metadata and a sensible default is chosen automatically.
    """
    # ── 1. Extract metadata (no download yet) ──────────────────────────────
    info_opts: dict = {**_yt_base_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(info_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    video_id: str = info["id"]
    _validate_video_id(video_id)

    video_title: str = info.get("title") or video_id

    # Duration is in seconds (int) in the yt-dlp info dict; default to 60
    # if somehow absent.
    total_duration: int = int(info.get("duration") or 60)
    if clip_duration is None:
        clip_duration = _auto_clip_duration(total_duration)

    clip_dir = CLIPS_DIR / video_id
    clip_dir.mkdir(parents=True, exist_ok=True)
    original_path = clip_dir / "original.mp4"

    # ── 2. Download ────────────────────────────────────────────────────────
    dl_opts: dict = {
        **_yt_base_opts(),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(original_path),
        "ffmpeg_location": str(Path(_FFMPEG).parent),
    }
    with yt_dlp.YoutubeDL(dl_opts) as ydl:
        ydl.download([url])

    # ── 3. Split into raw clips (stream-copy, fast) ────────────────────────
    raw_clips = _split_video(original_path, clip_dir, clip_duration)
    total_clips = len(raw_clips)

    # ── 4. Convert each raw clip to Shorts format ──────────────────────────
    final_clips: List[Path] = []
    for idx, raw in enumerate(raw_clips, start=1):
        label = f"Part {idx}/{total_clips}"
        dst = clip_dir / f"clip_{idx}.mp4"
        _to_shorts(raw, dst, label)
        raw.unlink(missing_ok=True)   # delete raw segment
        final_clips.append(dst)

    # ── 5. Delete original download ────────────────────────────────────────
    original_path.unlink(missing_ok=True)

    # ── 6. Build public links ──────────────────────────────────────────────
    base = settings.base_url.rstrip("/")
    links = [f"{base}/video/{video_id}/{i}" for i in range(1, total_clips + 1)]

    return {
        "video_id": video_id,
        "title": video_title,
        "video_duration": total_duration,
        "clip_duration": clip_duration,
        "links": links,
    }
