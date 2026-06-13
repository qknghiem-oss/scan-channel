# 03 — Technical-Rules: Architektur, Pipeline, Server, Tests

## Pipeline-Reihenfolge (Heilige Skript-Kette)

```
01_scan_channel.py          → data/videos_list.json     (yt-dlp Metadaten)
02_extract_transcripts.py   → data/videos_full.json     (+Transkripte + Thumbnails)
03_analyze_rulebased.py     → data/knowledge_graph.json (Entitaeten + Konzept-Graph)
04_build_site_data.py       → site/data/videos.json + graph.json
05_extract_briefings.py     → data/knowledge_book/_briefings/*.json
   (Manuelle Phase: Topic-Clustering → _book.json
    + 39 Sektionen via Agents → sections/*.md)
06_assemble_book.py         → data/knowledge_book/_index.json (Cross-Ref + Validierung)
07_build_site_book.py       → site/data/book.json (komplettes Buch für Browser)
08_build_concept_index.py   → site/data/graph.json (Buch-anchored Konzepte)
```

**Regel:** Die Skripte sind nummeriert nach Ausführungs-Reihenfolge.
Wenn man eine frühere Stufe ändert, müssen alle nachfolgenden re-laufen.

## Daten-Flow

```
videos_full.json   (11 MB, ~3M Zeichen Transkript)
        ↓ Schritt 03
knowledge_graph.json   (Entitaeten + Konzepte)
        ↓ Schritt 04+07+08
site/data/
    book.json     (470 KB, für Reader)
    videos.json   (320 KB, für Bibliothek-Tab)
    graph.json    (190 KB, für Konzept-Tab)
```

## Server: Threaded HTTP/1.1

`scripts/serve.py` — Pflicht-Server für Entwicklung und Tests.

```python
class ThreadedHTTP(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

class Handler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # Pflicht — sonst Reset bei parallelen Requests
    # Cache-Control: no-cache für Dev
```

**Wichtig:**
- `protocol_version = "HTTP/1.1"` — sonst TCP-Resets bei mehreren Requests
- `os.chdir(SITE_DIR)` statt `directory=` Parameter (Stabilitaets-Problem mit Unicode-Pfaden)
- Bindet auf `127.0.0.1` (nicht `0.0.0.0`) — Chromium Headless bevorzugt das
- Port: **8765** (Konstante)

## Frontend-Daten-Loading

**Sequenziell, nicht parallel** — verhindert TCP-Resets:

```js
(async function loadData() {
  const bookRes = await fetch("data/book.json");
  STATE.book = await bookRes.json();
  const vRes = await fetch("data/videos.json");
  STATE.videos = (await vRes.json()).videos;
  // ... graph dann
  init();
})();
```

## CSS-Spezifitaet-Trap

`.view.active { display: block }` hat Spezifitaet (0,2,0).
`.book-view { display: grid }` hat Spezifitaet (0,1,0).

→ `.view.active` gewinnt, kollabiert das Grid.

**Lösung:** Höhere Spezifitaet:
```css
.book-view { display: none; }
.view.active.book-view { display: grid; }   /* Spezifitaet 0,3,0 — gewinnt */
```

## Verzeichnis-Konventionen

```
everlast_knowledge/
├── scripts/        ← Python (Pipeline + Tests + Server)
├── data/           ← Rohdaten + Wissensbuch (NICHT im git)
│   └── knowledge_book/
│       ├── _book.json        ← Inhaltsverzeichnis
│       ├── _index.json       ← Validierter Cross-Ref-Index
│       ├── _briefings/*.json ← Pro-Sektion Briefings
│       └── sections/*.md     ← Die 39 Lehr-Artikel
├── site/           ← Statische Website
│   ├── index.html
│   ├── assets/{style.css, app.js}
│   └── data/       ← Generierte JSONs für den Browser
└── test_screenshots/ ← Playwright-Beweise
```

## Playwright-Tests

`scripts/test_site.py` — 35 Asserts in 15 Test-Stufen.

### Bekannte Faellen:
1. **`wait_until="networkidle"`** triggert zu früh — JS-Init noch nicht durch.
   → Stattdessen: `wait_until="load"` + `wait_for(toc-section count >= 39)`
   
2. **Retry-Logic nötig** beim ersten Seitenladen — Browser braucht oft 2 Versuche
   bis die sequentiellen Fetches durchlaufen.

3. **Sticky-Sidebar überlappt Section-Nav** beim Klick.
   → Stattdessen Section-Nav-Klicks per `page.evaluate("loadSection(...)")` triggern.

4. **Modal-Close mit iframe:** Das iframe faengt Pointer-Events ab.
   → `page.click("button.modal-close")` nicht `[data-close]`.

### Erfolgskriterium:
**35/35 Tests bestanden.** Bei Änderungen am UI immer voll durchlaufen lassen.

## Anti-Pattern (verboten)

### CSS
- `!important` — fast immer Spezifitaets-Schmerz vermeiden, nicht erzwingen
- Inline-Styles — Ausnahme: dynamische `style.setProperty("--cat", color)` für Kategorie-Farbe
- Fixed-Pixel ohne Bezug zum Spacing-System

### JS
- `Promise.all` mit lokalem Server (TCP-Reset, siehe oben)
- Modul-globale Side-Effects außerhalb des `loadData()`-IIFE
- DOM-Manipulation in mehreren Funktionen gleichzeitig (Reihenfolge: erst Daten, dann Render)

### Daten
- Mehrfach-Pipelines (gleicher Output von zwei Skripten geschrieben)
- Überschreiben von User-Daten (localStorage-Notizen)
- Halluzinierte Quellen oder Zitate (siehe `01_CONTENT_RULES.md`)

## ElevenLabs TTS-Integration

**Aktiv seit Juni 2026.** Production-TTS via ElevenLabs Flash v2.5.

### Konfiguration (.env)
```env
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_MODEL=eleven_flash_v2_5
ELEVENLABS_DEFAULT_VOICE=pNInz6obpgDQGcFmaJgB
```

### Server-Endpunkte
- `GET /tts/voices` → JSON mit verfügbaren Stimmen + default + model
- `GET /tts/audio?section=X.Y&voice=VOICE_ID` → MP3-Stream

### MP3-Cache
- Pfad: `data/audio_cache/SECTION__VOICE__HASH.mp3`
- Erste Generation: ~17s pro Sektion (Flash v2.5)
- Cache-Hit: <50ms
- Hash basiert auf section_id + voice_id + model — bei Modell-Wechsel automatisch neu generiert

### Voices (5 vorausgewählt)
- `pNInz6obpgDQGcFmaJgB` — Adam (m, neutral) — Default
- `JBFqnCBsd6RMkjVDRZzb` — George (m, ruhig)
- `XB0fDUnXU5powFXDhCwa` — Charlotte (w, warm)
- `onwK4e9ZLuTAKqWW03F9` — Daniel (m, sachlich)
- `EXAVITQu4vr4xnSDxMaL` — Sarah (w, klar)

### Cost-Estimat
- Flash v2.5: ~$0.05 / 1000 Zeichen
- Komplettes Buch (46k Wörter ≈ 280k Zeichen): **~$14 Vollkosten beim ersten Cache-Aufbau**
- Wiederholtes Hoeren: kostenlos

## Anthropic API

**Aktuell nicht verwendet.** Alle Synthese laeuft via Claude im Chat über
Explore-/General-Agents.

Wenn API-Key spaeter gesetzt: Pipeline-Stufe 03 koennte durch echte LLM-Analyse
ersetzt werden (statt regelbasierter). Aber: gegenwaertige Qualitaet rechtfertigt
das nicht — Pflicht ist nur das Schreiben der Sektionen, und das macht Claude
im Chat erfolgreich.

## Performance-Targets

| Metrik | Soll |
|--------|------|
| Initial Page Load | < 3s |
| Sektions-Wechsel | < 200ms |
| Knowledge-Graph-Render | < 1s |
| book.json | < 500 KB |
| videos.json | < 350 KB |

## Backup & Versionierung

- `data/knowledge_book/sections/*.md` ist die **Quelle der Wahrheit** des Buchs
- Alle anderen Dateien koennen aus diesem regeneriert werden
- Empfehlung: `sections/` und `_book.json` git-versionieren, Rest gitignoren
