from __future__ import annotations

from hashlib import sha256
from typing import Dict, List
import random
import xml.etree.ElementTree as ET
import requests

RSS_FEEDS: Dict[str, str] = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "india": "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "cricket": "https://feeds.feedburner.com/NDTV-Sports",
}


PLATFORMS = ["instagram", "youtube"]


def _extract_items(xml_text: str, category: str) -> List[dict]:
    root = ET.fromstring(xml_text)
    items: List[dict] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        guid = (item.findtext("guid") or "").strip() or link or title
        
        if not title:
            continue
        
        # Try to extract image from multiple sources
        image_url = None
        MRSS = "{http://search.yahoo.com/mrss/}"

        # 1. media:thumbnail (BBC, most common)
        thumbnail = item.find(f"{MRSS}thumbnail")
        if thumbnail is not None:
            image_url = thumbnail.get("url")

        # 2. media:content[@medium="image"]
        if not image_url:
            for media_content in item.findall(f"{MRSS}content"):
                if media_content.get("medium") == "image" or (media_content.get("type") or "").startswith("image/"):
                    image_url = media_content.get("url")
                    break

        # 3. <enclosure type="image/...">
        if not image_url:
            enclosure = item.find("enclosure")
            if enclosure is not None and (enclosure.get("type") or "").startswith("image/"):
                image_url = enclosure.get("url")

        # 4. <img src="..."> inside description HTML
        if not image_url and "<img" in description:
            try:
                import re
                match = re.search(r'src=["\']([^"\']+)["\']', description)
                if match:
                    image_url = match.group(1)
            except Exception:
                pass
        
        # Strip HTML tags from description
        import re
        clean_desc = re.sub(r"<[^>]+>", "", description)[:200]
        
        rss_id = sha256(guid.encode("utf-8")).hexdigest()
        items.append(
            {
                "rss_id": rss_id,
                "title": title,
                "category": category,
                "description": clean_desc,
                "image_url": image_url or "",
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
            response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            all_items.extend(_extract_items(response.text, category))
        except Exception:
            # Keep pipeline resilient even when one feed fails.
            continue

    return all_items
