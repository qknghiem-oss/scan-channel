# 01 — Content-Rules: Wie Sektionen geschrieben werden

## Grundprinzip

Jede Sektion ist ein **eigenständig lesbarer Lehr-Artikel**. Der Leser braucht
das Video NICHT zu sehen, um den Inhalt zu verstehen — aber kann jederzeit per
Timestamp-Klick in die Quelle springen.

## Schreibstil: Erzählend-Lehrbuch

### Was es ist:
- **Narrativ**, nicht enzyklopaedisch
- Roter Faden zieht sich durch die Sektion
- Beispiele und Gedankenexperimente erlaubt
- Persoenliche Stimme erlaubt, aber faktenbasiert
- Übergaenge wie "Daraus folgt…", "Anders gesagt…", "Was bedeutet das praktisch?"

### Was es NICHT ist:
- Keine Stichpunkt-Liste
- Keine reine Zitatesammlung
- Kein trockener Wikipedia-Stil
- Keine Werbe-Sprache

### Eröffnungs-Beispiel (Gold-Standard)

> Im Maerz 2026 noch sah Claude Code aus wie ein praktischer Copilot.
> Drei Monate spaeter ist daraus etwas geworden, was wir vorher nicht hatten —
> ein Werkzeug, das ganze Projekte selbst orchestriert.

→ Eine konkrete Szene, ein Zeitsprung, eine These. KEIN "In dieser Sektion behandeln wir…".

## Laengen-Tiers

| Tier | Wörter | Wann |
|------|---------|------|
| **mega** | 1000-1500 | Kernsaeulen, die der Channel ständig diskutiert |
| **mittel** | 700-1100 | Wichtige Sub-Themen mit eigener Tiefe |
| **neben** | 400-700 | Erganzungen, einzelne Use-Cases, Werkzeugkasten |

Wortzahl-Toleranz: ±15% akzeptabel. Lieber präzise als kuenstlich gestreckt.

## Pflicht-Bausteine pro Sektion

### 1. YAML-Frontmatter (immer)
```yaml
---
section_id: "2.1"
title: "Was Claude Code wirklich ist"
chapter: "Claude Code — Das neue Betriebssystem für Wissensarbeit"
chapter_number: 2
tier: "mega"
word_count: 1400
read_minutes: 7
sources: ["Lu95f1ZBIos", "9nnsszlfE0w", "yOFb95LgnoM", "U07CLU73PEc"]
---
```

### 2. H1 + Meta-Zeile
```markdown
# 2.1 Was Claude Code wirklich ist

⏱ 7 Min Lesezeit · 🎯 Mega-Thema · 🏷 Anfaenger bis Fortgeschritten
```

### 3. Erzählende Eröffnung (1 Absatz, 100-150 Wörter)
Konkrete Szene/Story/These — kein Inhaltsverzeichnis-Vorgriff.

### 4. 3-5 H2-Sektionen mit Fließtext
Jede H2 hat einen aussagekräftigen Titel:
- ✅ "Vom Copilot zum Agent — der konzeptionelle Sprung"
- ❌ "Einleitung"
- ❌ "Hintergrund"

### 5. "Was du jetzt konkret damit anfangen kannst" (am Ende)
Praktische Handlungs-Schritte, 150-200 Wörter. Drei konkrete Reflexe.

### 6. `## 📺 Quellen dieser Sektion`
Liste der Quell-Videos mit Titel, Dauer, View-Count und ID.

### 7. `## 🔗 Verwandtes Wissen`
3-5 Cross-References im `[[X.Y Titel]]`-Format.

## Zitat-Format (PFLICHT)

### Format:
```markdown
> "Wer Claude Code nur als besseren Copilot benutzt,
>  hat den Sprung nicht verstanden."
>
> — Leonard Schmedding, *Automatisiere ALLES mit Claude Code* ([▶ 7:23](video:Lu95f1ZBIos?t=443))
```

### Regeln:
- **WörtlIch.** Kein Paraphrasieren ohne klare Markierung ("sinngemäß").
- **Eingebettet.** Erst Kontext-Satz, dann Zitat, dann Einordnung.
- **Mit Quelle.** `video:VIDEO_ID?t=SEKUNDEN` ist Pflicht — wir parsen das für
  klickbare Timestamp-Links in der HTML-Reader-UI.
- **Mindestens 3 Zitate pro Sektion** (Mega: 5+).

### Falsch:
```markdown
Leonard sagt, dass Claude Code mehr ist als ein Copilot.
```
→ Paraphrase ohne Quelle. Verboten.

### Falsch:
```markdown
Zitat 1: "..."
Zitat 2: "..."
Zitat 3: "..."
```
→ Liste statt Erzählung. Verboten.

## Cross-Reference-Format (PFLICHT)

```markdown
Wer die Tiefe dieses Prinzips erkunden will, findet sie in
[[2.2 Die 5 Prinzipien des Context Engineering]].
```

- Format `[[X.Y Titel]]` — der Reader-JS-Code parst das zu klickbaren Links
- Cross-Refs sollten **organisch** im Text auftauchen, nicht aufgelistet werden
- 3-5 Cross-Refs am Sektions-Ende ist OK, aber im Body wichtiger

## Anti-Halluzinations-Regel

**ABSOLUTE GRENZE:** Was nicht im Briefing steht, wird nicht erfunden.

Erlaubt:
- Glaetten von OCR-/Transkript-Fehlern ("Schlonkowski NN MCP" → "Stitch MCP")
- Sinngemäße Wiedergabe ("sinngemäß sagt X…")
- Eigene Einordnung/Zusammenfassung der Quell-Aussagen

NICHT erlaubt:
- Zahlen erfinden
- Quellen erfinden
- Personen erfinden
- Verlauf erfinden ("danach sagte er…" wenn nicht im Briefing)

## Stil-Eichung

Der **Prototyp ist Sektion 2.1** (`sections/2.1.md`).
Bei Stil-Unsicherheit immer dort schauen — es ist der Tone-Setter.

## Sprache

- **Deutsch** (kanal-folgend)
- Du-Form (lehrbuchhaft, direkt)
- Kurze Saetze bevorzugt
- Aktive Sprache > Passive
