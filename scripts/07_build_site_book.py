"""
Phase 4-Helper: Packt das fertige Wissensbuch zu einer JSON-Datei für die Website.
Liest alle Sektionen aus data/knowledge_book/sections/*.md und kombiniert sie mit
dem Index zu site/data/book.json.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
BOOK_FILE = ROOT / "data" / "knowledge_book" / "_book.json"
INDEX_FILE = ROOT / "data" / "knowledge_book" / "_index.json"
SECTIONS_DIR = ROOT / "data" / "knowledge_book" / "sections"
VIDEOS_FILE = ROOT / "data" / "videos_full.json"
OUT = ROOT / "site" / "data" / "book.json"

RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    return RE_FRONTMATTER.sub("", text, count=1)


def main():
    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    videos = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))

    videos_by_id = {v["id"]: v for v in videos["videos"]}

    # Per Sektion: Body-Markdown + Metadaten + Quell-Videos
    chapters_out = []
    for chapter in book["chapters"]:
        sections_out = []
        for section in chapter["sections"]:
            sid = section["id"]
            md_path = SECTIONS_DIR / f"{sid}.md"
            if not md_path.exists():
                continue
            raw = md_path.read_text(encoding="utf-8")
            body = strip_frontmatter(raw).strip()

            # Hole Meta aus Index (cross-refs, video-links, word_count)
            idx = index["sections"].get(sid, {})

            # Source-Video-Details
            source_videos_full = []
            for vid in section["source_videos"]:
                v = videos_by_id.get(vid)
                if not v:
                    continue
                source_videos_full.append({
                    "id": v["id"],
                    "title": v["title"],
                    "duration_min": v["duration_min"],
                    "view_count": v["view_count"],
                    "published_date": v["published_date"],
                    "url": v["source_url"],
                })

            sections_out.append({
                "id": sid,
                "title": section["title"],
                "tier": section["tier"],
                "word_target": section["word_target"],
                "word_count": idx.get("word_count_actual", 0),
                "outline": section["outline"],
                "body_md": body,
                "source_videos": source_videos_full,
                "crossrefs": idx.get("crossrefs", []),
                "video_links": idx.get("video_links", []),
                "quotes_count": idx.get("quotes_count", 0),
            })

        chapters_out.append({
            "id": chapter["id"],
            "number": chapter["number"],
            "title": chapter["title"],
            "subtitle": chapter.get("subtitle", ""),
            "tier": chapter["tier"],
            "intro": chapter.get("intro", ""),
            "sections": sections_out,
        })

    # Reading paths bleiben aus _book.json
    out = {
        "meta": book["meta"],
        "reading_paths": book.get("reading_paths", []),
        "chapters": chapters_out,
        "stats": {
            "total_chapters": len(chapters_out),
            "total_sections": sum(len(c["sections"]) for c in chapters_out),
            "total_words": sum(s["word_count"] for c in chapters_out for s in c["sections"]),
            "total_quotes": sum(s["quotes_count"] for c in chapters_out for s in c["sections"]),
            "total_source_videos": 45,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    size_kb = OUT.stat().st_size / 1024
    print(f"OK Buch-JSON gespeichert: {OUT.name} ({size_kb:.1f} KB)")
    print(f"   Kapitel:   {out['stats']['total_chapters']}")
    print(f"   Sektionen: {out['stats']['total_sections']}")
    print(f"   Wörter:   {out['stats']['total_words']:,}")
    print(f"   Zitate:    {out['stats']['total_quotes']}")


if __name__ == "__main__":
    main()
