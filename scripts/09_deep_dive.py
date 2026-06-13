"""
Phase 9: Deep-Dive-Aggregator
Liest Bookmark aus data/deep_dives/pending/, sammelt aus Channel-Daten alles
zum Topic, schreibt Dashboard-Daten und beschreibt den Workflow für den
Agent-Schritt (Synthese).

Aufruf:
    python scripts/09_deep_dive.py --list                  # listet pending
    python scripts/09_deep_dive.py --aggregate <bookmark>  # baut Dashboard-Daten
    python scripts/09_deep_dive.py --workflow <bookmark>   # gibt Agent-Prompt aus
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DD_DIR = ROOT / "data" / "deep_dives"
PENDING_DIR = DD_DIR / "pending"
GENERATED_DIR = DD_DIR / "generated"
DASHBOARD_DIR = DD_DIR / "dashboard_data"
SECTIONS_DIR = ROOT / "data" / "knowledge_book" / "sections"
INDEX_FILE = ROOT / "data" / "knowledge_book" / "_index.json"
VIDEOS_FILE = ROOT / "data" / "videos_full.json"
KG_FILE = ROOT / "data" / "knowledge_graph.json"


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "topic"


def list_pending():
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(PENDING_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append({"file": f.name, **data})
        except Exception as e:
            print(f"  WARN: cannot read {f.name}: {e}")
    return items


def find_mentions_in_sections(topic: str) -> list[dict]:
    """Suche Sektionen, die das Topic erwaehnen — mit Snippet."""
    if not SECTIONS_DIR.exists():
        return []
    topic_low = topic.lower()
    found = []
    for md in sorted(SECTIONS_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        body = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
        body_low = body.lower()
        # Pattern mit Wortgrenzen
        pattern = r"(?<![A-Za-z0-9])" + re.escape(topic_low) + r"(?![A-Za-z0-9])"
        if not re.search(pattern, body_low):
            continue
        # Frontmatter parsen
        fm = {}
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"').strip("'")
        # Snippets sammeln (kontextuelle 200-Zeichen-Auszuege)
        snippets = []
        for m in re.finditer(pattern, body_low):
            start = max(0, m.start() - 100)
            end = min(len(body), m.end() + 100)
            snippet = body[start:end].strip().replace("\n", " ")
            snippets.append(snippet)
            if len(snippets) >= 3:
                break
        found.append({
            "section_id": fm.get("section_id", md.stem),
            "title": fm.get("title", ""),
            "chapter": fm.get("chapter", ""),
            "tier": fm.get("tier", ""),
            "snippets": snippets,
            "mentions_count": len(re.findall(pattern, body_low)),
        })
    return found


def find_videos_for_topic(topic: str) -> list[dict]:
    """Finde Quell-Videos in denen Topic vorkommt (Transkript)."""
    if not VIDEOS_FILE.exists():
        return []
    data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    topic_low = topic.lower()
    pattern = r"(?<![A-Za-z0-9])" + re.escape(topic_low) + r"(?![A-Za-z0-9])"
    found = []
    for v in data["videos"]:
        transcript = (v.get("transcript", "") or "").lower()
        count = len(re.findall(pattern, transcript))
        if count == 0:
            continue
        # Erste Erwaehnung mit Timestamp finden
        timestamps = v.get("transcript_timestamps", [])
        first_at = None
        for t in timestamps:
            if topic_low in (t.get("text") or "").lower():
                first_at = round(t.get("time", 0))
                break
        found.append({
            "id": v["id"],
            "title": v["title"],
            "published_date": v["published_date"],
            "duration_min": v["duration_min"],
            "view_count": v["view_count"],
            "mentions_count": count,
            "first_mention_seconds": first_at,
            "url": v["source_url"],
        })
    found.sort(key=lambda x: x["published_date"])
    return found


def find_related_concepts(topic: str) -> list[dict]:
    """Holt verwandte Konzepte aus knowledge_graph."""
    if not KG_FILE.exists():
        return []
    kg = json.loads(KG_FILE.read_text(encoding="utf-8"))
    concepts = kg.get("concepts", {})
    connections = kg.get("connections", [])
    # Falls Topic ein Konzept ist: hole Verbindungen
    if topic in concepts:
        related = []
        for c in connections:
            if c["from"] == topic:
                other = c["to"]
            elif c["to"] == topic:
                other = c["from"]
            else:
                continue
            if other in concepts:
                related.append({
                    "label": other,
                    "category": concepts[other]["category"],
                    "color": concepts[other]["color"],
                    "video_count": concepts[other]["video_count"],
                    "strength": c["strength"],
                })
        related.sort(key=lambda x: -x["strength"])
        return related[:15]
    return []


def aggregate_dashboard(bookmark: dict) -> dict:
    topic = bookmark["topic"]
    slug = slugify(topic)

    sections = find_mentions_in_sections(topic)
    videos = find_videos_for_topic(topic)
    related = find_related_concepts(topic)

    # Timeline-Daten (welche Videos, wann, mit Wichtigkeit)
    timeline = [
        {
            "date": v["published_date"],
            "video_id": v["id"],
            "title": v["title"],
            "mentions": v["mentions_count"],
            "views": v["view_count"],
            "first_mention_seconds": v["first_mention_seconds"],
        }
        for v in videos
    ]

    # Personen-Cloud aus knowledge_graph (Co-Occurrence)
    if KG_FILE.exists():
        kg = json.loads(KG_FILE.read_text(encoding="utf-8"))
        people = [
            c for c in kg.get("concepts", {}).values()
            if c["category"] == "person" and topic in c.get("videos", [])
        ]
    else:
        people = []

    # Tools die das Topic gemeinsam mit anderen Videos haben
    tool_co_occurrence = [
        r for r in related if r.get("category") == "tool"
    ]
    company_co_occurrence = [
        r for r in related if r.get("category") == "company"
    ]

    dashboard = {
        "topic": topic,
        "slug": slug,
        "type": bookmark.get("type", "concept"),
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "sections_count": len(sections),
            "videos_count": len(videos),
            "related_concepts": len(related),
        },
        "sections": sections,
        "videos": videos,
        "timeline": timeline,
        "related_concepts": related,
        "tools": tool_co_occurrence,
        "companies": company_co_occurrence,
        "people": [{"label": p["label"], "video_count": p["video_count"]} for p in people],
    }
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    out = DASHBOARD_DIR / f"{slug}.json"
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
    return dashboard


def workflow_briefing(bookmark: dict, dashboard: dict) -> str:
    """Generiert Agent-Prompt für die Deep-Dive-Synthese."""
    topic = bookmark["topic"]
    slug = dashboard["slug"]

    top_videos = dashboard["videos"][:5]
    top_sections = dashboard["sections"][:8]
    top_related = dashboard["related_concepts"][:8]

    sections_block = "\n".join(
        f"  - [{s['section_id']}] {s['title']} ({s['mentions_count']}x erwähnt)"
        for s in top_sections
    )
    videos_block = "\n".join(
        f"  - {v['published_date']} {v['title'][:60]} ({v['mentions_count']}x, video:{v['id']})"
        for v in top_videos
    )
    related_block = "\n".join(
        f"  - {r['label']} ({r['category']}, Stärke {r['strength']:.1f})"
        for r in top_related
    )

    return f"""# Deep-Dive Agent-Briefing: "{topic}"

## Eingabe-Daten

**Topic:** {topic}
**Type:** {bookmark.get('type', 'concept')}
**Slug:** {slug}
**Sektionen die das Topic erwaehnen:** {dashboard['stats']['sections_count']}
**Quell-Videos:** {dashboard['stats']['videos_count']}
**Verwandte Konzepte:** {dashboard['stats']['related_concepts']}

## Top-Sektionen
{sections_block}

## Top-Videos
{videos_block}

## Top verwandte Konzepte
{related_block}

## Deine Aufgabe (Agent)

Schreibe eine Deep-Dive-Sektion auf Deutsch im Lehrbuch-Stil (siehe `sections/2.1.md` als Prototyp).
Datei: `sections/dd-{slug}.md`
Länge: 2000-3000 Wörter

**Pflicht-Frontmatter:**
```yaml
---
section_id: "dd-{slug}"
title: "Deep Dive: {topic}"
chapter: "Deep Dives"
chapter_number: 13
tier: "mega"
word_count: 2500
read_minutes: 13
deep_dive: true
deep_dive_topic: "{topic}"
sources: [<Channel-Video-IDs>]
external_sources: [<URLs>]
---
```

**4 Pflicht-Abschnitte:**

1. **Was ist {topic}? — Eine Standortbestimmung**
   - Definition aus Channel-Material + Web-Kontext
   - Warum es jetzt wichtig ist

2. **Wie der Channel das Thema behandelt**
   - Chronologie der Erwaehnungen (Timeline)
   - Mindestens 8 wörtliche Zitate aus den Sektionen (Format: `> "..."` mit Quelle)
   - Wichtige Pivots/Erkenntnisse

3. **Was die Welt dazu sagt (Web-Recherche)**
   - WebSearch nach "{topic} 2026" oder vergleichbar
   - Maximal 3 externe Quellen
   - Vergleich Channel-Perspektive vs. extern

4. **Luecken und offene Fragen**
   - Was wird NICHT im Channel behandelt
   - Welche Fragen bleiben offen

**Cross-References:** Alle Top-Sektionen oben referenzieren `[[X.Y Titel]]`.

**Speichere am Ende:**
1. `data/knowledge_book/sections/dd-{slug}.md`
2. `data/deep_dives/generated/{slug}.json` mit: topic, slug, word_count, generated_at, sources_count

**Nach Abschluss:** Pipeline-Schritte 06+07+08 laufen lassen, damit Buch + Site aktualisiert werden.

## Bookmark-Datei (bitte verschieben/löschen nach Abschluss)
`{bookmark.get('_file', '?')}`
"""


def main():
    parser = argparse.ArgumentParser(description="Deep-Dive Aggregator + Workflow")
    parser.add_argument("--list", action="store_true", help="Liste pending Deep Dives")
    parser.add_argument("--aggregate", help="Bookmark-Datei: baue Dashboard-Daten")
    parser.add_argument("--workflow", help="Bookmark-Datei: gib Agent-Prompt aus")
    parser.add_argument("--all-pending", action="store_true", help="Alle pending aggregieren + Briefings ausgeben")
    args = parser.parse_args()

    if args.list:
        items = list_pending()
        if not items:
            print("Keine pending Deep Dives.")
            return
        print(f"Pending Deep Dives ({len(items)}):")
        for it in items:
            print(f"  • {it['file']:50}  topic={it.get('topic','?')}  type={it.get('type','?')}")
        return

    if args.aggregate:
        path = PENDING_DIR / args.aggregate if not Path(args.aggregate).exists() else Path(args.aggregate)
        bookmark = json.loads(path.read_text(encoding="utf-8"))
        dash = aggregate_dashboard(bookmark)
        print(f"OK Dashboard für '{bookmark['topic']}': {dash['stats']}")
        print(f"   Gespeichert: {DASHBOARD_DIR / (dash['slug'] + '.json')}")
        return

    if args.workflow:
        path = PENDING_DIR / args.workflow if not Path(args.workflow).exists() else Path(args.workflow)
        bookmark = json.loads(path.read_text(encoding="utf-8"))
        bookmark["_file"] = str(path)
        dash = aggregate_dashboard(bookmark)
        print(workflow_briefing(bookmark, dash))
        return

    if args.all_pending:
        items = list_pending()
        if not items:
            print("Keine pending Deep Dives.")
            return
        print(f"=== {len(items)} pending Deep Dives ===\n")
        for it in items:
            bookmark = {**it}
            bookmark["_file"] = str(PENDING_DIR / it["file"])
            dash = aggregate_dashboard(bookmark)
            print(workflow_briefing(bookmark, dash))
            print("\n" + "="*70 + "\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
