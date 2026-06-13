"""
Phase 10: Inkrementelle Synchronisation
Scannt den Channel, vergleicht mit bestehender videos_full.json,
lädt nur neue Transkripte + Thumbnails, aktualisiert sync_state.json.

Aufruf:
    python scripts/10_sync.py [--dry-run]

Output:
    - Updates data/videos_full.json (nur neue Videos angehängt)
    - Updates data/sync_state.json
    - Erstellt für neue Videos Bookmark-Entries in data/per_video_deep_dives/pending/
"""

import argparse
import json
import sys
import time
import urllib.request
import ssl
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

ROOT = Path(__file__).parent.parent
VIDEOS_FILE = ROOT / "data" / "videos_full.json"
SYNC_STATE = ROOT / "data" / "sync_state.json"
THUMB_DIR = ROOT / "data" / "thumbnails"
PER_VIDEO_DIR = ROOT / "data" / "per_video_deep_dives"
PER_VIDEO_PENDING = PER_VIDEO_DIR / "pending"
PER_VIDEO_ASSETS = ROOT / "data" / "per_video_assets"
CHANNEL_URL = "https://www.youtube.com/@everlastai/videos"

_session = requests.Session()
_session.verify = False


def categorize(title: str) -> str:
    title_low = title.lower()
    if any(k in title_low for k in ["claude", "anthropic", "opus", "mythos", "colossus"]):
        return "claude"
    if any(k in title_low for k in ["agent", "agentic", "subagent", "codex", "hive mind", "workflow"]):
        return "agents"
    if any(k in title_low for k in ["interview", "im gespräch", "prof.", "dr."]):
        return "interview"
    if any(k in title_low for k in ["roboter", "humanoid", "tesla", "optimus", "robotik", "neuromorphic"]):
        return "robotik"
    if any(k in title_low for k in ["business", "umsatz", "post-labor", "deindustri", "wirtschaft", "ökonomie"]):
        return "business"
    if any(k in title_low for k in ["gpt", "openai", "gemini", "google", "gemma", "imagegen"]):
        return "google-openai"
    if any(k in title_low for k in ["china", "europa", "huawei", "geopoliti"]):
        return "geopolitik"
    return "tools"


def calculate_importance(video: dict) -> int:
    score = 5
    views = video.get("view_count") or 0
    if views > 50000: score += 2
    elif views > 20000: score += 1
    duration = video.get("duration") or 0
    if duration > 1200: score += 1
    elif duration < 300: score -= 2
    return max(1, min(10, score))


def load_state() -> dict:
    if SYNC_STATE.exists():
        return json.loads(SYNC_STATE.read_text(encoding="utf-8"))
    return {
        "last_sync_at": None,
        "last_channel_scan_at": None,
        "known_video_ids": [],
        "pending_new_videos": [],
        "sync_history": [],
    }


def save_state(state: dict):
    SYNC_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def load_videos_full() -> dict:
    if VIDEOS_FILE.exists():
        return json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    return {"meta": {}, "videos": []}


def scan_channel_new_only(known_ids: set, max_new: int = 30) -> list[dict]:
    """Scanne Channel, gib nur Videos zurück die noch nicht in known_ids sind."""
    ydl_opts = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "extract_flat": True, "playlistend": 60, "nocheckcertificate": True,
    }
    print(f"  → Scanne {CHANNEL_URL} ...")
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
    entries = info.get("entries", [])
    print(f"  → {len(entries)} Einträge gefunden (flat)")

    new_videos = []
    for entry in entries:
        vid = entry.get("id")
        if not vid or vid in known_ids:
            continue
        # Volle Metadaten holen
        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "nocheckcertificate": True}) as ydl:
                v = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        except Exception as e:
            print(f"    ⚠ Fehler bei {vid}: {e}")
            continue
        upload_date = v.get("upload_date")
        if not upload_date:
            continue
        new_videos.append({
            "id": vid,
            "title": v.get("title", ""),
            "published_date": datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d"),
            "duration_min": round((v.get("duration") or 0) / 60, 1),
            "view_count": v.get("view_count") or 0,
            "like_count": v.get("like_count") or 0,
            "description": (v.get("description") or "")[:1000],
            "thumbnail_url": v.get("thumbnail", ""),
            "chapters": v.get("chapters") or [],
            "source_url": f"https://www.youtube.com/watch?v={vid}",
            "category": categorize(v.get("title", "")),
            "importance_score": calculate_importance(v),
        })
        if len(new_videos) >= max_new:
            break
    return new_videos


def fetch_transcript(video_id: str):
    try:
        api = YouTubeTranscriptApi(http_client=_session)
        transcript_list = api.list(video_id)
    except Exception as e:
        return None, f"list-error: {e}"

    transcript_obj = None
    for lang in ["de", "de-DE", "en", "en-US"]:
        try:
            transcript_obj = transcript_list.find_transcript([lang])
            break
        except Exception:
            continue
    if not transcript_obj:
        try:
            transcript_obj = next(iter(transcript_list))
        except Exception:
            return None, "no-transcript"

    try:
        fetched = transcript_obj.fetch()
    except Exception as e:
        return None, f"fetch-error: {e}"

    timestamps = [{"time": round(s.start, 2), "text": s.text} for s in fetched]
    full_text = " ".join(s.text for s in fetched)
    return {
        "full_text": full_text,
        "with_timestamps": timestamps,
        "language": transcript_obj.language_code,
        "is_generated": transcript_obj.is_generated,
    }, None


def download_thumbnail(video_id: str, url: str) -> str:
    if not url:
        return ""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out_path = THUMB_DIR / f"{video_id}.jpg"
    if out_path.exists():
        return str(out_path.relative_to(ROOT))
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=ctx, timeout=15) as response:
            out_path.write_bytes(response.read())
        return str(out_path.relative_to(ROOT))
    except Exception:
        return ""


def download_preview_images(video_id: str) -> dict:
    """Lade Vorschau-Bilder von YouTube CDN (hqdefault, sd1-3, maxresdefault)."""
    PER_VIDEO_ASSETS.mkdir(parents=True, exist_ok=True)
    video_dir = PER_VIDEO_ASSETS / video_id
    video_dir.mkdir(exist_ok=True)
    images = {}
    sources = {
        "hero": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        "preview_1": f"https://i.ytimg.com/vi/{video_id}/1.jpg",
        "preview_2": f"https://i.ytimg.com/vi/{video_id}/2.jpg",
        "preview_3": f"https://i.ytimg.com/vi/{video_id}/3.jpg",
    }
    ctx = ssl._create_unverified_context()
    for key, url in sources.items():
        out_path = video_dir / f"{key}.jpg"
        if out_path.exists():
            images[key] = str(out_path.relative_to(ROOT))
            continue
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=15) as response:
                if response.status == 200:
                    out_path.write_bytes(response.read())
                    images[key] = str(out_path.relative_to(ROOT))
        except Exception:
            pass
    return images


def create_pending_per_video_deep_dive(video: dict):
    """Lege Pending-Bookmark für Per-Video-Deep-Dive an."""
    PER_VIDEO_PENDING.mkdir(parents=True, exist_ok=True)
    fname = f"{video['id']}.json"
    path = PER_VIDEO_PENDING / fname
    payload = {
        "video_id": video["id"],
        "title": video["title"],
        "published_date": video["published_date"],
        "category": video["category"],
        "bookmarked_at": datetime.now().isoformat(),
        "status": "pending",
        "type": "per_video",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Inkrementelle Channel-Synchronisation")
    parser.add_argument("--dry-run", action="store_true", help="Nur prüfen, nichts schreiben")
    parser.add_argument("--max-new", type=int, default=30, help="Maximum neue Videos pro Sync (default 30)")
    args = parser.parse_args()

    start = time.time()
    print(f"=== SYNC START ({datetime.now().isoformat()}) ===")

    state = load_state()
    known_ids = set(state.get("known_video_ids", []))
    print(f"  → Bekannt: {len(known_ids)} Video-IDs")

    videos_data = load_videos_full()
    existing_videos = videos_data.get("videos", [])
    # Sicherheits-check: known_ids muss alle in videos_full.json IDs enthalten
    for v in existing_videos:
        known_ids.add(v["id"])

    new_videos = scan_channel_new_only(known_ids, max_new=args.max_new)
    print(f"  → {len(new_videos)} NEUE Videos entdeckt")

    if args.dry_run:
        print("  ℹ DRY-RUN — keine Änderungen")
        for v in new_videos:
            print(f"     - {v['id']} | {v['published_date']} | {v['title'][:60]}")
        return

    enriched_new = []
    for i, v in enumerate(new_videos, 1):
        print(f"  → [{i}/{len(new_videos)}] Lade Transkript + Bilder: {v['id']}")
        transcript_data, err = fetch_transcript(v["id"])
        if transcript_data:
            v["transcript"] = transcript_data["full_text"]
            v["transcript_timestamps"] = transcript_data["with_timestamps"]
            v["transcript_language"] = transcript_data["language"]
            v["transcript_is_generated"] = transcript_data["is_generated"]
            print(f"     ✓ Transkript ({transcript_data['language']}, {len(transcript_data['full_text'])//1000}k chars)")
        else:
            v["transcript"] = ""
            v["transcript_timestamps"] = []
            v["transcript_language"] = ""
            v["transcript_is_generated"] = False
            v["transcript_error"] = err
            print(f"     ⚠ Kein Transkript: {err}")

        # Thumbnail + Preview-Bilder
        thumb_path = download_thumbnail(v["id"], v.get("thumbnail_url", ""))
        if thumb_path:
            v["thumbnail_path"] = thumb_path
        previews = download_preview_images(v["id"])
        if previews:
            v["preview_images"] = previews
            print(f"     ✓ {len(previews)} Vorschau-Bilder")

        # Pending Per-Video Deep Dive anlegen
        create_pending_per_video_deep_dive(v)

        enriched_new.append(v)
        time.sleep(0.5)  # Rate-Limit

    # Speichern
    all_videos = existing_videos + enriched_new
    all_videos.sort(key=lambda x: x["published_date"], reverse=True)
    videos_data["videos"] = all_videos
    videos_data["meta"]["extracted_at"] = datetime.now().isoformat()
    videos_data["meta"]["total_videos"] = len(all_videos)
    VIDEOS_FILE.write_text(json.dumps(videos_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # State
    state["last_sync_at"] = datetime.now().isoformat()
    state["last_channel_scan_at"] = datetime.now().isoformat()
    state["known_video_ids"] = sorted({v["id"] for v in all_videos})
    state["pending_new_videos"] = [
        {"id": v["id"], "discovered_at": state["last_sync_at"], "title": v["title"], "status": "pending_assignment"}
        for v in enriched_new
    ]
    duration = round(time.time() - start)
    state.setdefault("sync_history", []).append({
        "at": state["last_sync_at"],
        "found_new": len(enriched_new),
        "duration_seconds": duration,
    })
    save_state(state)

    print()
    print(f"=== SYNC FERTIG ===")
    print(f"   Neue Videos:    {len(enriched_new)}")
    print(f"   Gesamt-Videos:  {len(all_videos)}")
    print(f"   Dauer:          {duration}s")
    print()
    if enriched_new:
        print(f"   Nächste Schritte:")
        print(f"   1. python scripts/03_analyze_rulebased.py")
        print(f"   2. python scripts/04_build_site_data.py")
        print(f"   3. python scripts/05_extract_briefings.py")
        print(f"   4. python scripts/07_build_site_book.py")
        print(f"   5. python scripts/08_build_concept_index.py")
        print(f"   6. Per-Video-Deep-Dives synthetisieren (Agent im Chat)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        sys.exit(1)
