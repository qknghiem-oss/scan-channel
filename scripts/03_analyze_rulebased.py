"""
Phase C (Rule-Based): Analyse ohne LLM
Extrahiert Entitäten, Themen, Zitate, Verbindungen aus Transkripten + Beschreibungen + Kapiteln.

Output: data/knowledge_graph.json
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path(__file__).parent.parent / "data" / "videos_full.json"
OUTPUT = Path(__file__).parent.parent / "data" / "knowledge_graph.json"

# === Bekannte Entitäten — aus channel.config.json oder Everlast-Fallback ===
_CONFIG_FILE = Path(__file__).parent.parent / "channel.config.json"
_CONFIG = {}
if _CONFIG_FILE.exists():
    try:
        _CONFIG = json.load(open(_CONFIG_FILE, encoding="utf-8"))
    except Exception:
        pass

_ENTITIES = _CONFIG.get("known_entities", {})

KNOWN_PEOPLE = _ENTITIES.get("people") or [
    "Leonard Schmedding", "Dario Amodei", "Sam Altman", "Elon Musk",
    "Joscha Bach", "Daniel Cremers", "Sven Gabor Janszky", "Frank Sieren",
    "Lars Hinrichs", "Niels Birbaumer", "Adrian Locher", "Alois Knoll",
    "Achim Lilienthal", "Oliver Bendel", "Pero Micic", "Thomas Zurbuchen",
    "Jörg Wuttke", "Alexander König", "Robert Vogel", "Jenny Seidenschwarz",
    "Anne Greul", "Stefan Faistenauer", "Felix Urban", "Maximilian Rolf",
    "Jürgen Kocka", "Andreas Moring", "Lutz Keppeler", "Magnus Müller",
    "Mark Müller", "Oliver Trabert", "Dr. Johann Rehberger",
]

KNOWN_TOOLS = _ENTITIES.get("tools") or [
    "Claude Code", "Claude Opus", "Claude Sonnet", "Claude Haiku",
    "ChatGPT", "GPT-5.5", "GPT-5", "Codex", "Cursor", "Copilot",
    "Gemini", "Gemma", "Llama", "Mistral",
    "n8n", "Zapier", "Make", "Notion", "Obsidian",
    "Subagents", "Managed Agents", "Skills", "MCP",
    "Stitch", "AutoDream", "Browser Use", "Voicely", "Wispr Flow",
    "Dynamic Workflows", "UltraCode", "Agent View", "Fast Mode",
    "ImageGen", "Sora", "Veo", "Kling", "Suno", "HeyGen",
    "Mythos", "Spud", "Kairos", "Goal",
]

KNOWN_COMPANIES = _ENTITIES.get("companies") or [
    "Anthropic", "OpenAI", "Google", "Microsoft", "Meta", "Apple",
    "Tesla", "xAI", "Nvidia", "Huawei", "Alibaba",
    "Everlast AI", "Mistral", "DeepMind",
    "Octonomy AI", "Invitris AI", "Mirelo AI", "goodBytz", "Neura Robotics",
    "Terafab", "Browser Use", "Odyssey",
]

KNOWN_CONCEPTS = _ENTITIES.get("concepts") or [
    "Knowledge Graph", "RAG", "Embedding", "Fine-Tuning", "Prompt",
    "Agent", "Agentic Workflows", "Subagents", "Managed Agents", "Hive Mind",
    "Vibe Coding", "Agentic Coding",
    "Post-Labor Economy", "Singularität", "AGI", "Superintelligenz",
    "Weltmodell", "Multi-Agent", "Reasoning",
    "Deindustrialisierung", "Humanoide", "Roboter",
    "Memory-Hack", "Neuromorphic Computing", "BCI", "Quantencomputing",
]


# === Extraktions-Funktionen ===

def extract_entities(text: str, dictionary: list[str]) -> list[str]:
    """Findet bekannte Entitäten im Text mit Wortgrenzen (case-insensitive)."""
    found = []
    for entity in dictionary:
        # Pattern mit Wortgrenzen — exakte Treffer, keine Teilstrings
        pattern = r"(?<![A-Za-zÄÖÜäöüß0-9])" + re.escape(entity) + r"(?![A-Za-zÄÖÜäöüß0-9])"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(entity)
    return sorted(set(found))


def extract_quotes(transcript: str, max_quotes: int = 5) -> list[str]:
    """Findet zitatwürdige Sätze: kurz, prägnant, mit Schlüsselwörtern."""
    if not transcript:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    candidates = []

    quote_keywords = [
        "krass", "wahnsinn", "unglaublich", "absolute", "wirklich",
        "das ist", "das wird", "es gibt", "wir haben", "ich glaube",
        "die wahrheit", "in zukunft", "wirklich", "wichtig", "kommt jetzt",
        "ändert alles", "das ende", "der durchbruch",
    ]

    for s in sentences:
        s = s.strip()
        word_count = len(s.split())
        if word_count < 6 or word_count > 30:
            continue
        s_low = s.lower()
        if not any(k in s_low for k in quote_keywords):
            continue
        # Score nach Kürze + Keyword-Dichte
        kw_hits = sum(1 for k in quote_keywords if k in s_low)
        score = kw_hits * 2 - abs(word_count - 14) * 0.1
        candidates.append((score, s))

    candidates.sort(reverse=True, key=lambda x: x[0])
    seen = set()
    result = []
    for _, s in candidates:
        # Dedup basierend auf ersten 30 Zeichen
        key = s[:30].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(s)
        if len(result) >= max_quotes:
            break
    return result


def extract_key_numbers(text: str) -> list[dict]:
    """Findet Zahlen mit Kontext."""
    pattern = re.compile(
        r'([\d,.]+\s*(?:%|Prozent|Millionen|Milliarden|Mrd\.|Mio\.|x|fach|Punkte|Punkten|Tokens|US?D?|\$|€|Euro|Dollar))',
        re.IGNORECASE
    )
    sentences = re.split(r'(?<=[.!?])\s+', text)
    found = []
    for s in sentences:
        m = pattern.search(s)
        if m:
            ctx = s.strip()[:140]
            if 10 < len(ctx) < 140:
                found.append({"value": m.group(1).strip(), "context": ctx})
        if len(found) >= 8:
            break
    return found


def make_summary(description: str, chapters: list) -> str:
    """Generiere Kurz-Zusammenfassung aus Beschreibung."""
    if description:
        # Erste 2-3 Sätze
        sentences = re.split(r'(?<=[.!?])\s+', description.strip())
        # Stoppe bei "Link" / "Sichere dir" — diese leiten zu Werbung
        clean = []
        for s in sentences:
            if any(stop in s.lower() for stop in ["sichere dir", "kostenfrei", "https://", "https:", "newsletter", "▶", "+++", "kibubble"]):
                break
            clean.append(s)
            if len(" ".join(clean)) > 280:
                break
        if clean:
            return " ".join(clean).strip()
    if chapters:
        return "Themen: " + ", ".join(c.get("title", "") for c in chapters[:5])
    return ""


def extract_topics_from_chapters(chapters: list) -> list[str]:
    """Kapitel-Titel als Topics."""
    return [c.get("title", "").strip() for c in chapters if c.get("title")]


def calc_score(video: dict) -> int:
    """Importance-Score 1-10 basierend auf Engagement + Dauer + Kapitel."""
    score = 4.0
    views = video.get("view_count", 0)
    likes = video.get("like_count", 0)

    if views > 100000: score += 2.5
    elif views > 50000: score += 1.8
    elif views > 20000: score += 1.0
    elif views > 5000: score += 0.4

    if likes > 1000: score += 0.8
    if video.get("duration_min", 0) > 25: score += 0.6
    if len(video.get("chapters", [])) > 8: score += 0.5
    if len(video.get("transcript", "")) > 50000: score += 0.5

    return max(1, min(10, round(score)))


def build_concept_graph(videos: list) -> dict:
    """Konzepte aggregieren und Verbindungen herstellen."""
    concept_videos = defaultdict(list)
    concept_meta = {}

    for v in videos:
        entities = (
            v.get("people", []) +
            v.get("tools", []) +
            v.get("companies", []) +
            v.get("concepts_found", [])
        )
        for ent in entities:
            concept_videos[ent].append(v["id"])

    concepts = {}
    for label, video_ids in concept_videos.items():
        if len(video_ids) < 2:
            continue  # Nur Konzepte die in mindestens 2 Videos vorkommen
        # Kategorie bestimmen
        if label in KNOWN_PEOPLE:
            cat, color = "person", "#10b981"
        elif label in KNOWN_TOOLS:
            cat, color = "tool", "#8b5cf6"
        elif label in KNOWN_COMPANIES:
            cat, color = "company", "#f59e0b"
        else:
            cat, color = "concept", "#3b82f6"
        concepts[label] = {
            "label": label,
            "category": cat,
            "color": color,
            "video_count": len(video_ids),
            "videos": video_ids,
        }

    # Connections: Wenn 2 Konzepte zusammen in min. 2 Videos auftauchen
    cooc = defaultdict(int)
    for v in videos:
        all_ents = list(set(
            v.get("people", []) +
            v.get("tools", []) +
            v.get("companies", []) +
            v.get("concepts_found", [])
        ))
        for i, a in enumerate(all_ents):
            for b in all_ents[i+1:]:
                if a in concepts and b in concepts:
                    pair = tuple(sorted([a, b]))
                    cooc[pair] += 1

    connections = []
    for (a, b), n in cooc.items():
        if n >= 2:
            connections.append({"from": a, "to": b, "strength": n})

    return {"concepts": concepts, "connections": connections}


def build_video_links(videos: list) -> dict:
    """Video-zu-Video-Links basierend auf gemeinsamen Entitäten."""
    links = defaultdict(list)
    for i, v1 in enumerate(videos):
        ents1 = set(v1.get("people", []) + v1.get("tools", []) + v1.get("companies", []))
        scores = []
        for j, v2 in enumerate(videos):
            if i == j:
                continue
            ents2 = set(v2.get("people", []) + v2.get("tools", []) + v2.get("companies", []))
            overlap = len(ents1 & ents2)
            if overlap >= 2:
                scores.append((overlap, v2["id"]))
        scores.sort(reverse=True)
        links[v1["id"]] = [vid for _, vid in scores[:4]]
    return dict(links)


# === Main ===

def main():
    print("Phase C (rule-based): Wissens-Analyse")
    print("-" * 60)

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    videos = data["videos"]
    n = len(videos)

    enriched = []
    for i, v in enumerate(videos, 1):
        transcript = v.get("transcript", "")
        description = v.get("description", "")
        chapters = v.get("chapters", [])
        full_text = transcript + " " + description

        v["people"] = extract_entities(full_text, KNOWN_PEOPLE)
        v["tools"] = extract_entities(full_text, KNOWN_TOOLS)
        v["companies"] = extract_entities(full_text, KNOWN_COMPANIES)
        v["concepts_found"] = extract_entities(full_text, KNOWN_CONCEPTS)
        v["key_quotes"] = extract_quotes(transcript, max_quotes=3)
        v["key_numbers"] = extract_key_numbers(transcript)
        v["summary"] = make_summary(description, chapters)
        v["topics_from_chapters"] = extract_topics_from_chapters(chapters)
        v["importance_score"] = calc_score(v)

        # Tags (max 5): Mix aus tools, top concepts, Kategorie
        tag_candidates = v["tools"][:3] + v["concepts_found"][:2] + v["people"][:1]
        v["tags"] = list(dict.fromkeys(tag_candidates))[:5]

        enriched.append(v)
        print(f"  [{i:>2}/{n}] {v['id']} | P:{len(v['people'])} T:{len(v['tools'])} "
              f"C:{len(v['companies'])} Q:{len(v['key_quotes'])} | score={v['importance_score']}")

    # Build graph
    print()
    print("Baue Konzept-Graph...")
    graph = build_concept_graph(enriched)
    print(f"  {len(graph['concepts'])} Konzepte, {len(graph['connections'])} Verbindungen")

    print("Baue Video-Verlinkungen...")
    links = build_video_links(enriched)
    for v in enriched:
        v["related_videos"] = links.get(v["id"], [])

    output = {
        "meta": {**data["meta"], "analyzed_at_phase": "C-rulebased"},
        "videos": enriched,
        "concepts": graph["concepts"],
        "connections": graph["connections"],
    }
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(f"OK Knowledge Graph gespeichert: {OUTPUT}")
    print(f"   - {len(enriched)} Videos angereichert")
    print(f"   - {len(graph['concepts'])} Konzepte erkannt")
    print(f"   - {len(graph['connections'])} Verbindungen")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
