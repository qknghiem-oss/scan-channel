# Skill scan-channel — Feature-Backlog

> Was noch in den Skill rein muss, bevor er als Multi-Channel-Tool produktiv ist.
> Diese Datei wird bei jeder Session aktualisiert wenn neue Anforderungen kommen.

---

## ⟳ Update — voller Channel-Refresh (Session 6, eingebaut im Reader)

### Was es heute kann (lokales Projekt)
Im Reader-Header gibt es einen **Update-Button** (Symbol ⟳). Klick → `/update/trigger`
→ Backend startet `scripts/15_full_update.py`, das **9 Phasen** sequenziell durchläuft:

| # | Phase ID | Skript | Was passiert |
|---|----------|--------|--------------|
| 1 | SCAN | `10_sync.py` | yt-dlp Channel-Scan + Transkripte + Thumbnails + Per-Video-Bookmarks |
| 2 | ANALYZE | `03_analyze_rulebased.py` | Entitäten + Konzepte aus Transkripten |
| 3 | SITE_DATA | `04_build_site_data.py` | `site/data/videos.json` + `graph.json` |
| 4 | BRIEFINGS | `05_extract_briefings.py` | Briefings je Video |
| 5 | ASSEMBLE | `06_assemble_book.py` | `_index.json` + Cross-Ref-Validation |
| 6 | SYNC_DDS | `14_sync_deep_dives_to_book.py` | `dd-*.md` → Kapitel 13 in `_book.json` |
| 7 | SITE_BOOK | `07_build_site_book.py` | `site/data/book.json` für Reader |
| 8 | CONCEPT_IX | `08_build_concept_index.py` | Konzept-Index anreichern |
| 9 | AUTO_BOOK | `13_setup_bookmarks.py --topics-mega` | Auto-Bookmarks für neue MEGA-Themen |

Jede Phase schreibt maschinenlesbare Marker (`PHASE:n:start`, `:log`, `:done`, `:fail`) +
am Ende `UPDATE:done:<seconds>`. Das Backend parst sie und der Phasen-Tracker im UI zeigt
pro Phase Status (○ pending, ◐ running, ✓ done, ✗ fail) + Dauer.

### Was für den Skill rein muss (Phase 2)

**Slash-Command `/scan-channel update [URL]`:**
- Liest `channel.config.json` (Kanal-URL, Keywords, Bookmark-Filter)
- Spawnt `15_full_update.py` mit Channel-URL als Arg statt hardcoded
- Streamt Phasen-Marker an den User mit gleichem UI (oder klartext-Bullets im Chat)
- Akzeptiert Flags:
  - `--skip-sync` (nur Pipeline rebauen, nicht scannen)
  - `--from-phase N` (Wiederaufnehmen ab Phase N)
  - `--dry-run` (zeigen was passieren würde, ohne Schreibvorgänge)

**Channel-agnostische Refaktoren nötig in:**
- `10_sync.py:44` — `CHANNEL_URL` aus config statt hardcoded `@everlastai`
- `10_sync.py:50-66` — `categorize()` aus config.keywords
- `13_setup_bookmarks.py:170` — `GENERIC_COMPANIES` aus config

**Config-Schema-Erweiterung (`channel.config.json`):**
```json
{
  "channel_url": "https://www.youtube.com/@<handle>/videos",
  "channel_name": "...",
  "categorization_keywords": {
    "claude": ["claude", "anthropic", ...],
    "agents": ["agent", "codex", ...]
  },
  "update_filters": {
    "min_videos_for_mega_topic": 10,
    "max_new_per_sync": 30,
    "max_topic_bookmarks_per_sync": 25
  },
  "deep_dive_generic_excludes": ["Google", "Microsoft", ...]
}
```

---

## ✨ Synthese — neue Inhalte automatisch schreiben (Session 6, Backend stubbed)

### Was es heute kann
Im Reader-Header gibt es einen **Synthese-Button** (Symbol ✨). Klick → `/synthesize/status`
listet was offen ist (Topic-DDs, Per-Video-DDs, neue Videos ohne Sektion). Klick zeigt das
Listing, aber **startet noch keine Synthese** — UI sagt klar: "Phase 2 — Backend folgt".
Heute startet der User die Synthese manuell im Chat:
- `Mache die offenen Deep Dives` → Chat-Agent spawnt parallele Sub-Agents je Bookmark
- `Mache die Per-Video-Deep-Dives` → analog für Per-Video
- `Synthetisiere die neuen Sektionen aus den Briefings` → neue Buch-Sektionen

### Was für den Skill rein muss (Phase 2)

**Slash-Command `/scan-channel synthesize [filter]`:**
Macht im Backend, was heute der Chat-Agent händisch tut:
1. Liest `/synthesize/status` (oder direkt die `pending/`-Ordner)
2. Pro Bookmark: ruft den richtigen Aggregator (`09_deep_dive.py --all-pending` /
   `11_per_video_dive.py`) für Dashboard-Daten
3. Spawnt parallele Claude-Code-Subagents (via Agent SDK oder CLI-Pipe) mit dem
   passenden Prompt-Template aus `references/prompts/`
4. Wartet auf Completion, sammelt Logs
5. Lässt am Ende `15_full_update.py --skip-sync --from-phase 5` laufen (Rebuild Buch + Site)

**Drei Modi (filter-Argument):**
- `topics` — nur Topic-DDs (Default)
- `videos` — nur Per-Video-DDs
- `sections` — nur neue Buch-Sektionen aus Briefings
- `all` — alles

**Konfigurierbares Parallelism-Limit** (default 4 — auf VPS-Limits abgestimmt).

**Resume-Verhalten:** wenn ein Agent crasht (API-Socket-Fehler wie in Batch 1),
Bookmark bleibt pending, Skill retried beim nächsten Aufruf automatisch.

**UI-Hook:** Synthese-Button im Reader sendet POST `/synthesize/trigger` →
Backend spawnt **denselben Mechanismus** wie der Slash-Command (gemeinsamer Code-Pfad
in `scripts/16_synthesize.py`, das zu schreiben ist).

---

## Bekannte Bugs/Limits, die der Skill mitbringen muss

1. **Audio-Listener-Leak** (Session 6 gefixt in `site/assets/app.js:213`) — beim
   Wechsel auf neues Audio-Segment alle Listener auf alten Audio nullen, dann
   `removeAttribute("src") + load()`, sonst feuert async `onerror` und kollidiert
   mit neuem State.
2. **DD-Sync-Skript Pflicht** — ohne `14_sync_deep_dives_to_book.py` sind dd-*.md
   im UI **unsichtbar**. Pipeline-Reihenfolge: nach `06_assemble_book.py`, vor
   `07_build_site_book.py`.
3. **`06_assemble_book.py` Sort-Key** muss `dd-*` Sektionen tolerieren (separater
   Sortier-Zweig statt `tuple(int(x))`).
4. **API-Socket-Crashes bei parallelen Agents** — beim Spawnen 4+ Claude-Agents
   gleichzeitig kann eine Verbindung mit "socket connection closed" crashen.
   Retry-Logik: Bookmark bleibt pending, nächster Aufruf greift sie wieder auf.

---

## Was die Skill-Phase-2-Reihenfolge im Skill-Repo sein sollte

```
~/.claude/skills/scan-channel/
├── SKILL.md                      ← Trigger + Workflow + Phasen-Übersicht
├── BACKLOG.md                    ← DU LIEST GERADE
├── scripts/
│   ├── 00_init_channel.py        ← Channel-Config-Wizard (existiert)
│   ├── 01_scan_channel.py        ← refaktorieren auf Config
│   ├── 03_analyze_rulebased.py   ← refaktorieren auf Config
│   ├── ...
│   ├── 14_sync_deep_dives_to_book.py  ← NEU (kopieren)
│   ├── 15_full_update.py         ← NEU (kopieren)
│   └── 16_synthesize.py          ← NEU (zu bauen, Backend für ✨ Synthese)
├── references/prompts/
│   ├── section_synthesis.md
│   ├── deep_dive_synthesis.md    ← v2.0
│   └── per_video_deep_dive_synthesis.md  ← zu erstellen (Phase 3 Roadmap)
└── ui_templates/
    ├── update_button.html        ← Header-Snippet
    ├── synthesize_button.html
    └── phase_tracker.css         ← Phasen-Liste-Style
```

---

## Verifikations-Test für Skill-Phase-2

Wenn `/scan-channel update https://www.youtube.com/@anderer-channel/videos` läuft, muss:
1. `channel.config.json` neu erstellt werden, falls noch nicht da
2. Alle 9 Phasen durchlaufen — Output je Phase im Chat sichtbar
3. Am Ende ein lauffähiges `site/data/book.json` mit den Channel-Inhalten
4. `06_assemble_book.py` zeigt 0 Issues
5. Browser auf `http://127.0.0.1:8765/index.html` zeigt den neuen Channel

Wenn `/scan-channel synthesize topics` läuft, muss:
1. Pending Topic-DDs aus `data/deep_dives/pending/` gelesen werden
2. Parallele Agents spawnen (max 4)
3. Bei Erfolg: `sections/dd-*.md` geschrieben, Bookmark gelöscht
4. Bei Crash eines Agents: Bookmark bleibt, andere laufen weiter
5. Am Ende: Auto-Trigger `15_full_update.py --skip-sync --from-phase 5`
