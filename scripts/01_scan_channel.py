"""
Phase A: Channel-Scanner
Scannt einen YouTube-, TikTok- oder Instagram-Channel und filtert Videos.

Aufruf:
    python scripts/01_scan_channel.py                        # Standard: @everlastai
    python scripts/01_scan_channel.py --url <URL>            # Beliebiger Channel
    python scripts/01_scan_channel.py --url <URL> --days 60  # Zeitraum anpassen

Output: data/videos_list.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from yt_dlp import YoutubeDL

# Standard-Konfiguration — wird von channel.config.json überschrieben falls vorhanden
_CONFIG_FILE = Path(__file__).parent.parent / "channel.config.json"
_CONFIG = {}
if _CONFIG_FILE.exists():
    try:
        _CONFIG = json.load(open(_CONFIG_FILE, encoding="utf-8"))
    except Exception:
        pass

DEFAULT_URL = _CONFIG.get("channel_url", "https://www.youtube.com/@everlastai/videos")
DAYS_BACK = _CONFIG.get("days_back", 90)
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "videos_list.json"

# Themen-Kategorisierung — aus channel.config.json oder Everlast-Fallback
CATEGORY_KEYWORDS = _CONFIG.get("category_keywords") or {
    "claude": ["claude", "anthropic", "opus", "sonnet", "haiku", "mythos", "colossus"],
    "agents": ["agent", "agentic", "subagent", "hive mind", "codex", "workflow"],
    "interview": ["interview", "im gespräch", "prof.", "dr."],
    "robotik": ["roboter", "humanoid", "tesla", "optimus", "robotik", "robotergym", "neuromorphic", "nvidia"],
    "business": ["business", "geschäft", "umsatz", "post-labor", "deindustriali", "wirtschaft", "ökonomie"],
    "google-openai": ["gpt", "openai", "gemini", "google", "gemma", "imagegen", "spud"],
    "tools": ["tool", "stack", "lokale ki", "installieren", "wissensdatenbank", "voicely", "wispr"],
    "geopolitik": ["china", "europa", "huawei", "geopoliti", "involution"],
}


def detect_platform(url: str) -> str:
    """Erkennt Plattform aus URL: youtube | tiktok | instagram."""
    url_low = url.lower()
    if "tiktok.com" in url_low:
        return "tiktok"
    if "instagram.com" in url_low:
        return "instagram"
    return "youtube"


def make_source_url(platform: str, video_id: str, uploader: str = "") -> str:
    """Baut korrekte Source-URL je nach Plattform."""
    if platform == "tiktok":
        return f"https://www.tiktok.com/@{uploader}/video/{video_id}"
    if platform == "instagram":
        return f"https://www.instagram.com/reel/{video_id}/"
    return f"https://www.youtube.com/watch?v={video_id}"


def categorize(title: str) -> str:
    """Schnelle Keyword-basierte Kategorisierung."""
    title_low = title.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in title_low)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "tools"


def calculate_importance(video: dict) -> int:
    """Berechne Importance-Score 1-10 basierend auf Views, Dauer, Aktualität."""
    score = 5
    views = video.get("view_count") or 0
    if views > 50000:
        score += 2
    elif views > 20000:
        score += 1
    duration = video.get("duration") or 0
    if duration > 1200:
        score += 1
    elif duration < 300:
        score -= 2
    return max(1, min(10, score))


def scan_channel(url: str, days_back: int) -> list[dict]:
    """Scannt einen Channel auf einer beliebigen Plattform (YouTube/TikTok/Instagram)."""
    platform = detect_platform(url)
    cutoff_date = datetime.now() - timedelta(days=days_back)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": 300,
        "nocheckcertificate": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries", [])
    channel_name = info.get("channel") or info.get("uploader") or info.get("title") or "Unbekannt"
    uploader_id = info.get("uploader_id") or info.get("channel_id") or ""
    print(f"Channel: {channel_name}  ({platform})  —  {len(entries)} Einträge")

    videos = []
    for i, entry in enumerate(entries, 1):
        video_id = entry.get("id")
        if not video_id:
            continue

        # Direkte URL je Plattform
        if platform == "tiktok":
            video_url = f"https://www.tiktok.com/@{uploader_id}/video/{video_id}"
        elif platform == "instagram":
            video_url = f"https://www.instagram.com/reel/{video_id}/"
        else:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "nocheckcertificate": True}) as ydl:
                v = ydl.extract_info(video_url, download=False)
        except Exception as e:
            print(f"  [{i}/{len(entries)}] FEHLER {video_id}: {e}")
            continue

        upload_date_str = v.get("upload_date")
        if not upload_date_str:
            continue

        upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
        if upload_date < cutoff_date:
            print(f"  [{i}/{len(entries)}] Älter als {days_back}d — Scan beendet")
            break

        video_data = {
            "id": video_id,
            "platform": platform,
            "title": v.get("title", ""),
            "published_date": upload_date.strftime("%Y-%m-%d"),
            "duration_min": round((v.get("duration") or 0) / 60, 1),
            "duration": v.get("duration") or 0,
            "view_count": v.get("view_count") or 0,
            "like_count": v.get("like_count") or 0,
            "description": (v.get("description") or "")[:1000],
            "thumbnail_url": v.get("thumbnail", ""),
            "chapters": v.get("chapters") or [],
            "source_url": make_source_url(platform, video_id, uploader_id),
            "category": categorize(v.get("title", "")),
            "importance_score": calculate_importance(v),
        }
        videos.append(video_data)
        print(f"  [{i}/{len(entries)}] {upload_date_str} | {video_data['category']:12} | {v.get('title','')[:55]}")

    videos.sort(key=lambda x: x["published_date"], reverse=True)
    return videos, channel_name, uploader_id, platform


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL, help="Channel-URL (YouTube/TikTok/Instagram)")
    parser.add_argument("--days", type=int, default=DAYS_BACK, help="Tage zurück (default: 90)")
    parser.add_argument("--output", default=str(OUTPUT_FILE), help="Output JSON-Pfad")
    args = parser.parse_args()

    url = args.url
    platform = detect_platform(url)

    print(f"Scanne: {url}")
    print(f"Plattform: {platform}  |  Zeitraum: letzte {args.days} Tage")
    print("-" * 60)

    videos, channel_name, uploader_id, platform = scan_channel(url, args.days)

    output = {
        "meta": {
            "channel": channel_name,
            "handle": uploader_id,
            "channel_url": url,
            "platform": platform,
            "scanned_at": datetime.now().isoformat(),
            "period_days": args.days,
            "cutoff_date": (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d"),
            "total_videos": len(videos),
        },
        "videos": videos,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 60)
    print(f"OK  {len(videos)} Videos gespeichert → {out_path.name}")
    cats = {}
    for v in videos:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:15} {n:3d}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
