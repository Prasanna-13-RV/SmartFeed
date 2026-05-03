"""
setup_yt_auth.py — ONE-TIME local script to authenticate with YouTube via OAuth2.

Run this on your local machine (NOT on the server):

    python tools/setup_yt_auth.py

It will:
  1. Open a yt-dlp OAuth2 device-auth flow — you visit a URL and enter a code.
  2. Save the token to a local cache folder.
  3. Print the YT_OAUTH_TOKEN_B64 value to paste into Render.

OAuth2 refresh tokens do NOT expire unless you revoke access.
You only need to run this once (or if you revoke and need to re-authorize).
"""
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "_yt_auth_cache"
TOKEN_FILE = CACHE_DIR / "youtube-oauth2" / "token.json"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("YouTube OAuth2 one-time setup")
print("=" * 60)
print()
print("yt-dlp will show you:")
print("  1. A URL  →  open it in your browser")
print("  2. A code →  enter it on that page")
print("  3. Sign in with your Google account")
print()
print("Starting authentication flow...\n")

result = subprocess.run(
    [
        sys.executable, "-m", "yt_dlp",
        "--username", "oauth2",
        "--password", "",
        "--cache-dir", str(CACHE_DIR),
        "--skip-download",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
    # Do NOT capture output — user must see the URL and code interactively
)

if not TOKEN_FILE.exists():
    print("\n❌  Token file not found. Authentication may have failed.")
    print(f"    Expected: {TOKEN_FILE}")
    sys.exit(1)

b64 = base64.b64encode(TOKEN_FILE.read_bytes()).decode()

print("\n" + "=" * 60)
print("✅  Authentication successful!")
print("=" * 60)
print()
print("Add this environment variable to your Render service:")
print()
print(f"  Key:   YT_OAUTH_TOKEN_B64")
print(f"  Value: {b64}")
print()
print("Steps:")
print("  1. Go to render.com → your backend service → Environment")
print("  2. Add Environment Variable: YT_OAUTH_TOKEN_B64 = <value above>")
print("  3. Save → Render will redeploy automatically")
print()
print("That's it. This token will work indefinitely.")
