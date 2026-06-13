"""
18_extract_praxis.py — Praxis-Wissen aus Videos extrahieren (Layer 3)

Liest videos_full.json und extrahiert für jedes Video via Ollama
konkrete, handlungsorientierte Praxis-Tipps.

Ausgabe:
  - praxis_items-Feld in jedem Video (videos_full.json)
  - data/praxis/praxis_index.json (aggregiert für UI)

Kategorien:
  tool        → konkrete Software/Tool-Empfehlung
  technik     → Methode/Vorgehensweise
  workflow    → Ablauf/Prozess/Pipeline
  framework   → konzeptuelles Modell/Denkrahmen
  mindset     → Haltung/Perspektive

Usage:
  python scripts/18_extract_praxis.py            # alle ohne praxis_items
  python scripts/18_extract_praxis.py --all      # alle neu (überschreiben)
  python scripts/18_extract_praxis.py --video ID # ein Video
  python scripts/18_extract_praxis.py --build    # nur Index neu bauen
  python scripts/18_extract_praxis.py --dry-run  # zeigen was passiert
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VIDEOS_FILE = ROOT / "data" / "videos_full.json"
PRAXIS_DIR  = ROOT / "data" / "praxis"
PRAXIS_INDEX = PRAXIS_DIR / "praxis_index.json"

SYSTEM_PROMPT = """Du bist ein Wissensextrakteur für ein deutsches KI-Wissensbuch.

Deine Aufgabe: Extrahiere aus dem Transkript eines YouTube-Videos konkrete,
handlungsorientierte Praxis-Tipps — Dinge, die ein Zuschauer in seiner Arbeit nutzen kann.

FORMAT (antworte NUR mit JSON-Array, kein Markdown-Wrapper, keine Erklärungen davor):
[
  {
    "text": "Konkreter Tipp in einem Satz (max 130 Zeichen)",
    "category": "tool|technik|workflow|framework|mindset",
    "kontext": "Ein erläuternder Satz mit Hintergrund (max 220 Zeichen)"
  }
]

KATEGORIEN:
- tool:      Konkrete Software, API, Plattform, Service die genutzt werden soll
- technik:   Spezifische Methode, Technik oder Vorgehensweise
- workflow:  Ablauf, Prozess, Pipeline, Routine die man adaptieren kann
- framework: Konzeptuelles Modell, Denkrahmen, Prinzip oder mentales Werkzeug
- mindset:   Haltung, Perspektivwechsel, Erkenntnis die das Handeln ändert

REGELN:
- 2-7 Items pro Video (auch bei Interviews und News-Videos gibt es lehrreiche Aussagen)
- Sowohl Tutorial-Tipps ("Nutze Tool X") als auch strategische Erkenntnisse ("Erkenne, dass...")
- Aus dem Transkript ableitbar — nicht erfinden
- Auf Deutsch formulieren
- Nur wenn das Transkript wirklich leer ist: gib [] zurück
- Antworte SOFORT mit dem JSON-Array, ohne Einleitung
"""

VALID_CATEGORIES = {"tool", "technik", "workflow", "framework", "mindset"}


def load_videos() -> dict:
    with open(VIDEOS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_videos(data: dict):
    with open(VIDEOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_json_from_response(text: str) -> list:
    """Parst JSON-Array aus LLM-Antwort, robust gegen Chain-of-Thought."""
    text = text.strip()
    # Markdown-Code-Blöcke entfernen
    text = re.sub(r"```[a-z]*\n?", "", text).replace("```", "")
    # Direktes JSON
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    # Letzten JSON-Array finden (Chain-of-Thought schreibt denken vor dem Array)
    last_bracket = text.rfind("[")
    if last_bracket == -1:
        return []
    # Klammern-zählen für korrektes Ende
    depth, end_pos = 0, -1
    for i, ch in enumerate(text[last_bracket:], last_bracket):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break
    if end_pos == -1:
        return []
    try:
        result = json.loads(text[last_bracket:end_pos])
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    return []


def extract_praxis_for_video(video: dict, dry_run: bool = False) -> list:
    """Extrahiert Praxis-Items für ein Video via Ollama."""
    transcript = video.get("transcript", "")
    if not transcript or len(transcript) < 200:
        print(f"  → Kein/zu kurzes Transkript, überspringe")
        return []

    # Transkript: Anfang + Mitte + Ende für breitere Abdeckung
    if len(transcript) > 6000:
        t_start = transcript[:2500]
        t_mid   = transcript[len(transcript)//2 - 500 : len(transcript)//2 + 500]
        t_end   = transcript[-1500:]
        transcript_snippet = t_start + "\n[...]\n" + t_mid + "\n[...]\n" + t_end
    else:
        transcript_snippet = transcript[:6000]

    user_content = f"""VIDEO: {video.get('title', 'Unbekannt')}
KANAL: Everlast AI
KATEGORIE: {video.get('category', 'Allgemein')}

TRANSKRIPT (Auszug):
{transcript_snippet}

Extrahiere die konkreten Praxis-Tipps aus diesem Video."""

    if dry_run:
        print(f"  [DRY-RUN] Würde Ollama aufrufen für: {video.get('title','?')[:60]}")
        return [
            {"text": "Beispiel-Tipp (dry run)", "category": "technik",
             "kontext": "Platzhalter-Kontext"}
        ]

    try:
        from ollama_client import synthesize, MODEL_FAST
        response = synthesize(SYSTEM_PROMPT, user_content,
                              model=MODEL_FAST, temperature=0.2, max_tokens=2000)
        items = extract_json_from_response(response)

        # Validierung
        validated = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            cat  = str(item.get("category", "")).strip().lower()
            ctx  = str(item.get("kontext", "")).strip()
            if not text or cat not in VALID_CATEGORIES:
                continue
            validated.append({"text": text[:150], "category": cat, "kontext": ctx[:250]})

        return validated[:7]

    except Exception as e:
        print(f"  FEHLER Ollama: {e}")
        return []


def build_praxis_index(videos: list) -> dict:
    """Baut den aggregierten Praxis-Index für die UI."""
    all_items = []
    by_category = {cat: [] for cat in VALID_CATEGORIES}
    by_video_category = {}

    for video in videos:
        video_cat = video.get("category", "Allgemein")
        if video_cat not in by_video_category:
            by_video_category[video_cat] = []

        for item in video.get("praxis_items", []):
            entry = {
                "text":      item.get("text", ""),
                "category":  item.get("category", "technik"),
                "kontext":   item.get("kontext", ""),
                "video_id":  video.get("id", ""),
                "video_title": video.get("title", ""),
                "video_category": video_cat,
                "source_url": video.get("source_url", ""),
            }
            all_items.append(entry)
            cat = item.get("category", "technik")
            if cat in by_category:
                by_category[cat].append(entry)
            by_video_category[video_cat].append(entry)

    return {
        "generated_at": datetime.now().isoformat(),
        "total_items":  len(all_items),
        "by_category":  by_category,
        "by_video_category": by_video_category,
        "all_items":    all_items,
    }


def save_praxis_index(index: dict):
    PRAXIS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PRAXIS_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Praxis-Wissen extrahieren")
    parser.add_argument("--all",     action="store_true", help="Alle Videos neu verarbeiten")
    parser.add_argument("--video",   type=str, help="Nur dieses Video (ID)")
    parser.add_argument("--build",   action="store_true", help="Nur Index neu bauen")
    parser.add_argument("--dry-run", action="store_true", help="Testlauf ohne Ollama")
    args = parser.parse_args()

    data = load_videos()
    videos = data.get("videos", [])

    if args.build:
        print("Baue Praxis-Index neu...")
        index = build_praxis_index(videos)
        save_praxis_index(index)
        print(f"Index gespeichert: {index['total_items']} Items in {PRAXIS_INDEX}")
        return

    # Welche Videos verarbeiten?
    if args.video:
        targets = [v for v in videos if v.get("id") == args.video]
        if not targets:
            print(f"FEHLER: Video {args.video} nicht gefunden")
            sys.exit(1)
    elif args.all:
        targets = videos
    else:
        # Nur Videos ohne praxis_items (oder mit leerer Liste)
        targets = [v for v in videos if not v.get("praxis_items")]

    if not targets:
        print("Alle Videos haben bereits praxis_items — nichts zu tun.")
        print("Nutze --all um alle neu zu verarbeiten.")
        # Index trotzdem bauen
        index = build_praxis_index(videos)
        save_praxis_index(index)
        return

    print(f"Verarbeite {len(targets)} Videos...")
    total_items = 0
    import time

    for i, video in enumerate(targets, 1):
        vid_id = video.get("id", "?")
        title  = video.get("title", "?")[:60]
        print(f"[{i}/{len(targets)}] {title} ({vid_id})")

        items = extract_praxis_for_video(video, dry_run=args.dry_run)
        video["praxis_items"] = items
        total_items += len(items)
        print(f"  → {len(items)} Praxis-Items extrahiert")
        if not args.dry_run and i < len(targets):
            time.sleep(1.5)  # Rate-Limit-Pause zwischen Requests

    if not args.dry_run:
        save_videos(data)
        print(f"\nVideos-Datei aktualisiert ({total_items} neue Items)")

    # Index immer neu bauen
    index = build_praxis_index(videos)
    if not args.dry_run:
        save_praxis_index(index)
    print(f"Praxis-Index: {index['total_items']} Items total")
    print(f"\nFertig. Kategorien:")
    for cat, items in index["by_category"].items():
        print(f"  {cat:12s}: {len(items)}")


if __name__ == "__main__":
    main()
