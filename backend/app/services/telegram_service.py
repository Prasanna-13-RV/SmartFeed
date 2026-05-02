from __future__ import annotations

import urllib3
import requests
from app.config import settings

# Corporate proxies often do SSL inspection — suppress the resulting warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def send_telegram_message(message: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=15, verify=False)
