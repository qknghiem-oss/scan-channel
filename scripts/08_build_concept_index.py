"""
Phase 5: Buch-basierter Konzept-Index
Erweitert die Konzept-Daten um Buch-Sektionen, in denen das Konzept behandelt wird.
Überschreibt site/data/graph.json mit angereicherten Daten.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
KG_FILE = ROOT / "data" / "knowledge_graph.json"
BOOK_FILE = ROOT / "site" / "data" / "book.json"
OUT = ROOT / "site" / "data" / "graph.json"


def main():
    kg = json.loads(KG_FILE.read_text(encoding="utf-8"))
    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))

    concepts = kg.get("concepts", {})
    connections = kg.get("connections", [])

    # Build inverted index: concept-label → list of sections mentioning it
    concept_sections = defaultdict(list)
    for chapter in book["chapters"]:
        for section in chapter["sections"]:
            body_low = section["body_md"].lower()
            for label, c in concepts.items():
                # Wortgrenzen-Match (gleicher Stil wie in 03_analyze_rulebased)
                pattern = r"(?<![A-Za-z0-9])" + re.escape(label.lower()) + r"(?![A-Za-z0-9])"
                if re.search(pattern, body_low):
                    concept_sections[label].append({
                        "section_id": section["id"],
                        "section_title": section["title"],
                        "chapter_title": chapter["title"],
                    })

    # Enrich concepts
    for label, c in concepts.items():
        c["sections"] = concept_sections.get(label, [])
        c["section_count"] = len(c["sections"])

    out = {
        "concepts": concepts,
        "connections": connections,
        "meta": {
            "total_concepts": len(concepts),
            "concepts_with_sections": sum(1 for c in concepts.values() if c["section_count"] > 0),
            "total_connections": len(connections),
        },
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK Konzept-Index angereichert:")
    print(f"   Konzepte: {out['meta']['total_concepts']}")
    print(f"   Konzepte mit Buch-Sektionen: {out['meta']['concepts_with_sections']}")
    print()
    print("Top 10 Konzepte nach Buch-Anbindung:")
    top = sorted(concepts.values(), key=lambda c: -c["section_count"])[:10]
    for c in top:
        print(f"  {c['section_count']:>3} Sektionen | {c['video_count']:>2} Videos | {c['label']}")


if __name__ == "__main__":
    main()
