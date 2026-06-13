# Agent-Prompt: Sektions-Synthese (Standard)

Verwende diesen Prompt für jeden Agent, der eine reguläre Buch-Sektion (1.1, 2.3, etc.)
synthetisieren soll. Pro Agent eine Sektion, parallel mehrere Agents möglich.

```text
Schreibe Sektion für deutsches Wissensbuch.

**STIL-PROTOTYP:** `<PROJEKT>/data/knowledge_book/sections/2.1.md`
**BRIEFING:**     `<PROJEKT>/data/knowledge_book/_briefings/<SECTION_ID>.json`

**AUFGABE:** Sektion <SECTION_ID> "<TITEL>", <ZIEL_WÖRTER> Wörter, erzählend-lehrbuchhaft.

**REGELN:**
1. Format wie Prototyp: YAML frontmatter, H1+Meta, 4-5 H2 Abschnitte mit Fließtext,
   "Was du jetzt konkret damit anfangen kannst", Quellen + Verwandtes Wissen.

2. Mindestens N wörtliche Zitate aus Briefing-Chunks. Format:
   > "Zitat hier"
   >
   > — *Video-Titel* ([▶ MM:SS](video:VIDEO_ID?t=SEKUNDEN))

3. Erfinde nichts. Nur aus Briefing.

4. Cross-References: `[[X.Y Titel]]` zu verwandten Sektionen einbauen.

5. Eröffnung: konkrete Szene oder Hook, kein "In dieser Sektion behandeln wir…".

6. Headlines aussagekräftig (keine "Einleitung", "Hintergrund").

**FRONTMATTER:**
```yaml
---
section_id: "<SECTION_ID>"
title: "<TITEL>"
chapter: "<KAPITEL_TITEL>"
chapter_number: <KAPITEL_NUMMER>
tier: "mega|mittel|neben"
word_count: <ZIEL_WÖRTER>
read_minutes: <LESEZEIT_MIN>
sources: ["<VIDEO_ID_1>", "<VIDEO_ID_2>", ...]
---
```

**SPEICHERE:** `<PROJEKT>/data/knowledge_book/sections/<SECTION_ID>.md`

Antworte am Ende mit: "FERTIG <SECTION_ID>" + tatsächliche Wortzahl.
```

## Tier → Wort-Range

| Tier | Wörter | Wann |
|------|--------|------|
| mega | 1000-1500 | Kernsäulen des Channels |
| mittel | 700-1100 | Wichtige Sub-Themen |
| neben | 400-700 | Ergänzungen |

## Mindest-Zitatzahl pro Tier

| Tier | Mindest-Zitate |
|------|---------------|
| mega | 5+ |
| mittel | 3+ |
| neben | 3+ |
