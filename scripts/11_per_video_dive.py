"""
Phase 11: Per-Video Deep-Dive Aggregator
Liest pending Per-Video-Bookmarks und sammelt für jeden alle relevanten Daten
für die Synthese durch den Agent.

Aufruf:
    python scripts/11_per_video_dive.py --list
    python scripts/11_per_video_dive.py --briefing <video_id>
    python scripts/11_per_video_dive.py --all-pending
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
PER_VIDEO_DIR = ROOT / "data" / "per_video_deep_dives"
PENDING_DIR = PER_VIDEO_DIR / "pending"
GENERATED_DIR = PER_VIDEO_DIR / "generated"
ASSETS_DIR = ROOT / "data" / "per_video_assets"
SECTIONS_DIR = ROOT / "data" / "knowledge_book" / "sections"
VIDEOS_FILE = ROOT / "data" / "videos_full.json"
INDEX_FILE = ROOT / "data" / "knowledge_book" / "_index.json"


def list_pending():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(PENDING_DIR.glob("*.json")):
        try:
            items.append({"file": f.name, **json.loads(f.read_text(encoding="utf-8"))})
        except Exception:
            pass
    return items


def load_video(video_id: str) -> dict:
    data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    for v in data["videos"]:
        if v["id"] == video_id:
            return v
    return None


def find_thematic_sections(video_id: str) -> list[dict]:
    """Finde Buch-Sektionen, die das Video als Quelle haben."""
    if not INDEX_FILE.exists():
        return []
    idx = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    sections = []
    for sid, sdata in idx.get("sections", {}).items():
        sources = sdata.get("source_videos", [])
        if video_id in sources:
            sections.append({
                "section_id": sid,
                "title": sdata.get("title", ""),
                "chapter_title": sdata.get("chapter_title", ""),
            })
    return sections


def build_briefing(bookmark: dict) -> dict:
    video_id = bookmark["video_id"]
    video = load_video(video_id)
    if not video:
        return {"error": f"Video {video_id} nicht in videos_full.json gefunden"}

    sections = find_thematic_sections(video_id)
    assets_dir = ASSETS_DIR / video_id
    images = {}
    if assets_dir.exists():
        for img in assets_dir.glob("*.jpg"):
            images[img.stem] = str(img.relative_to(ROOT))

    chapters = video.get("chapters", [])
    transcript = video.get("transcript", "")

    briefing = {
        "video_id": video_id,
        "title": video.get("title", ""),
        "published_date": video.get("published_date", ""),
        "duration_min": video.get("duration_min", 0),
        "view_count": video.get("view_count", 0),
        "category": video.get("category", ""),
        "thumbnail_path": video.get("thumbnail_path", ""),
        "preview_images": video.get("preview_images", images),
        "description": video.get("description", ""),
        "chapters": chapters,
        "transcript_length": len(transcript),
        "transcript_excerpt_intro": transcript[:2000] if transcript else "",
        "transcript_excerpt_end": transcript[-2000:] if transcript else "",
        "thematic_sections": sections,
        "source_url": video.get("source_url", ""),
    }
    return briefing


def workflow_briefing_text(bookmark: dict, briefing: dict) -> str:
    if "error" in briefing:
        return f"FEHLER: {briefing['error']}"

    chapters_block = "\n".join(
        f"  - [{int(c.get('start_time',0))}s-{int(c.get('end_time',0))}s] {c.get('title','')}"
        for c in briefing["chapters"][:15]
    )
    sections_block = "\n".join(
        f"  - [[{s['section_id']} {s['title']}]] ({s['chapter_title']})"
        for s in briefing["thematic_sections"]
    )
    images_block = "\n".join(
        f"  - {k}: {v}" for k, v in briefing["preview_images"].items()
    )
    return f"""# Per-Video Deep-Dive Agent-Briefing

## Video-Metadaten
- ID: {briefing['video_id']}
- Titel: {briefing['title']}
- Veröffentlicht: {briefing['published_date']}
- Dauer: {briefing['duration_min']:.0f} min · Views: {briefing['view_count']:,}
- Kategorie: {briefing['category']}
- URL: {briefing['source_url']}

## Bilder verfügbar
{images_block or "  (keine)"}

## Kapitel (mit Timestamps)
{chapters_block or "  (keine Kapitel)"}

## Bereits thematisch in Buch-Sektionen
{sections_block or "  (in keiner Sektion verwendet)"}

## Transkript
- Länge: {briefing['transcript_length']:,} Zeichen
- Erste 2000 Zeichen verfügbar
- Letzte 2000 Zeichen verfügbar
- Vollständiges Transkript: `data/videos_full.json` → videos[id={briefing['video_id']}].transcript

## Deine Aufgabe (Agent)

Schreibe einen Per-Video Deep-Dive im Lehrbuch-Stil.
Stil-Vorbild: `data/knowledge_book/sections/2.1.md`
Länge: 1500-2500 Wörter
Datei: `data/per_video_deep_dives/generated/{briefing['video_id']}.md`

**Pflicht-Frontmatter:**
```yaml
---
video_id: "{briefing['video_id']}"
title: "Deep Dive: {briefing['title'][:60]}..."
source_video_title: "{briefing['title']}"
published: "{briefing['published_date']}"
duration_min: {briefing['duration_min']:.0f}
view_count: {briefing['view_count']}
deep_dive_type: "per_video"
word_count: 2000
related_topics: []
related_sections: {[s['section_id'] for s in briefing['thematic_sections']]}
generated_at: "<ISO>"
hero_image: "{briefing['preview_images'].get('hero', '')}"
---
```

**Struktur:**

# Deep Dive: <Video-Titel> — Was DIESES Video wirklich bedeutet

![Hero]({briefing['preview_images'].get('hero', '')})

## Worum geht es? (3-Satz-Zusammenfassung)
(150 Wörter)

## Die Kern-Aussagen
Pro Kapitel eine Kern-Aussage mit Timestamp.
(400 Wörter)

## Was visuell gezeigt wird
Bezug zu Thumbnails/Preview-Bildern.
(200 Wörter)

## Wörtliche Schlüsselzitate (5-10)
Pro Zitat: Kontext-Satz, Zitat, Timestamp-Quelle.
(500 Wörter)

## Bedeutung für die Themen
Cross-Refs zu thematischen Sektionen: [[1.1 Titel]] etc.
(300 Wörter)

## Lese-Empfehlungen
Was als Nächstes lesen.
(150 Wörter)

## 📎 Marginalia
Person-/Tool-/Zahl-Marker aus dem Video.

**Auch speichern:**
`data/per_video_deep_dives/generated/{briefing['video_id']}.json`:
```json
{{
  "video_id": "{briefing['video_id']}",
  "title": "...",
  "word_count": <tatsächlich>,
  "quotes_count": <wieviele>,
  "generated_at": "<ISO>",
  "hero_image": "{briefing['preview_images'].get('hero', '')}"
}}
```

**Bookmark abräumen:**
Lösche `data/per_video_deep_dives/pending/{briefing['video_id']}.json`

Antworte am Ende mit:
"FERTIG Per-Video Deep Dive: {briefing['video_id']} ({{<wörter>}} Wörter)"
"""


SYNTHESIS_SYSTEM = """Du schreibst einen Per-Video Deep-Dive für ein Wissensbuch über den YouTube-Channel "Everlast AI" von Leonard Schmedding.

Stil: Narrativ-lehrbuchhaft, wie ein Qualitätsjournalist der ein komplexes Thema erklärt. Kein Marketing-Sprech, keine Übertreibungen. Ton-Setter: sachlich, erhellend, dicht.

Zitat-Format:
> "Exaktes Zitat aus dem Transkript"
> — *Video-Titel* ([▶ MM:SS](video:{video_id}?t={sekunden}))

Cross-References: [[X.Y Abschnittstitel]] für Verweise auf andere Buch-Sektionen.

Pflicht-Frontmatter (yaml, exakt dieses Format):
---
video_id: "{video_id}"
title: "Deep Dive: {titel_kurz}"
source_video_title: "{voller_titel}"
published: "{datum}"
duration_min: {minuten}
deep_dive_type: "per_video"
generated_at: "{iso_jetzt}"
---

Dann:
# Deep Dive: {kurztitel} — Was dieses Video wirklich lehrt

## Überblick (150 Wörter)
Worum geht es? Was ist die Kern-These? Warum ist dieses Video relevant?

## Die wichtigsten Aussagen (nach Kapiteln)
Pro Kapitel: Kern-Aussage (1-2 Sätze) + Zitat + Timestamp-Link.
Mindestens 5 Kapitel-Zusammenfassungen.

## Schlüsselzitate (mindestens 6)
Die stärksten Zitate aus dem Transkript, mit Kontext-Satz davor.
Format: exakt wie im Zitat-Format oben.

## Einordnung: Was bedeutet das?
Wie ordnet sich dieses Video in die größere KI-Entwicklung ein?
Cross-Refs zu verwandten Sektionen im Wissensbuch falls bekannt.

## Lese-Empfehlungen
2-3 Sektionen oder Deep Dives, die man danach lesen sollte.

Länge: 1500-2200 Wörter. Kein schmückendes Beiwerk. Keine Zusammenfassung am Ende."""


def synthesize_video(video_id: str, dry_run: bool = False) -> bool:
    """Synthetisiert einen Per-Video Deep Dive via LLM."""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from ollama_client import synthesize, MODEL_PRO
    except ImportError:
        print("  FEHLER: ollama_client nicht gefunden", file=sys.stderr)
        return False

    pending_path = PENDING_DIR / f"{video_id}.json"
    if not pending_path.exists():
        print(f"  Kein Bookmark für {video_id}", file=sys.stderr)
        return False

    bookmark = json.loads(pending_path.read_text(encoding="utf-8"))
    briefing = build_briefing(bookmark)
    if "error" in briefing:
        print(f"  FEHLER Briefing: {briefing['error']}", file=sys.stderr)
        return False

    video = load_video(video_id)
    transcript = (video.get("transcript") or "")[:8000]
    chapters_text = "\n".join(
        f"[{int(c.get('start_time',0))}s] {c.get('title','')}"
        for c in briefing["chapters"][:20]
    )
    sections_text = "\n".join(
        f"[[{s['section_id']} {s['title']}]]"
        for s in briefing["thematic_sections"]
    ) or "(noch nicht in Sektionen verarbeitet)"

    user_content = f"""VIDEO-ID: {video_id}
TITEL: {briefing['title']}
VERÖFFENTLICHT: {briefing['published_date']}
DAUER: {briefing['duration_min']:.0f} min
KATEGORIE: {briefing['category']}
URL: {briefing['source_url']}

KAPITEL:
{chapters_text or '(keine Kapitel)'}

BEREITS IN BUCH-SEKTIONEN:
{sections_text}

TRANSKRIPT (erste 8000 Zeichen):
{transcript}
"""

    system = SYNTHESIS_SYSTEM.replace("{video_id}", video_id)

    print(f"  [{video_id}] Synthetisiere '{briefing['title'][:60]}...' ...", flush=True)
    t0 = time.time()

    if dry_run:
        print(f"  DRY RUN — würde LLM aufrufen mit {len(user_content)} Zeichen")
        return True

    try:
        result = synthesize(system, user_content, model=MODEL_PRO, temperature=0.3, max_tokens=4000)
    except Exception as e:
        print(f"  LLM FEHLER: {e}", file=sys.stderr)
        return False

    elapsed = time.time() - t0
    word_count = len(result.split())
    print(f"  OK in {elapsed:.0f}s — {word_count} Wörter", flush=True)

    if word_count < 300:
        print(f"  WARNUNG: Zu kurz ({word_count} Wörter), überspringe", file=sys.stderr)
        return False

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    md_path = GENERATED_DIR / f"{video_id}.md"
    md_path.write_text(result, encoding="utf-8")

    meta = {
        "video_id": video_id,
        "title": f"Deep Dive: {briefing['title'][:60]}",
        "source_video_title": briefing["title"],
        "published": briefing["published_date"],
        "duration_min": briefing["duration_min"],
        "word_count": word_count,
        "generated_at": datetime.now().isoformat(),
        "hero_image": briefing["preview_images"].get("hero", ""),
        "related_sections": [s["section_id"] for s in briefing["thematic_sections"]],
    }
    (GENERATED_DIR / f"{video_id}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Bookmark entfernen
    pending_path.unlink(missing_ok=True)
    print(f"  Gespeichert: {md_path.name} + {video_id}.json")
    return True


def main():
    parser = argparse.ArgumentParser(description="Per-Video Deep-Dive Aggregator + Synthesizer")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--briefing", help="video_id")
    parser.add_argument("--all-pending", action="store_true")
    parser.add_argument("--synthesize", help="video_id — LLM-Synthese für ein Video")
    parser.add_argument("--synthesize-all", action="store_true", help="LLM-Synthese für alle pending")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list:
        items = list_pending()
        if not items:
            print("Keine pending Per-Video Deep Dives.")
            return
        print(f"Pending Per-Video Deep Dives ({len(items)}):")
        for it in items:
            print(f"  - {it['video_id']:15} {it.get('published_date',''):10} {it.get('title','')[:60]}")
        return

    if args.briefing:
        path = PENDING_DIR / f"{args.briefing}.json"
        if not path.exists():
            print(f"Bookmark {args.briefing}.json nicht in pending/")
            return
        bookmark = json.loads(path.read_text(encoding="utf-8"))
        b = build_briefing(bookmark)
        print(workflow_briefing_text(bookmark, b))
        return

    if args.all_pending:
        items = list_pending()
        if not items:
            print("Keine pending Per-Video Deep Dives.")
            return
        for it in items:
            b = build_briefing(it)
            print(workflow_briefing_text(it, b))
            print("\n" + "="*70 + "\n")
        return

    if args.synthesize:
        ok = synthesize_video(args.synthesize, dry_run=args.dry_run)
        sys.exit(0 if ok else 1)

    if args.synthesize_all:
        items = list_pending()
        real_items = [it for it in items if it["video_id"] != "test"]
        print(f"Starte Synthese für {len(real_items)} Videos...")
        ok_count, fail_count = 0, 0
        for it in real_items:
            ok = synthesize_video(it["video_id"], dry_run=args.dry_run)
            if ok:
                ok_count += 1
            else:
                fail_count += 1
            time.sleep(2)
        print(f"\nFertig: {ok_count} OK, {fail_count} Fehler")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
