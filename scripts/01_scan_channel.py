"""
Phase A: Channel-Scanner
Scannt den Everlast AI YouTube-Channel und filtert Videos der letzten 90 Tage.

Output: data/videos_list.json
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from yt_dlp import YoutubeDL

# Konfiguration
CHANNEL_URL = "https://www.youtube.com/@everlastai/videos"
DAYS_BACK = 90
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "videos_list.json"

# Themen-Kategorisierung (Keyword-basiert für schnelle Vor-Klassifikation)
CATEGORY_KEYWORDS = {
    "claude": ["claude", "anthropic", "opus", "sonnet", "haiku", "mythos", "colossus"],
    "agents": ["agent", "agentic", "subagent", "hive mind", "codex", "workflow"],
    "interview": ["interview", "im gespräch", "prof.", "dr."],
    "robotik": ["roboter", "humanoid", "tesla", "optimus", "robotik", "robotergym", "neuromorphic", "nvidia"],
    "business": ["business", "geschäft", "umsatz", "post-labor", "deindustriali", "wirtschaft", "ökonomie"],
    "google-openai": ["gpt", "openai", "gemini", "google", "gemma", "imagegen", "spud"],
    "tools": ["tool", "stack", "lokale ki", "installieren", "wissensdatenbank", "voicely", "wispr"],
    "geopolitik": ["china", "europa", "huawei", "geopoliti", "involution"],
}


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
    score = 5  # Basis

    views = video.get("view_count") or 0
    if views > 50000:
        score += 2
    elif views > 20000:
        score += 1

    duration = video.get("duration") or 0
    if duration > 1200:  # > 20 Min = Tiefes Thema
        score += 1
    elif duration < 300:  # < 5 Min = Short
        score -= 2

    return max(1, min(10, score))


def main():
    print(f"Scanne Channel: {CHANNEL_URL}")
    print(f"Zeitraum: letzte {DAYS_BACK} Tage")
    print("-" * 60)

    cutoff_date = datetime.now() - timedelta(days=DAYS_BACK)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": 200,
        "nocheckcertificate": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)

    entries = info.get("entries", [])
    print(f"Channel-Scan: {len(entries)} Einträge gefunden (flat).")

    # Detail-Scan: Wir brauchen Upload-Datum, deshalb extract_info pro Video
    print(f"Lade Details für {len(entries)} Videos...")

    videos = []
    for i, entry in enumerate(entries, 1):
        video_id = entry.get("id")
        if not video_id:
            continue

        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "nocheckcertificate": True}) as ydl:
                v = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False,
                )
        except Exception as e:
            print(f"  [{i}/{len(entries)}] FEHLER bei {video_id}: {e}")
            continue

        # Upload-Datum prüfen
        upload_date_str = v.get("upload_date")  # YYYYMMDD
        if not upload_date_str:
            continue

        upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
        if upload_date < cutoff_date:
            print(f"  [{i}/{len(entries)}] Aus Zeitraum: {upload_date_str} — Scan beendet")
            break  # Sortiert nach Datum, ältere folgen

        video_data = {
            "id": video_id,
            "title": v.get("title", ""),
            "published_date": upload_date.strftime("%Y-%m-%d"),
            "duration_min": round((v.get("duration") or 0) / 60, 1),
            "view_count": v.get("view_count") or 0,
            "like_count": v.get("like_count") or 0,
            "description": (v.get("description") or "")[:1000],
            "thumbnail_url": v.get("thumbnail", ""),
            "chapters": v.get("chapters") or [],
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "category": categorize(v.get("title", "")),
            "importance_score": calculate_importance(v),
        }
        videos.append(video_data)
        print(f"  [{i}/{len(entries)}] {upload_date_str} | {video_data['category']:12} | {v.get('title','')[:60]}")

    # Sortieren nach Datum (neueste zuerst)
    videos.sort(key=lambda x: x["published_date"], reverse=True)

    output = {
        "meta": {
            "channel": "Everlast AI",
            "handle": "@everlastai",
            "channel_url": CHANNEL_URL,
            "scanned_at": datetime.now().isoformat(),
            "period_days": DAYS_BACK,
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
            "total_videos": len(videos),
        },
        "videos": videos,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 60)
    print(f"OK {len(videos)} Videos in {OUTPUT_FILE.name} gespeichert")
    print(f"  Pfad: {OUTPUT_FILE}")
    print()

    # Kategorie-Verteilung
    cats = {}
    for v in videos:
        cats[v["category"]] = cats.get(v["category"], 0) + 1
    print("Kategorie-Verteilung:")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:15} {n:3d}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
