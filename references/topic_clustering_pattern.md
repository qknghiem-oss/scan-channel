# Topic-Clustering — Vom Video-Pool zum Buch-Inhaltsverzeichnis

Dieser Schritt ist Claude-im-Chat manuell. Es ist die kreative Phase, wo aus
einem Pool von 30-70 Videos ein zusammenhängendes Buch-Inhaltsverzeichnis wird.

## Eingabe

Nach `python scripts/02_extract_transcripts.py` liegt vor:
- `data/videos_full.json` mit allen Videos, Titeln, Beschreibungen, Kapiteln, Transkripten

## Workflow

### 1. Übersicht erstellen

```bash
python -c "
import json
d = json.load(open('data/videos_full.json', encoding='utf-8'))
for v in d['videos']:
    chap_titles = ' | '.join(c.get('title','') for c in v.get('chapters', [])[:12])
    desc_first = (v.get('description','') or '').split('\n')[0][:200]
    print(f'=== {v[\"id\"]} | {v[\"published_date\"]} | {v[\"duration_min\"]:.0f}min')
    print(f'TITLE: {v[\"title\"]}')
    print(f'INTRO: {desc_first}')
    print(f'CHAPS: {chap_titles}')
    print()
" > _overview.txt
```

→ Lies die Übersicht durch (oder lass Claude im Chat sie lesen).

### 2. Themen-Cluster bilden

Identifiziere 10-15 Hauptthemen, die sich durch die Video-Titel und
Kapitel-Beschreibungen ziehen.

**Faustregeln:**
- **Mega-Themen**: 5+ Videos behandeln das direkt → eigenes Kapitel
- **Mittel-Themen**: 3-5 Videos → eigenes Kapitel
- **Neben-Themen**: 1-2 Videos → in einem "Werkzeugkasten"-Kapitel sammeln

**Standard-Kapitel-Muster** (anpassen pro Channel):
1. "Die Landschaft <JAHR>" — Standortbestimmung
2. "Hauptwerkzeug der Domain" — z.B. Claude Code, Excel, Photoshop
3. "Modelle/Versionen/Evolution"
4. "Workflows + Praktiken"
5. "Wettkampf" (z.B. Anthropic vs. OpenAI)
6. "Wirtschaftliche Auswirkungen"
7. "Geopolitik / Markt"
8. "Wissenschaft + Frontier"
9. "Werkzeugkasten" (Tools + Sicherheit)
10. "Ausblick"

### 3. Pro Kapitel 3-5 Sektionen definieren

Jede Sektion ist eine eigenständige Lese-Einheit (700-1500 Wörter).
Sektion-Titel müssen aussagekräftig sein.

**Schlecht:**
- "Was sind Tools?"
- "Einleitung Robotik"

**Gut:**
- "Was Claude Code wirklich ist — Vom Copilot zum Orchestrator"
- "Humanoide Robotik 2026 — Stand der Dinge nach Optimus Gen 3"

### 4. Tier-Zuordnung

Pro Sektion: mega / mittel / neben

- **mega**: Kernsäulen, vom Channel sehr oft diskutiert (5+ Videos zugeordnet)
- **mittel**: Wichtige Sub-Themen (3-5 Videos)
- **neben**: Ergänzungen (1-3 Videos)

### 5. Quell-Videos pro Sektion

Jede Sektion bekommt eine Liste von 3-8 Video-IDs als Quellen. Diese sind die
Briefing-Basis für die Synthese.

### 6. Lesepfade definieren

3-6 kuratierte Lesepfade durch das Buch:
- "Schnell-Einstieg (30 Min)" — die 3-4 wichtigsten Sektionen
- "Mastery-Pfad" pro Mega-Thema — alle Sektionen dazu
- "Business-Sicht" — was Unternehmer wissen müssen
- "Vollständig" — alle Sektionen in Reihenfolge

### 7. _book.json schreiben

Format:

```json
{
  "meta": {
    "title": "...",
    "subtitle": "...",
    "channel": "...",
    "handle": "@...",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "source_videos": <ANZAHL>,
    "total_chapters": <ANZAHL>,
    "total_sections": <ANZAHL>,
    "estimated_read_minutes": <SUMME>,
    "style": "narrativ-erzaehlend",
    "language": "de"
  },
  "reading_paths": [
    {
      "id": "schnell-einstieg",
      "title": "Schnell-Einstieg (30 Min)",
      "description": "...",
      "sections": ["1.1", "2.1", "X.Y"]
    },
    ...
  ],
  "chapters": [
    {
      "id": "ch01",
      "number": 1,
      "title": "...",
      "subtitle": "...",
      "tier": "mega|mittel|neben",
      "intro": "...",
      "sections": [
        {
          "id": "1.1",
          "number": "1.1",
          "title": "...",
          "tier": "mega|mittel|neben",
          "word_target": 1100,
          "outline": ["Bullet 1", "Bullet 2", ...],
          "source_videos": ["VIDEO_ID_1", ...]
        }
      ]
    }
  ],
  "video_coverage": {
    "covered_video_ids": [<alle Video-IDs aus videos_full.json>],
    "total_covered": <SOLL = videos.length>,
    "total_in_dataset": <ist>
  }
}
```

### 8. Validierung

Nach dem Schreiben:
```bash
python scripts/05_extract_briefings.py
```

→ erzeugt pro Sektion ein Briefing-File. Wenn ein Briefing leer ist
(`0 Quellen | 0 Chunks`), war die Sektion falsch zugeordnet.

### 9. Synthese

Pro Sektion einen Agent spawnen mit dem Prompt aus
`references/prompts/section_synthesis.md`.

Batch-Größe: ~6 Agents parallel.

## Beispiel: Erfolgreiche Cluster-Entscheidungen

Aus dem Everlast-Pilot:
- **45 Videos** wurden zu **12 Kapiteln × 3-5 Sektionen = 39 Sektionen**
- Mega-Kapitel: Claude Code (5 Sektionen), Agenten-Revolution (4), Post-Labor (4)
- Mittel: Wettkampf (3), Robotik (3), Geopolitik (3), Bewusstsein (3), Business (3)
- Neben: Hardware-Frontier (2), Werkzeugkasten (3)
- Lesepfade: 5 (Schnell-Einstieg, Claude Mastery, Agents Mastery, Business, Vollständig)
