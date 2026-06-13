# 04 — Workflow-Rules: Wie wir konkret arbeiten

## Workflow A: Eine bestehende Sektion überarbeiten

1. **Sektion lesen:** `data/knowledge_book/sections/X.Y.md`
2. **Briefing checken:** `data/knowledge_book/_briefings/X.Y.json` (was lag der KI vor?)
3. **Aendern:** Manuell oder via Agent neu schreiben lassen
4. **Validieren:** `python scripts/06_assemble_book.py` (Issues = 0?)
5. **Buch + Konzepte neu bauen:**
   ```bash
   python scripts/07_build_site_book.py
   python scripts/08_build_concept_index.py
   ```
6. **Browser reload** mit Cache-Buster: `?v=X` an URL.

## Workflow B: Neues Kapitel oder neue Sektion hinzufuegen

1. **`_book.json` editieren** — neuen Kapitel-Block oder Sektions-Block einfuegen.
2. **`coverage_video_ids`** updaten — alle 45 Video-IDs müssen mindestens 1x abgedeckt sein.
3. **Briefing extrahieren:** `python scripts/05_extract_briefings.py`
4. **Sektion synthetisieren:** Agent mit Stil-Prototyp `2.1.md` + Briefing.
5. **Validierung + Re-Build** wie Workflow A.

## Workflow C: Neuen Channel scannen (Multi-Channel-Vision)

Dies ist die **Vision** — noch nicht fertig automatisiert. Manuelle Schritte:

1. **`scripts/01_scan_channel.py`** anpassen:
   - `CHANNEL_URL` ändern
   - `CATEGORY_KEYWORDS` an den neuen Channel anpassen
2. **Pipeline laufen lassen** (Schritte 01-04)
3. **Topic-Clustering** manuell (oder via Agent):
   - Lies alle Titel + Chapters
   - Cluster in 10-15 Kapitel mit jeweils 3-4 Sektionen
   - Schreibe ein neues `_book.json`
4. **Briefings + Sektionen** wie Workflow B
5. **Channel-spezifische Styles** anpassen (Kategorie-Farben?)

**Ziel:** Diese 5 Schritte in einen Skill `/scan-channel <URL>` automatisieren.

## Workflow D: Wissensbuch lokal prüfen

```bash
# Server starten (1x pro Session)
python scripts/serve.py
# Browser: http://127.0.0.1:8765/index.html

# Bei JS/CSS-Änderungen: Cache-Buster
# http://127.0.0.1:8765/index.html?v=2

# Test laufen lassen
python scripts/test_site.py
# → 35/35 OK erwartet
```

## Workflow E: Pipeline von Null neu starten

```bash
# 1. Daten löschen (Vorsicht!)
rm -rf data/videos_list.json data/videos_full.json data/knowledge_graph.json
rm -rf data/knowledge_book/_briefings data/knowledge_book/_index.json
rm -rf site/data/*.json

# 2. Skripte sequenziell
python scripts/01_scan_channel.py        # ~5 Min
python scripts/02_extract_transcripts.py # ~15 Min (Rate Limit)
python scripts/03_analyze_rulebased.py   # <1 Min
python scripts/04_build_site_data.py     # <1 Min
python scripts/05_extract_briefings.py   # <1 Min

# 3. Sektionen: Agent-basiert, neu schreiben
#    (Stil-Prototyp ist 2.1.md — siehe rules/01_CONTENT_RULES.md)

# 4. Buch zusammensetzen
python scripts/06_assemble_book.py
python scripts/07_build_site_book.py
python scripts/08_build_concept_index.py

# 5. Test
python scripts/test_site.py
```

## Agent-Briefing-Template (für Sektions-Synthese)

Wenn ein Agent eine Sektion schreiben soll, folgendes Briefing-Template:

```text
Schreibe Sektion für deutsches Wissensbuch.

STIL-PROTOTYP: data/knowledge_book/sections/2.1.md
BRIEFING:     data/knowledge_book/_briefings/X.Y.json

AUFGABE: Sektion X.Y "Titel", Z Wörter, erzählend-lehrbuchhaft.

REGELN:
1. Format wie Prototyp: YAML frontmatter, H1+Meta, 4 H2, Praxis-Block, Quellen, Verwandtes.
2. Mindestens N wörtliche Zitate aus Briefing. Format:
   > "Zitat"  > — *Titel* ([▶ MM:SS](video:ID?t=SEK))
3. Erfinde nichts. Nur aus Briefing.
4. Cross-Refs: [[X.Y Titel]] zu verwandten Sektionen.
5. Eröffnung: konkrete Szene/Story.

FRONTMATTER: [YAML hier]
SPEICHERE: sections/X.Y.md

Antworte: "FERTIG X.Y" + Wortzahl.
```

## Session-Continuity-Workflow (WICHTIG)

**Bei JEDEM Session-Start:**
1. `CLAUDE.md` lesen (automatisch durch Harness)
2. `SESSION.md` lesen — letzter Stand
3. Optional: `/resume` Skill verwenden

**Bei JEDEM Session-Ende oder großen Schritt:**
1. `SESSION.md` updaten mit:
   - Datum + Zeit
   - Was gemacht wurde
   - Aktuelle offene Punkte
   - Nächste sinnvolle Schritte
2. Optional: `/compress` Skill verwenden

**Auto-Trigger:** Der `Stop`-Hook in `.claude/settings.local.json` erinnert
Claude am Ende der Session, `SESSION.md` zu aktualisieren.

## Pflicht-Verifikation

**Niemals "fertig" sagen ohne:**
- `python scripts/06_assemble_book.py` → 0 Issues
- `python scripts/test_site.py` → 35/35 OK
- Manueller Browser-Check der geänderten Sektion

## Was nicht im Workflow gehoert

- Sektionen ohne Quellen oder mit weniger als 3 Zitaten "fertig" melden
- Direkte HTML-Edits in `site/index.html` ohne Update der zugrundeliegenden Daten
- "Quick-Fix" in `app.js` ohne entsprechendes Test-Case-Update
- Channel-spezifische Hardcodierung an Stellen, die generisch sein sollten
  (kann an Multi-Channel-Vision blockieren)
