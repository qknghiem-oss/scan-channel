"""
Phase 3: Cross-Linking + Buch-Index
Liest alle Sektionen, parst Cross-References und Video-Links,
validiert Konsistenz und erzeugt einen Master-Index.

Output:
- data/knowledge_book/_index.json (Master-Index)
- Validierungs-Report im Terminal
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
SECTIONS_DIR = ROOT / "data" / "knowledge_book" / "sections"
INDEX_OUT = ROOT / "data" / "knowledge_book" / "_index.json"
VIDEOS_FILE = ROOT / "data" / "videos_full.json"

# Regex-Patterns
RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
RE_CROSSREF = re.compile(r"\[\[([0-9]+\.[0-9]+)\s+([^\]]+)\]\]")
RE_VIDEO_LINK = re.compile(r"\(video:([A-Za-z0-9_-]+)(?:\?t=(\d+))?\)")
RE_QUOTE = re.compile(r"^>\s+\"([^\"]+)\"", re.MULTILINE)


def parse_frontmatter(text: str) -> dict:
    m = RE_FRONTMATTER.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip().strip('"').strip("'")
            # Liste erkennen
            if v.startswith("[") and v.endswith("]"):
                items = [s.strip().strip('"').strip("'") for s in v[1:-1].split(",")]
                fm[k.strip()] = items
            else:
                fm[k.strip()] = v
    return fm


def count_words(text: str) -> int:
    body = RE_FRONTMATTER.sub("", text)
    body = re.sub(r"^---.*$", "", body, flags=re.MULTILINE)
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    return len(body.split())


def analyze_section(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    crossrefs = RE_CROSSREF.findall(text)
    video_links = RE_VIDEO_LINK.findall(text)
    quotes = RE_QUOTE.findall(text)

    word_count = count_words(text)

    return {
        "file": path.name,
        "frontmatter": fm,
        "word_count_actual": word_count,
        "word_target": int(fm.get("word_count", 0) or 0),
        "crossrefs": [{"section_id": s, "title": t.strip()} for s, t in crossrefs],
        "video_links": [{"video_id": vid, "timestamp": int(t) if t else 0} for vid, t in video_links],
        "quotes_count": len(quotes),
    }


def main():
    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
    videos_data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    valid_video_ids = {v["id"] for v in videos_data["videos"]}

    # Build expected section IDs from book
    expected_sections = {}
    for chapter in book["chapters"]:
        for section in chapter["sections"]:
            expected_sections[section["id"]] = {
                "chapter_id": chapter["id"],
                "chapter_number": chapter["number"],
                "chapter_title": chapter["title"],
                "section_id": section["id"],
                "title": section["title"],
                "tier": section["tier"],
                "word_target": section["word_target"],
                "source_videos": section["source_videos"],
            }

    # Analyze each section file
    section_data = {}
    issues = []

    for sid in sorted(expected_sections.keys(), key=lambda s: tuple(int(x) for x in s.split("."))):
        path = SECTIONS_DIR / f"{sid}.md"
        if not path.exists():
            issues.append(f"MISSING: {sid}.md")
            continue
        info = analyze_section(path)
        section_data[sid] = {**expected_sections[sid], **info}

        # Validate crossrefs
        for cr in info["crossrefs"]:
            if cr["section_id"] not in expected_sections:
                issues.append(f"{sid}: crossref to unknown section {cr['section_id']}")

        # Validate video links
        for vl in info["video_links"]:
            if vl["video_id"] not in valid_video_ids:
                issues.append(f"{sid}: video link to unknown video {vl['video_id']}")

        # Word count check
        target = info["word_target"]
        actual = info["word_count_actual"]
        if target and (actual < target * 0.7 or actual > target * 1.5):
            issues.append(f"{sid}: word count {actual} vs target {target} (out of range)")

    # Build inverted indexes
    sections_by_video = defaultdict(list)  # video_id -> [section_id]
    crossref_targets = defaultdict(list)   # section_id -> [referenced by]

    for sid, sdata in section_data.items():
        for vl in sdata.get("video_links", []):
            sections_by_video[vl["video_id"]].append(sid)
        for cr in sdata.get("crossrefs", []):
            crossref_targets[cr["section_id"]].append(sid)

    # Build the master index
    index = {
        "meta": {
            **book["meta"],
            "assembled_at": "2026-06-11",
            "sections_count": len(section_data),
        },
        "sections": section_data,
        "sections_by_video": dict(sections_by_video),
        "crossref_incoming": dict(crossref_targets),
        "videos": {v["id"]: {"title": v["title"], "url": v["source_url"], "duration_min": v["duration_min"], "view_count": v["view_count"], "published_date": v["published_date"]} for v in videos_data["videos"]},
        "issues": issues,
    }

    INDEX_OUT.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    # Stats
    print(f"Sektionen analysiert: {len(section_data)}/{len(expected_sections)}")
    print(f"Issues gefunden: {len(issues)}")
    print()

    total_words = sum(s["word_count_actual"] for s in section_data.values())
    total_quotes = sum(s["quotes_count"] for s in section_data.values())
    total_video_links = sum(len(s["video_links"]) for s in section_data.values())
    total_crossrefs = sum(len(s["crossrefs"]) for s in section_data.values())

    print(f"Gesamt-Wörter:        {total_words:>6,}")
    print(f"Gesamt-Zitate:         {total_quotes:>6}")
    print(f"Gesamt-Video-Links:    {total_video_links:>6}")
    print(f"Gesamt-Cross-Refs:     {total_crossrefs:>6}")
    print()

    # Per chapter summary
    print(f"{'Kap':>3} {'Title':<48} {'Sec':>3} {'Words':>6} {'Q':>3} {'VL':>3} {'XR':>3}")
    print("-" * 80)
    chapters_summary = defaultdict(lambda: {"count": 0, "words": 0, "quotes": 0, "vlinks": 0, "xrefs": 0})
    for sid, sdata in section_data.items():
        cnum = sdata["chapter_number"]
        ctitle = sdata["chapter_title"]
        s = chapters_summary[cnum]
        s["title"] = ctitle
        s["count"] += 1
        s["words"] += sdata["word_count_actual"]
        s["quotes"] += sdata["quotes_count"]
        s["vlinks"] += len(sdata["video_links"])
        s["xrefs"] += len(sdata["crossrefs"])
    for cnum in sorted(chapters_summary.keys()):
        s = chapters_summary[cnum]
        print(f"{cnum:>3} {s['title'][:48]:<48} {s['count']:>3} {s['words']:>6} {s['quotes']:>3} {s['vlinks']:>3} {s['xrefs']:>3}")

    if issues:
        print()
        print(f"Issues (erste 20):")
        for iss in issues[:20]:
            print(f"  ! {iss}")


if __name__ == "__main__":
    main()
