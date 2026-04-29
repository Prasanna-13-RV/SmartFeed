from __future__ import annotations

from hashlib import sha256
from typing import Dict, List
import random
import xml.etree.ElementTree as ET
import requests

RSS_FEEDS: Dict[str, str] = {
    "tamil": "https://www.dailythanthi.com/rss/latest-news.xml",
    "english": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "sports": "https://www.espn.com/espn/rss/news",
}


PLATFORMS = ["instagram", "youtube"]


def _extract_items(xml_text: str, category: str) -> List[dict]:
    root = ET.fromstring(xml_text)
    items: List[dict] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip() or link or title
        if not title:
            continue
        rss_id = sha256(guid.encode("utf-8")).hexdigest()
        items.append(
            {
                "rss_id": rss_id,
                "title": title,
                "category": category,
                "source_link": link,
                "assigned_platform": random.choice(PLATFORMS),
                "post_status": "queued",
            }
        )

    return items


def fetch_all_rss() -> List[dict]:
    all_items: List[dict] = []

    for category, url in RSS_FEEDS.items():
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            all_items.extend(_extract_items(response.text, category))
        except Exception:
            # Keep pipeline resilient even when one feed fails.
            continue

    return all_items
