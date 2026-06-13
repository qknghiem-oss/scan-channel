---
name: scan-channel
description: |
  IMMER nutzen wenn ein User einen YouTube-Channel-Link teilt, "Wissensbuch",
  "Channel-Scan", "Deep Dive", "Per-Video-Analyse", "Channel sync" oder
  ähnliches erwähnt. Vollständige YouTube-zu-Wissensbuch-Pipeline:
  scannt Channel, lädt Transkripte + Thumbnails, synthetisiert Lehrbuch-
  Sektionen mit Zitaten + Timestamps, generiert Tiefenanalysen pro Thema
  UND pro Video, ElevenLabs-Audio in Abschnitten, interaktive Reader-UI
  mit Marginalia + Visualisierungen, manueller Sync-Button für neue Videos.

  TRIGGER (Skill MUSS feuern):
  - User teilt YouTube-Channel-URL (@handle, /channel/, /c/)
  - User sagt "Scanne Channel", "Mach Wissensbuch", "Channel sync"
  - User sagt "Deep Dive auf <Thema>" oder "Per-Video Deep Dive"
  - User klickt UI-Buttons (Sync, Tiefenanalyse, Bookmark)
  - User sagt "Mache die offenen Deep Dives" / "Per-Video-Deep-Dives"
  - User fragt "Was sind die neuen Videos?"
  - "/scan-channel build/sync/deep-dive/per-video <args>"

  SKIP:
  - User will nur EIN einzelnes Video zusammenfassen (kein Channel-Kontext)
  - User will reine Audio-Generation ohne Buch (eigener Skill)
---

# Skill: scan-channel — YouTube zu Wissensbuch + Deep Dives

## Was dieser Skill macht

Aus einem deutschsprachigen YouTube-Channel wird ein interaktives
Wissensbuch erstellt: ein lesbares Lehrwerk mit Kapiteln, echten Zitaten und
klickbaren Timestamp-Quellen, plus ein interaktiver Deep-Dive-Modus für
Tiefenanalysen einzelner Themen.

**Pilot-Implementierung:** `everlast_knowledge/` im Projekt
"01#scanen mit Claude" — vollständig getestet (35/35 Playwright OK).

## Zwei Phasen

### Phase 1: Channel → Buch (Setup + Synthese)

Eingabe: Channel-URL + optional Anzahl Tage (default 90).

```bash
# 1. Channel-Konfiguration anlegen
python scripts/00_init_channel.py --url <URL> --name "<Name>" --output <DIR>

# 2. Pipeline ausführen (Setup-Skripte)
python scripts/01_scan_channel.py        # ~5 Min: yt-dlp Metadaten
python scripts/02_extract_transcripts.py # ~15 Min: deutsche Transkripte
python scripts/03_analyze_rulebased.py   # <1 Min: Entitäten + Konzept-Graph
python scripts/04_build_site_data.py     # <1 Min: Lite-JSON
python scripts/05_extract_briefings.py   # <1 Min: Pro-Sektion-Briefings

# 3. Manuelle Phase: Topic-Clustering
# Claude im Chat liest videos_full.json und schreibt _book.json
# (Inhaltsverzeichnis: 10-15 Kapitel × 3-5 Sektionen = 35-50 Sektionen)
# Siehe: references/topic_clustering_pattern.md

# 4. Sektionen synthetisieren (via Agents)
# Pro Sektion: Agent erhält Briefing + Stil-Prototyp + Schreibregeln
# Siehe: references/prompts/section_synthesis.md

# 5. Buch zusammensetzen + Validierung
python scripts/06_assemble_book.py       # Cross-Ref + Index, 0 Issues = OK
python scripts/07_build_site_book.py     # book.json für Browser
python scripts/08_build_concept_index.py # Konzept-Index angereichert

# 6. Site starten
python scripts/serve.py                  # Threaded HTTP/1.1 auf :8765
```

### Phase 2: Deep Dive (UI-getrieben)

User klickt im UI auf ein Konzept im Konzept-Wiki → "Deep Dive starten"-Button.
Browser sendet POST an `/deep-dive/bookmark`. Datei landet in
`data/deep_dives/pending/`.

Claude im Chat führt aus:

```bash
# 1. Pending-Liste anschauen
python scripts/09_deep_dive.py --list

# 2. Für jeden Pending: Briefing + Workflow generieren
python scripts/09_deep_dive.py --all-pending
# Gibt Agent-Prompt(s) aus

# 3. Pro Bookmark: Agent + WebSearch starten
# Agent liest:
#   - data/knowledge_book/_index.json
#   - data/videos_full.json
#   - sections/*.md
#   - data/deep_dives/dashboard_data/<slug>.json
# Plus WebSearch + WebFetch für externen Kontext (max 3 Quellen)
# Schreibt: sections/dd-<slug>.md (2000-3000 Wörter)
# Schreibt: data/deep_dives/generated/<slug>.json (Metadaten)
# Verschiebt: pending/* → fertig (bzw. löscht pending-File)

# 4. Pipeline re-laufen lassen
python scripts/06_assemble_book.py
python scripts/07_build_site_book.py
python scripts/08_build_concept_index.py

# 5. (Optional) ElevenLabs MP3 für die neue Sektion vorberechnen
# Geschieht automatisch beim ersten UI-Klick auf "Vorlesen"
```

## Channel-Konfiguration (`channel.config.json`)

Pro Channel eine Konfiguration im Projekt-Root:

```json
{
  "channel_url": "https://www.youtube.com/@channelname/videos",
  "channel_name": "Channel Display Name",
  "handle": "@channelname",
  "language": "de",
  "days_back": 90,
  "category_keywords": {
    "kategorie_1": ["keyword1", "keyword2"],
    "kategorie_2": ["..."]
  },
  "known_entities": {
    "people": ["Vorname Nachname", "..."],
    "tools": ["Tool-Name", "..."],
    "companies": ["Firma", "..."],
    "concepts": ["Konzept", "..."]
  },
  "book_meta": {
    "title": "Buch-Titel 2026",
    "subtitle": "Eine Lesereise durch...",
    "style": "narrativ-erzaehlend"
  }
}
```

`scripts/00_init_channel.py` erstellt eine Default-Vorlage und prüft den
Channel via yt-dlp.

## Trigger-Beispiele

| Was User schreibt | Was passiert |
|--------------------|--------------|
| "Scanne den Channel https://youtube.com/@xyz" | Phase 1 startet |
| "Mach mir ein Buch aus @everlastai" | Phase 1 (Channel-URL ergänzen) |
| "Deep Dive auf Agentic Workflows" | Phase 2 für genau dieses Topic |
| "Mache die offenen Deep Dives" | Phase 2 für alle pending |
| "Welche Deep Dives sind offen?" | `09_deep_dive.py --list` ausgeben |
| "Extrahiere Praxis-Tipps" | Phase 3: `18_extract_praxis.py` |
| "Synthetisiere Per-Video Artikel" | Phase 4: `11_per_video_dive.py --synthesize-all` |
| "Welche Per-Video Analysen fehlen?" | `11_per_video_dive.py --list` |
| "/scan-channel build <URL>" | Direkter Phase-1-Start |
| "/scan-channel deep-dive" | Direkter Phase-2-Start (alle pending) |
| "/scan-channel praxis" | Phase-3-Start: Praxis-Extraktion |
| "/scan-channel per-video" | Phase-4-Start: Per-Video-Synthese |

## Verifikation (Wann ist die Arbeit fertig?)

### Phase 1
1. `data/videos_full.json` enthält ≥10 Videos mit deutschem Transkript
2. `data/knowledge_book/_book.json` enthält 10-15 Kapitel
3. `data/knowledge_book/sections/*.md` enthält 35-50 Sektionen
4. `python scripts/06_assemble_book.py` → 0 Issues
5. `python scripts/test_site.py` → 35+/35+ OK
6. Browser zeigt das Wissensbuch unter http://127.0.0.1:8765

### Phase 2
1. `data/deep_dives/pending/` ist leer (alle abgearbeitet)
2. Für jeden abgearbeiteten Bookmark gibt es:
   - `sections/dd-<slug>.md` mit ≥2000 Wörtern
   - `data/deep_dives/generated/<slug>.json`
3. Browser-Tab "Deep Dive" → "Fertige" zeigt Karte mit dem Eintrag
4. Klick auf Karte springt zur Sektion im Wissensbuch

## Referenzen

- `references/content_rules.md` — Wie Sektionen geschrieben werden
- `references/design_rules.md` — Farben, Typografie, Layout
- `references/technical_rules.md` — Pipeline-Details, TCP-Reset-Workaround, etc.
- `references/workflow_rules.md` — Schrittweise Arbeits-Templates
- `references/anti_repetition_rules.md` — **NEU**: Marginalia-System, Visualisierungen, Anti-Repetition
- `references/prompts/section_synthesis.md` — Agent-Prompt für Standard-Sektionen
- `references/prompts/deep_dive_synthesis.md` — Agent-Prompt für Deep Dives
- `references/topic_clustering_pattern.md` — Wie man 45 Videos zu 12 Kapiteln clustert

## Neu in v1.2 (11.06.2026, Session 4)

- **Sync-Button**: Manueller Refresh-Trigger im UI-Header
  - Endpunkt `POST /sync/trigger` startet `10_sync.py` im Hintergrund
  - Endpunkt `GET /sync/status?job_id=...` für Progress-Polling
  - Endpunkt `GET /sync/state` für letzten Sync-State
  - Frontend-Modal mit Progress-Bar, listet neue Videos
  - `data/sync_state.json` als Source-of-Truth für bekannte Videos
  - Skript `scripts/10_sync.py` mit `--dry-run` für Testlauf
- **Per-Video Deep Dive**: Tiefenanalyse pro einzelnem Video (nicht nur pro Thema)
  - Endpunkte `POST /per-video/bookmark` und `GET /per-video/list`
  - Skript `scripts/11_per_video_dive.py` als Aggregator + Briefing-Generator
  - "Tiefenanalyse anfordern"-Button im Video-Modal (Quellen-Bibliothek)
  - Neuer Sub-Tab "📹 Pro Video" im Deep-Dive-Tab
  - Preview-Bilder pro Video (hero + 3 previews) in `data/per_video_assets/`
- **Inkrementelles Update**: Sync verarbeitet nur neue Videos, nicht alle erneut
  - Bei jedem neuen Video: Pending-Bookmark für Per-Video Deep Dive automatisch
- **Rules erweitert**: `references/sync_and_video_deepdive_rules.md`
  - Anleitung für Sync-Workflow
  - Anleitung für Per-Video Deep Dive (Struktur + Anforderungen)
  - Image-Extraktion dokumentiert

## Neu in v1.1 (11.06.2026)

- **Audio-Segmentierung:** Pro H2-Abschnitt eigenes MP3 statt einer 10-Minuten-Spur
  - Endpunkt `/tts/segments?section=X.Y` listet Segmente
  - Endpunkt `/tts/audio?section=X.Y&seg=N` liefert MP3 nur eines Segments
  - Frontend zeigt Chips zum Springen, hebt H2 hervor während Vortrag
- **Marginalia-System:** Konzepte/Personen/Zahlen einmalig definieren
  - Syntax: `[^typ:slug]` Inline + Definition am Ende der Sektion
  - Typen: `person`, `tool`, `firma`, `zahl`, `begriff`, `quelle`
  - Frontend rendert als Karten in der rechten Seitenleiste
- **Inline-Visualisierungen:** `{{viz:type|params}}` in Markdown
  - Typen: `evolution`, `compare`, `timeline`, `quote-box`, `network`
  - Frontend rendert als D3/CSS-Diagramme im Fließtext
- **Anti-Wiederholungs-Rules** (`anti_repetition_rules.md`):
  - Jeder Begriff wird einmal definiert (Anker-Sektion), danach nur verlinkt
  - Zahlen in Marginalia, nicht im Fließtext wiederholt
  - Migration bestehender Sektionen sektionsweise bei Bedarf

## Phase 3: Praxis-Extraktion (Skript-gesteuert)

Extrahiert handlungsorientierte Tipps aus allen Videos und baut einen
durchsuchbaren Praxis-Index für den "Praxis"-Tab in der UI.

```bash
# Alle Videos ohne praxis_items verarbeiten
python scripts/18_extract_praxis.py

# Alle neu verarbeiten (überschreiben)
python scripts/18_extract_praxis.py --all

# Nur Index neu bauen (ohne LLM-Calls)
python scripts/18_extract_praxis.py --build

# Testlauf ohne Ollama
python scripts/18_extract_praxis.py --dry-run
```

Ausgabe: `data/praxis/praxis_index.json` — wird von der UI direkt geladen.

**Kategorien:** `tool`, `technik`, `workflow`, `framework`, `mindset`

## Phase 4: Per-Video Deep Dive Synthese

Generiert einen 1200-1800 Wörter Artikel pro einzelnem Video.

```bash
# Liste pending bookmarks
python scripts/11_per_video_dive.py --list

# Ein Video synthetisieren
python scripts/11_per_video_dive.py --synthesize <video_id>

# Alle pending synthetisieren
python scripts/11_per_video_dive.py --synthesize-all

# Trockenlauf
python scripts/11_per_video_dive.py --dry-run
```

Ausgabe pro Video:
- `data/per_video_deep_dives/generated/<video_id>.md` — Artikel
- `data/per_video_deep_dives/generated/<video_id>.json` — Metadaten

**Struktur des Artikels:** Intro + Kernthesen + Wichtigste Erkenntnisse +
Praktische Anwendung + Einordnung ins Gesamtbild

## LLM-Backend: LiteLLM / Ollama

`scripts/ollama_client.py` unterstützt sowohl lokales Ollama als auch ein
LiteLLM-Gateway auf dem VPS:

```python
# Konfiguration via Umgebungsvariablen:
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LITELLM_URL = os.getenv("LITELLM_URL", "")       # z.B. http://litellm:4000
LITELLM_KEY = os.getenv("LITELLM_API_KEY", "")

# Modelle (in LiteLLM-Projekten anpassen):
MODEL_FAST = "deepseek-v4-flash"   # für Extraktion + kurze Tasks
MODEL_PRO  = "deepseek-v4-pro"    # für Synthese + lange Artikel
```

**Wichtig für Deepseek-Modelle (chain-of-thought):** Das Modell gibt manchmal
`content: ""` zurück und schreibt die Antwort in `reasoning_content`.
`ollama_client.py` fällt automatisch auf `reasoning_content` zurück.

## Server-Endpunkte (vollständig)

| Endpunkt | Methode | Zweck |
|----------|---------|-------|
| `/` | GET | Redirect → index.html |
| `/site/<path>` | GET | Statische Site-Dateien |
| `/data/<path>` | GET | JSON-Dateien aus data/ |
| `/section/<id>` | GET | Markdown einer Sektion |
| `/tts/audio?section=X.Y&seg=N` | GET | ElevenLabs MP3-Segment |
| `/tts/segments?section=X.Y` | GET | Segment-Liste einer Sektion |
| `/sync/trigger` | POST | Startet 10_sync.py im Hintergrund |
| `/sync/status?job_id=...` | GET | Progress-Polling |
| `/sync/state` | GET | Letzter Sync-State |
| `/deep-dive/bookmark` | POST | Thema-Bookmark anlegen |
| `/deep-dive/list` | GET | Pending + Generated |
| `/deep-dive/dashboard?topic=X` | GET | Dashboard-Daten |
| `/per-video/bookmark` | POST | Video-Bookmark anlegen |
| `/per-video/list` | GET | Pending + Generated |
| `/per-video/content?id=<id>` | GET | Markdown eines generierten Artikels |
| `/search/usecase` | POST | Semantische Praxis-Suche via LLM |

## Bekannte Stolperfallen

1. **CSS-Spezifität:** `.view.active { display: block }` bricht `.book-view { display: grid }`.
   Nutze `.view.active.book-view { display: grid }`.

2. **TCP-Reset bei Promise.all:** Frontend-Code muss `fetch()` sequenziell
   machen, nicht parallel — sonst resettet der Python-Server.

3. **Playwright `wait_until="networkidle"`** triggert zu früh — Browser hat
   JS-Init noch nicht durch. Stattdessen `wait_until="load"` + Retry-Loop
   bis `document.querySelectorAll('.toc-section').length >= 39`.

4. **Sticky-Sidebar überlappt Section-Nav** beim automatisierten Klick.
   `page.evaluate("loadSection(...)")` statt direkter Locator-Clicks.

5. **ElevenLabs API-Key** muss in `.env` stehen (nicht hardcoded), die Datei
   gehört in `.gitignore`. Audio-Cache (`data/audio_cache/`) ebenfalls.

6. **Windows `SO_REUSEADDR` Port-Sharing:** Auf Windows können mehrere Prozesse
   denselben Port binden. Stale Python-Instanzen verteilen Requests, was zu
   9-Sekunden-Latenzen führt. `serve.py` killt beim Start automatisch alle
   Prozesse auf dem Port (`_kill_port()`). Bei manuellem Debugging:
   `netstat -ano | findstr :8765` → alle PIDs mit `taskkill /F /PID <pid>`.

7. **Deepseek chain-of-thought leeres `content`-Feld:** Wenn das LLM-Modell
   chain-of-thought nutzt, ist `choices[0].message.content` leer und die
   Antwort steckt in `reasoning_content`. `ollama_client.py` fällt
   automatisch zurück — aber nur wenn `LITELLM_URL` gesetzt ist.

8. **LLM gibt String-Indices zurück** (z.B. `"P0"`, `"S1"` statt `0`, `1`):
   Passiert bei `/search/usecase` wenn der Prompt Label-Strings enthält.
   `_norm_ids()` in `serve.py` bereinigt das automatisch.

## Cost-Estimate

| Was | Kosten |
|-----|--------|
| Vollständiges Buch (46k Wörter) erstmalig generieren | $0 (Claude-Chat-Agents) |
| ElevenLabs TTS für komplettes Buch (erstmalig) | ~$14 |
| Wiederholtes Hören aus MP3-Cache | $0 |
| Deep Dive pro Thema (Agent + WebSearch) | $0 (Claude-Chat) |
| Deep Dive Audio (ElevenLabs) | ~$0.50 pro Deep Dive |
| Per-Video Deep Dive (via LiteLLM/VPS) | ~$0 (self-hosted) |
| Praxis-Extraktion 60 Videos (via LiteLLM/VPS) | ~$0 (self-hosted) |

## Aktueller Stand (14.06.2026)

- Pilot: `@everlastai` — 60 Videos, 39 Sektionen + 30 Per-Video DDs, 46.620 Wörter, 156 Zitate
- Pipeline-Skripte: 12 Stück (00-11, 18)
- Reader-UI: 7 Tabs (Buch, Lesepfade, Konzepte, Deep Dive, Timeline, Bibliothek, Praxis)
- LLM-Backend: LiteLLM auf VPS (deepseek-v4-flash + deepseek-v4-pro)
- ElevenLabs: 5 Stimmen, MP3-Cache funktional
- Playwright: 35/35 OK
- Skill noch nicht channel-agnostisch refaktoriert — siehe Phase 1 Schritt 1

## Neu in v1.3 (14.06.2026, Sessions 7+8)

- **Per-Video Deep Dive Synthese**: `11_per_video_dive.py --synthesize` erzeugt
  1200-1800 Wörter Artikel pro Video via LLM (deepseek-v4-pro)
  - Transkript-Sampling: Start (2500) + Mitte (±500) + Ende (1500) für breite Abdeckung
  - 30 Artikel für @everlastai vollständig generiert
  - Neuer Endpunkt `/per-video/content?id=<id>` liefert Artikel als JSON
  - UI rendert Artikel mit `marked.js` inkl. YAML-Frontmatter-Stripping
  - Thumbnail-Bilder in generierten Karten via `img.youtube.com/vi/{id}/hqdefault.jpg`
- **Praxis-Extraktion**: `18_extract_praxis.py` — handlungsorientierte Tipps aus jedem Video
  - Kategorien: tool, technik, workflow, framework, mindset
  - Breites Transkript-Sampling (Start + Mitte + Ende statt nur Anfang)
  - Brace-counting JSON-Extraktion aus chain-of-thought Antworten
  - Neuer "Praxis"-Tab in der Reader-UI
- **Semantische Praxis-Suche** (`/search/usecase`): Use-Case-Beschreibung → passende Praxis-Items
  - LLM-gestützte Suche, max_tokens=2000 für chain-of-thought
  - `_norm_ids()` konvertiert String-Labels zu Integer-Indices
- **LiteLLM-Unterstützung**: `ollama_client.py` unterstützt jetzt LiteLLM-Gateway
  - Fallback auf `reasoning_content` wenn `content` leer (Deepseek chain-of-thought)
  - Konfiguration via `LITELLM_URL` + `LITELLM_API_KEY` Umgebungsvariablen
- **Stale-Server-Kill**: `serve.py` killt beim Start alle Prozesse auf dem Port
  - Verhindert 9-Sekunden-Latenzen durch Windows `SO_REUSEADDR` Port-Sharing
  - `_kill_port(port)` nutzt `netstat -ano` + `taskkill` (Windows) / `fuser` (Unix)
