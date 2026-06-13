"""
Phase 2-Vorbereitung: Briefing-Extraktor
Erzeugt pro Sektion ein Briefing-JSON mit den relevantesten Transkript-Chunks
aus den Quell-Videos, ausgewählt nach Kapitel-Titeln und Outline-Keywords.

Das Briefing wird vom Synthesis-Agent gelesen und zu einem fertigen Markdown-Artikel verarbeitet.

Output: data/knowledge_book/_briefings/SECTION_ID.json
"""

import json
import re
import sys
from pathlib import Path

# UTF-8 Stdout für Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
VIDEOS_FILE = ROOT / "data" / "videos_full.json"
BOOK_FILE = ROOT / "data" / "knowledge_book" / "_book.json"
BRIEFINGS_DIR = ROOT / "data" / "knowledge_book" / "_briefings"

# === Hilfsfunktionen ===

def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", text.lower())

def keywords_from_outline(outline: list[str]) -> list[str]:
    """Extrahiere bedeutsame Keywords aus Outline-Bullet-Points."""
    stopwords = {
        "ist", "sind", "der", "die", "das", "den", "dem", "ein", "eine", "einen",
        "und", "oder", "aber", "auch", "doch", "wie", "wo", "was", "wer", "wann",
        "über", "von", "in", "mit", "auf", "für", "zu", "bei", "nach", "vor",
        "ein", "es", "im", "am", "zur", "zum", "des", "dem",
        "der", "neue", "neuen", "neues", "neuer",
        "praktisch", "wirklich", "konkret", "konkrete", "konkreten",
    }
    keywords = set()
    for bullet in outline:
        for word in normalize(bullet).split():
            if len(word) >= 3 and word not in stopwords:
                keywords.add(word)
    return sorted(keywords)


def chunk_transcript_by_chapter(video: dict) -> list[dict]:
    """Schneide das Transkript in Chunks pro Kapitel."""
    chapters = video.get("chapters", [])
    timestamps = video.get("transcript_timestamps", [])

    if not chapters:
        # Wenn keine Kapitel: ganzer Transkript als ein Chunk
        full = video.get("transcript", "")
        return [{"chapter_title": "(Ohne Kapitel)", "start": 0.0, "end": 0.0, "text": full[:4000]}]

    chunks = []
    for ch in chapters:
        start = float(ch.get("start_time", 0))
        end = float(ch.get("end_time", start + 60))
        title = ch.get("title", "")
        # Sammle Timestamps innerhalb dieses Kapitels
        chunk_text = " ".join(
            t["text"] for t in timestamps
            if start <= t.get("time", 0) < end
        ).strip()
        if not chunk_text:
            continue
        chunks.append({
            "chapter_title": title,
            "start": round(start),
            "end": round(end),
            "text": chunk_text,
        })
    return chunks


def score_chunk(chunk: dict, keywords: list[str]) -> int:
    """Score: Wieviele Keywords kommen im Chunk vor?"""
    text_low = normalize(chunk["chapter_title"] + " " + chunk["text"])
    return sum(1 for kw in keywords if kw in text_low)


def pick_top_chunks_for_video(video: dict, keywords: list[str], max_chunks: int = 4) -> list[dict]:
    """Wähle die relevantesten Kapitel-Chunks aus einem Video."""
    chunks = chunk_transcript_by_chapter(video)
    if not chunks:
        return []
    scored = [(score_chunk(c, keywords), c) for c in chunks]
    scored.sort(reverse=True, key=lambda x: x[0])
    # Mindestens score >= 1, sonst die ersten 2 Chunks
    top = [c for s, c in scored if s >= 1][:max_chunks]
    if not top:
        top = [c for _, c in scored[:2]]
    return top


def truncate_chunk(chunk: dict, max_chars: int = 3500) -> dict:
    """Schneide zu lange Chunks zurück — behalte Anfang."""
    text = chunk["text"]
    if len(text) <= max_chars:
        return chunk
    return {**chunk, "text": text[:max_chars] + " […]"}


# === Main ===

def main():
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    book = json.loads(BOOK_FILE.read_text(encoding="utf-8"))
    videos_data = json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    videos_by_id = {v["id"]: v for v in videos_data["videos"]}

    total_sections = 0
    total_chars = 0

    for chapter in book["chapters"]:
        for section in chapter["sections"]:
            section_id = section["id"]
            keywords = keywords_from_outline(section["outline"])

            briefing = {
                "section_id": section_id,
                "section_title": section["title"],
                "chapter_title": chapter["title"],
                "chapter_intro": chapter.get("intro", ""),
                "tier": section["tier"],
                "word_target": section["word_target"],
                "outline": section["outline"],
                "extracted_keywords": keywords,
                "sources": [],
            }

            for vid in section["source_videos"]:
                if vid not in videos_by_id:
                    continue
                video = videos_by_id[vid]
                top_chunks = pick_top_chunks_for_video(video, keywords, max_chunks=4)
                truncated = [truncate_chunk(c) for c in top_chunks]

                briefing["sources"].append({
                    "video_id": vid,
                    "title": video["title"],
                    "published_date": video["published_date"],
                    "duration_min": video["duration_min"],
                    "view_count": video["view_count"],
                    "source_url": video["source_url"],
                    "thumbnail_url": video.get("thumbnail_url", ""),
                    "chunks": truncated,
                })

            # Output
            out_path = BRIEFINGS_DIR / f"{section_id}.json"
            out_path.write_text(
                json.dumps(briefing, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            size_kb = out_path.stat().st_size / 1024
            chunks_count = sum(len(s["chunks"]) for s in briefing["sources"])
            total_sections += 1
            total_chars += sum(len(c["text"]) for s in briefing["sources"] for c in s["chunks"])
            print(f"  {section_id:>5} | {len(briefing['sources'])} Quellen | {chunks_count} Chunks | {size_kb:5.1f} KB | {section['title'][:50]}")

    print()
    print(f"OK {total_sections} Briefings erstellt in {BRIEFINGS_DIR.relative_to(ROOT)}")
    print(f"   Gesamt-Volumen: {total_chars:,} Zeichen Transkript-Excerpts")


if __name__ == "__main__":
    main()
