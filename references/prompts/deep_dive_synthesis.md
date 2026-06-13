# Agent-Prompt: Deep-Dive-Synthese v2.0

**Stand:** Session 5 (12.06.2026) — überarbeitet mit User-Klarstellung:
"Lehrbuch mit Kante" + maximale Recherche + Praxisbezug

---

## Template

```text
Du machst einen Deep Dive auf "<TOPIC>" für ein deutsches Wissensbuch.
Dies ist eine **vertiefte Tiefenanalyse**, die über die Standard-Sektion
hinausgeht. Stil: **Lehrbuch mit Kante** — analytisch, eigene Stimme,
nicht polemisch, aber mit klaren Einordnungen.

═══════════════════════════════════════════════════════════════════
SCHRITT 1 — Channel-Material sammeln (alle Quellen lesen)
═══════════════════════════════════════════════════════════════════

Lies:
1. `data/knowledge_book/_index.json` — alle Sektionen + Konzept-Index
2. `data/videos_full.json` — Volltranskripte
3. `data/knowledge_book/sections/*.md` — existierende Sektionen, die
   das Topic erwähnen
4. `data/deep_dives/dashboard_data/<SLUG>.json` (Aggregator-Output)

Sammle daraus:
- Alle wörtlichen Zitate aus dem Channel (mindestens 10 Kandidaten,
  davon wirst du die besten 8-12 verwenden)
- Chronologie: wann wurde X zum ersten Mal erwähnt, wie hat es sich
  entwickelt?
- Welche Personen aus dem Channel haben sich dazu geäußert?
- Welche Behauptungen/Zahlen werden vom Channel aufgestellt?

═══════════════════════════════════════════════════════════════════
SCHRITT 2 — EXTERNE Recherche (Pflicht, mehrere Runden)
═══════════════════════════════════════════════════════════════════

**Wichtig:** Wir nehmen eine NEUTRALE Position ein. Der Channel ist
EINE Perspektive, nicht die Wahrheit. Du musst aktiv andere
Perspektiven einholen.

**Mindestens 3 Recherche-Runden:**

Runde 1 — Faktenvalidierung:
  WebSearch("<TOPIC> 2026 latest")
  WebSearch("<TOPIC> review benchmark study")
  → Stimmen die Channel-Behauptungen? Welche Zahlen werden offiziell
    bestätigt? Welche sind übertrieben?

Runde 2 — Gegenperspektiven:
  WebSearch("<TOPIC> criticism OR alternative OR debate")
  WebSearch("<TOPIC> vs alternatives 2026")
  → Wer widerspricht? Welche Alternativen gibt es? Was sehen andere
    Quellen anders?

Runde 3 — Praxisbezug (PFLICHT):
  WebSearch("<TOPIC> use case OR practical OR praxis OR tutorial")
  WebSearch("<TOPIC> production OR enterprise")
  → Was sind echte praktische Anwendungen? Wo wird X im Alltag
    konkret eingesetzt? Welche Praxistests gibt es?

Nutze WebFetch für die 3-5 wichtigsten Quellen, um konkrete
Zitate/Daten/Studien zu extrahieren.

**Notiere für jede Quelle: URL, Datum, Kern-Aussage.**

═══════════════════════════════════════════════════════════════════
SCHRITT 3 — Schreibe sections/dd-<SLUG>.md im "Lehrbuch mit Kante"-Stil
═══════════════════════════════════════════════════════════════════

**Tone of Voice:**
- Narrativ wie die Standard-Sektionen (siehe `sections/2.1.md`)
- ABER mit klar analytischer Stimme: du ordnest ein, du widersprichst
  begründet, du machst Pro/Contra sichtbar
- Eigene Synthese erlaubt — aber faktenbasiert, nicht polemisch
- Adressiere den Leser mit "Du" (lehrbuchhaft, direkt)

**Länge: 3500-4500 Wörter** (doppelt so lang wie Standard-Sektion)

**Pflicht-Frontmatter:**
```yaml
---
section_id: "dd-<SLUG>"
title: "Deep Dive: <TOPIC>"
chapter: "Deep Dives"
chapter_number: 13
tier: "mega"
word_count: 4000
read_minutes: 20
deep_dive: true
deep_dive_topic: "<TOPIC>"
deep_dive_type: "<concept|person|tool|company>"
deep_dive_depth: "deep"
sources_channel: ["<VIDEO_ID_1>", "<VIDEO_ID_2>", ...]
sources_external: ["<URL_1>", "<URL_2>", "<URL_3>"]
generated_at: "<ISO>"
character: "lehrbuch-mit-kante"
---
```

**Pflicht-Struktur (6 H2-Abschnitte):**

## 1. Was IST <TOPIC> eigentlich?
(500-700 Wörter)
- Klare Definition (nicht der Channel-Definition kopieren — eigene)
- Historischer Kontext (woher kommt das, seit wann gibt es das)
- 1-2 wörtliche Zitate aus dem Channel + 1 externes Faktum
- Eigene Einordnung in 1-2 Sätzen

## 2. Wie der Channel <TOPIC> behandelt
(800-1000 Wörter)
- Chronologie: zeitlich geordnete Erwähnungen
- Mindestens 5 wörtliche Zitate mit Timestamp-Quellen
- Cross-References zu allen relevanten Standard-Sektionen: [[X.Y Titel]]
- Wichtige Pivots/Erkenntnisse des Channels über Zeit

## 3. Was die externe Welt dazu sagt
(800-1000 Wörter)
- Synthese aus mindestens 3 externen Quellen
- Vergleich Channel-Perspektive vs. externe Konsens vs. Kritiker
- Konkrete Zahlen/Studien/Reports zitieren (mit Datum)
- Wo deckt sich, wo widerspricht es?

## 4. Praxisbezug — was hier WIRKLICH passiert
(600-800 Wörter) **WICHTIG: NEU IN V2.0**
- Konkrete Praxis-Anwendungen aus externen Quellen
- Welche Firmen/Personen nutzen X produktiv?
- Welche Praxis-Tests/Benchmarks/Erfahrungsberichte gibt es?
- Was funktioniert, was funktioniert nicht?
- Konkrete Code-Beispiele/Workflows/Use Cases (wenn applicable)
- Nicht abstrakt bleiben — der Leser muss verstehen, was er damit
  morgen anfangen kann

## 5. Lücken, blinde Flecken, offene Fragen
(400-500 Wörter)
- Was wird NICHT im Channel behandelt?
- Welche Fragen bleiben offen?
- Welche Aspekte werden vom Channel überbetont/unterbetont?
- Eigene begründete Kritik (3-4 Punkte)

## 6. Wie ich <TOPIC> 2026 einordne — meine Synthese
(400-500 Wörter)
- Eigene Position des Autors (das ist die "Kante")
- 3-5 zentrale Erkenntnisse
- Was bedeutet das für den Leser konkret?
- Was kommt als nächstes (Prognose mit Vorsicht)?

**Footer (Pflicht):**

## 📺 Quellen dieser Sektion

### Aus dem Channel (mit Timestamps)
- (Top-Videos mit ID + Erwähnungs-Count + Timestamps)

### Externe Quellen
- URL: Charakterisierung + Datum
- Mindestens 3-5 externe Sources

## 📎 Marginalia
[Person-/Tool-/Zahl-Marker mit Definitionen]

## 🎨 Visualisierungen
Mindestens **2 inline-Visualisierungen** {{viz:type|params}}:
- z.B. {{viz:evolution|versions=...}} für historische Entwicklung
- z.B. {{viz:compare|items=...}} für Vergleiche
- z.B. {{viz:quote-box|text=...|author=...}} für Schlüsselzitate

## 🔗 Verwandtes Wissen
- Mindestens 5 Cross-Refs zu Standard-Sektionen
- Mindestens 2 Cross-Refs zu anderen Deep Dives (falls vorhanden)

═══════════════════════════════════════════════════════════════════
SCHRITT 4 — Metadaten speichern
═══════════════════════════════════════════════════════════════════

Schreibe `data/deep_dives/generated/<SLUG>.json`:
```json
{
  "topic": "<TOPIC>",
  "slug": "<SLUG>",
  "type": "concept|person|tool|company",
  "depth": "deep",
  "character": "lehrbuch-mit-kante",
  "generated_at": "<ISO>",
  "word_count": <TATSÄCHLICH>,
  "sources_channel_count": <ANZAHL>,
  "sources_external_count": <ANZAHL>,
  "research_rounds": 3,
  "praxis_examples": <ANZAHL>,
  "section_file": "dd-<SLUG>.md"
}
```

═══════════════════════════════════════════════════════════════════
SCHRITT 5 — Bookmark abräumen
═══════════════════════════════════════════════════════════════════

Lösche `data/deep_dives/pending/<BOOKMARK_FILE>.json`.

═══════════════════════════════════════════════════════════════════
SCHRITT 6 — Pipeline-Rebuild (NICHT bei jedem DD, sondern am Ende
              eines Batches)
═══════════════════════════════════════════════════════════════════
```bash
python scripts/06_assemble_book.py
python scripts/07_build_site_book.py
python scripts/08_build_concept_index.py
```

═══════════════════════════════════════════════════════════════════
ANTWORT-FORMAT
═══════════════════════════════════════════════════════════════════

Am Ende:
"FERTIG Deep Dive: <TOPIC>
  Wörter: <N>
  Channel-Zitate: <N>
  Externe Quellen: <N>
  Praxis-Beispiele: <N>
  Visualisierungen: <N>
  Marginalia: <N>"
```

---

## Anti-Muster (was zu vermeiden ist)

❌ **Oberflächliche Aggregation:** "Hier sind alle Erwähnungen von X
   im Channel" — das macht 09_deep_dive.py schon. Wir wollen Synthese.

❌ **Channel-Nachsprechen:** Wenn der Channel sagt "X ist die Zukunft",
   musst du das prüfen — nicht einfach übernehmen.

❌ **Mehr Zitate ≠ besserer Deep Dive:** Wähle die 8-12 besten, nicht 30.

❌ **Externe Recherche ohne Einordnung:** "Hier sind 5 Links" reicht nicht.
   Du musst sie SYNTHETISIEREN.

❌ **Praxis als Spätschlag:** Praxisbezug ist Pflicht-H2, nicht ein
   versteckter Nachsatz.

❌ **"Bequemes" Schreiben ohne Kante:** Du sollst eine Position haben.
   Nicht polemisch — aber klar.

---

## Cap-Längen + Quality-Gates

- Hard-Cap: **5000 Wörter**. Über 5000 = aufteilen in zwei DDs.
- Mindestens 8 wörtliche Channel-Zitate (≠ Paraphrasen)
- Mindestens 3 externe Quellen mit WebFetch
- Mindestens 3 Praxis-Beispiele
- Mindestens 2 Inline-Visualisierungen

Wenn ein Topic weniger als 5 Channel-Erwähnungen hat: Bookmark abräumen
mit Status "insufficient_material" und User informieren.
