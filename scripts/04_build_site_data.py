"""
Phase E (Helper): Generiert die Lite-JSON für die Website.
Aus knowledge_graph.json → site/data/videos.json + site/data/graph.json
"""

import json
import os
from pathlib import Path

INPUT = Path(__file__).parent.parent / "data" / "knowledge_graph.json"
OUT_VIDEOS = Path(__file__).parent.parent / "site" / "data" / "videos.json"
OUT_GRAPH = Path(__file__).parent.parent / "site" / "data" / "graph.json"


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))

    # === Videos: schlanke Version (ohne Volltranskript) ===
    lite_videos = []
    for v in data["videos"]:
        transcript_preview = v.get("transcript", "")[:1200]
        lite_videos.append({
            "id": v["id"],
            "title": v["title"],
            "published_date": v["published_date"],
            "duration_min": v["duration_min"],
            "view_count": v["view_count"],
            "like_count": v.get("like_count", 0),
            "category": v["category"],
            "importance_score": v["importance_score"],
            "source_url": v["source_url"],
            "description": (v.get("description", "") or "")[:600],
            "summary": v.get("summary", ""),
            "transcript_preview": transcript_preview,
            "transcript_length": len(v.get("transcript", "")),
            "chapters": v.get("chapters", [])[:15],
            "key_quotes": v.get("key_quotes", []),
            "key_numbers": v.get("key_numbers", [])[:5],
            "people": v.get("people", []),
            "tools": v.get("tools", []),
            "companies": v.get("companies", []),
            "concepts": v.get("concepts_found", []),
            "tags": v.get("tags", []),
            "topics_from_chapters": v.get("topics_from_chapters", []),
            "related_videos": v.get("related_videos", []),
        })

    out_videos = {
        "meta": data["meta"],
        "videos": lite_videos,
    }
    OUT_VIDEOS.write_text(json.dumps(out_videos, indent=2, ensure_ascii=False), encoding="utf-8")

    # === Graph ===
    out_graph = {
        "concepts": data.get("concepts", {}),
        "connections": data.get("connections", []),
    }
    OUT_GRAPH.write_text(json.dumps(out_graph, indent=2, ensure_ascii=False), encoding="utf-8")

    size_videos = os.path.getsize(OUT_VIDEOS) / 1024
    size_graph = os.path.getsize(OUT_GRAPH) / 1024

    print(f"OK Generated site data:")
    print(f"   site/data/videos.json: {size_videos:.1f} KB ({len(lite_videos)} videos)")
    print(f"   site/data/graph.json:  {size_graph:.1f} KB ({len(out_graph['concepts'])} concepts, {len(out_graph['connections'])} connections)")


if __name__ == "__main__":
    main()
