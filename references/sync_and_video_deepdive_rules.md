# 06 — Sync-Trigger + Per-Video Deep Dive

> Diese Regel ergänzt die bisherigen 05 Regeln um zwei kritische Workflows:
> **inkrementelle Synchronisation** mit dem Channel und **Tiefenanalyse pro Video**
> (statt nur pro Thema).

## Teil 1: Sync-Trigger (manueller Refresh)

### Prinzip

Das Buch ist NICHT statisch. Der Channel veröffentlicht neue Videos.
Ein **manueller Sync-Button** im UI startet eine inkrementelle Pipeline,
die nur neue Videos verarbeitet — alte Videos und bestehende Sektionen
bleiben unangetastet.

### Wann triggert der User Sync?
- Nach einem neuen Video-Release auf dem Channel
- Wöchentlich als Routine
- Vor einer Lese-Session, um aktuell zu sein

### Was passiert beim Sync?
```
┌─────────────────────────────────────────────────────────────────┐
│  1. yt-dlp scannt Channel-URL                                   │
│  2. Filtert: video_id NOT IN data/videos_full.json              │
│  3. Falls 0 neue: "Nichts zu tun" — Ende                        │
│  4. Falls n neue:                                               │
│     a. Transkripte ziehen                                       │
│     b. Thumbnails laden                                         │
│     c. Regel-Analyse (Konzepte aktualisieren)                   │
│     d. Briefings für neue Videos                                │
│     e. Per-Video-Deep-Dive für neue Videos (siehe Teil 2)       │
│     f. _book.json: Kapitel-Zuordnung vorschlagen                │
│        ⚠ User muss bestätigen (UI-Dialog)                       │
│     g. Sektionen synthetisieren ODER vermerken als "todo"       │
│     h. Pipeline 06+07+08 re-laufen                              │
│  5. UI updated automatisch (Browser-Reload via SSE oder Polling)│
└─────────────────────────────────────────────────────────────────┘
```

### Sync-Status-Datei

`data/sync_state.json`:
```json
{
  "last_sync_at": "2026-06-11T14:30:00",
  "last_channel_scan_at": "2026-06-11T14:30:05",
  "known_video_ids": ["w2fVxiUPTv4", "XAPDzR2Xvng", "..."],
  "pending_new_videos": [
    {"id": "...", "discovered_at": "...", "title": "...", "status": "pending_assignment"}
  ],
  "sync_history": [
    {"at": "...", "found_new": 0, "duration_seconds": 12}
  ]
}
```

Die Datei ist die **Quelle der Wahrheit** für was bekannt ist.

### Endpunkt-Spezifikation

```
POST /sync
  → startet Sync im Hintergrund, kehrt sofort mit {job_id} zurück
  
GET /sync/status?job_id=...
  → {status: "running|done|failed", progress: 0-100, message: "...", new_videos: [...]}
  
GET /sync/state
  → liefert sync_state.json
```

### UI-Sync-Button

Im Header oder Deep-Dive-Tab:
```
[🔄 Channel-Sync]  · Zuletzt: vor 2h · 0 neue
```

Klick öffnet einen Progress-Modal:
```
┌─────────────────────────────────────┐
│ Synchronisiere @everlastai ...      │
│ ⏳ Scanne Channel ...               │
│ ✓ 2 neue Videos gefunden            │
│ ⏳ Lade Transkripte ...             │
│ ⏳ Analysiere ...                   │
│ ⏳ Bereite Briefings vor ...        │
│                                     │
│ → 2 neue Videos zur Zuordnung      │
│   bereit. Im Chat ausfuehren:       │
│   "Mache die Sync-Sektionen"        │
└─────────────────────────────────────┘
```

## Teil 2: Per-Video Deep Dive

### Prinzip

Bisheriges Deep-Dive arbeitet **pro Thema/Konzept** (z.B. "Claude Code").
Per-Video Deep Dive arbeitet **pro einzelnem Video** — ein eigenständiger
Lese-Artikel pro Video, der auf Transkript + Thumbnail + Kapitel basiert.

### Warum brauchen wir das?

- Jedes Video hat einen eigenen Wert, der über die Verwendung in Themen
  hinausgeht
- Manche User wollen **dieses spezifische Video tief verstehen** ohne in
  Themen-Hopping zu gehen
- Es ist die Grundlage für die später folgende Themen-Synthese: erst pro
  Video durchanalysieren, dann thematisch zusammenführen

### Datenfluss

```
videos_full.json (Transkript + Metadaten)
  ↓
data/per_video_deep_dives/
  ├── <video_id>.md   ← Lehr-Artikel (1500-2500 Worte)
  └── <video_id>.json ← Strukturierte Metadaten
```

### Pro-Video-Artikel-Struktur

```yaml
---
video_id: "lHU6jFHWAkM"
title: "Deep Dive: Claude Opus 4.8 — Was DIESE 7 Dinge wirklich bedeuten"
source_video_title: "Claude Opus 4.8: DIESE 7 Dinge ändern jetzt ALLES!"
published: "2026-05-31"
duration_min: 18
view_count: 48651
deep_dive_type: "per_video"
word_count: 2200
related_topics: ["claude-opus-4-8", "dynamic-workflows", "ultracode"]
related_sections: ["1.1", "2.3", "3.1"]
generated_at: "2026-06-11T15:00:00"
---

# Deep Dive: <Video-Titel> — Was DIESES Video wirklich bedeutet

[Hero-Bild: Thumbnail des Videos]

## Worum geht es? (3-Satz-Zusammenfassung)
...

## Die 7 Kern-Aussagen
[Pro Kapitel im Video eine Kern-Aussage, mit Timestamp]

## Was im Video gezeigt wird (visuell)
[Bezug zu Thumbnail/Vorschau-Bildern]

## Eingebettete Zitate (5-10 wörtliche)
> "..."
> — ([▶ MM:SS](video:VIDEO_ID?t=SEC))

## Was das Video für die Themen X, Y, Z bedeutet
[Cross-Refs zu thematischen Sektionen 1.1, 2.3, etc.]

## Lese-Empfehlungen (was als Nächstes)
- [[1.1]] für die Marktlage
- [[2.3]] für die Code-Aspekte

## 📎 Marginalia
[Person-/Tool-/Zahl-Marker wie in Standard-Sektionen]
```

### UI-Integration

**Im Video-Modal (Quellen-Bibliothek):**
```
[Video-Titel]
[Embed]
[Beschreibung]
[Kapitel-Liste]

→ Neuer Button: "🔬 Per-Video Deep Dive lesen"
```

Falls Deep Dive noch nicht existiert:
```
→ Button: "🔬 Deep Dive für dieses Video erstellen"
  (legt Bookmark in pending/)
```

**Neuer Sub-Tab im Deep-Dive-Tab:** "📹 Pro Video"
Liste aller fertigen Per-Video-Deep-Dives als Karten.

### Image-Extraktion

Bisher haben wir nur Hauptthumbnail. Für Per-Video Deep Dive holen
wir zusätzlich Vorschau-Bilder:

```python
# Thumbnails pro Kapitel (storyboard) per yt-dlp
yt-dlp --write-thumbnail \
       --thumbnail-format jpg \
       --write-info-json \
       <video_url>
       
# YouTube hat hqdefault, sd1-sd3, maxresdefault
# Wir nutzen alle vier für Per-Video Deep Dive
```

Speicherort: `data/per_video_assets/<video_id>/`
```
hero.jpg        ← maxresdefault
preview-1.jpg   ← sd1 (Anfang)
preview-2.jpg   ← sd2 (Mitte)
preview-3.jpg   ← sd3 (Ende)
chapters.json   ← Kapitel mit Zeitstempeln
```

### Agent-Prompt für Per-Video Deep Dive

Siehe `references/prompts/per_video_deep_dive_synthesis.md` (neu anzulegen).

## Teil 3: Integration in den Sync-Workflow

Beim Sync werden für jedes **neue** Video automatisch:
1. Transkript geladen
2. Thumbnail + Preview-Bilder geladen
3. **Per-Video Deep Dive synthetisiert** (Agent im Chat)
4. Bookmark in `data/deep_dives/pending/` falls thematische Zuordnung
   unklar

So entsteht aus jedem neuen Video automatisch ein lesbarer Tiefen-Artikel.

## Lese-Pflicht-Check (vor "fertig")

Für Per-Video Deep Dive:
1. **Hero-Bild** vorhanden und referenziert?
2. **3-Satz-Zusammenfassung** in Eröffnung?
3. **Mindestens 5 wörtliche Zitate** mit Timestamps?
4. **Cross-Refs** zu mind. 3 thematischen Sektionen?
5. **Marginalia** für Personen/Tools/Zahlen aus dem Video?
6. **Lese-Empfehlungen** am Ende?

Für Sync:
1. `sync_state.json` aktualisiert?
2. Alle neuen Videos haben Transkript + Thumbnails?
3. Pipeline 06+07+08 sind neu gelaufen?
4. UI lädt neue Daten ohne Manual-Reload?
