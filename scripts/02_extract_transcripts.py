"""
Phase B: Transkript-Extraktor
Lädt für jedes Video aus videos_list.json das deutsche Transkript via YouTube Transcript API.

Output: data/videos_full.json (Vollständige Daten + Transkripte)
"""

import json
import ssl
import sys
import time
import urllib.request
import warnings
from pathlib import Path

import requests
from urllib3.exceptions import InsecureRequestWarning

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

INPUT_FILE = Path(__file__).parent.parent / "data" / "videos_list.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "videos_full.json"
THUMB_DIR = Path(__file__).parent.parent / "data" / "thumbnails"

# SSL-Workaround (Corp-Proxy ohne Cert-Bundle)
warnings.simplefilter("ignore", InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# requests-Session mit deaktivierter SSL-Verifikation
_session = requests.Session()
_session.verify = False


def fetch_transcript(video_id: str):
    """Lade Transkript für ein Video. Versuche DE, dann DE auto, dann EN."""
    try:
        api = YouTubeTranscriptApi(http_client=_session)
        transcript_list = api.list(video_id)
    except (TranscriptsDisabled, VideoUnavailable) as e:
        return None, str(e)
    except Exception as e:
        return None, f"list-error: {e}"

    # Priorität: manuelles DE → auto DE → manuelles EN → auto EN
    languages_to_try = ["de", "de-DE", "en", "en-US"]
    transcript_obj = None
    for lang in languages_to_try:
        try:
            transcript_obj = transcript_list.find_transcript([lang])
            break
        except Exception:
            continue

    if not transcript_obj:
        # Fallback: erstes verfügbares
        try:
            transcript_obj = next(iter(transcript_list))
        except Exception:
            return None, "no-transcript-available"

    try:
        fetched = transcript_obj.fetch()
    except Exception as e:
        return None, f"fetch-error: {e}"

    # FetchedTranscript ist iterierbar mit FetchedTranscriptSnippet-Objekten (text, start, duration)
    timestamps = [
        {"time": round(s.start, 2), "text": s.text}
        for s in fetched
    ]
    full_text = " ".join(s.text for s in fetched)
    return {
        "full_text": full_text,
        "with_timestamps": timestamps,
        "language": transcript_obj.language_code,
        "is_generated": transcript_obj.is_generated,
    }, None


def download_thumbnail(video_id: str, url: str) -> str:
    """Lade Thumbnail lokal herunter."""
    if not url:
        return ""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    ext = "jpg"
    out_path = THUMB_DIR / f"{video_id}.{ext}"
    if out_path.exists():
        return str(out_path.relative_to(OUTPUT_FILE.parent.parent))
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=ctx, timeout=15) as response:
            out_path.write_bytes(response.read())
        return str(out_path.relative_to(OUTPUT_FILE.parent.parent))
    except Exception as e:
        print(f"  ! Thumbnail-Fehler {video_id}: {e}")
        return ""


def main():
    if not INPUT_FILE.exists():
        print(f"FEHLER: {INPUT_FILE} nicht gefunden. Erst 01_scan_channel.py laufen lassen.")
        sys.exit(1)

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    videos = data["videos"]
    total = len(videos)

    print(f"Extrahiere Transkripte für {total} Videos...")
    print("-" * 60)

    enriched = []
    stats = {"with_transcript": 0, "without_transcript": 0, "with_thumbnail": 0}

    for i, v in enumerate(videos, 1):
        vid = v["id"]
        title_short = v["title"][:55].encode("ascii", "replace").decode()
        print(f"  [{i:>2}/{total}] {vid} | {title_short}")

        # Transkript laden
        transcript_data, err = fetch_transcript(vid)
        if transcript_data:
            stats["with_transcript"] += 1
            v["transcript"] = transcript_data["full_text"]
            v["transcript_timestamps"] = transcript_data["with_timestamps"]
            v["transcript_language"] = transcript_data["language"]
            v["transcript_is_generated"] = transcript_data["is_generated"]
            length_kchar = len(transcript_data["full_text"]) // 1000
            print(f"           Transkript OK ({transcript_data['language']}, {length_kchar}k chars)")
        else:
            stats["without_transcript"] += 1
            v["transcript"] = ""
            v["transcript_timestamps"] = []
            v["transcript_language"] = ""
            v["transcript_is_generated"] = False
            v["transcript_error"] = err
            print(f"           Kein Transkript: {err}")

        # Thumbnail
        thumb_path = download_thumbnail(vid, v.get("thumbnail_url", ""))
        if thumb_path:
            v["thumbnail_path"] = thumb_path
            stats["with_thumbnail"] += 1

        enriched.append(v)

        # Rate Limit (kleine Pause)
        time.sleep(0.3)

    output = {
        "meta": {**data["meta"], "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
        "stats": stats,
        "videos": enriched,
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 60)
    print(f"OK Extraktion abgeschlossen")
    print(f"   Mit Transkript: {stats['with_transcript']}/{total}")
    print(f"   Ohne Transkript: {stats['without_transcript']}")
    print(f"   Mit Thumbnail: {stats['with_thumbnail']}")
    print(f"   Output: {OUTPUT_FILE.name}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
