# 05 — Anti-Wiederholungs-Regeln

> Wiederholungen sind Lese-Friktion. Jeder Begriff, jede Zahl, jede Definition
> wird im Buch **EINMAL** eingeführt. Danach wird verlinkt, nicht wiederholt.

## Die drei Prinzipien

### Prinzip 1: Eine Wahrheit, ein Ort

Jedes Konzept (z.B. "Claude Code", "Agent = Modell + Harness", "Mythos")
hat **genau eine Sektion**, in der es definiert wird. Die anderen Sektionen
**verlinken** auf diese Definition, sie wiederholen sie nicht.

**Falsch:**
```markdown
# Sektion 2.5
Claude Code ist Anthropics KI-Coding-Agent, der nicht nur Code schreibt,
sondern ganze Software-Projekte selbstständig orchestriert...
```
(Das hat 2.1 schon erklärt — hier wieder. Verschwendung.)

**Richtig:**
```markdown
# Sektion 2.5
[[2.1 Was Claude Code wirklich ist]] zeigt die Definition. Was wir hier
behandeln, ist die organisatorische Konsequenz für Unternehmen...
```

### Prinzip 2: Zahlen-Index — nicht im Fließtext wiederholen

Zahlen und Statistiken werden **einmal genannt** und dann über die
Marginalia-Spalte (linker Rand) verfügbar gemacht. Im Fließtext:
nur verweisen.

**Falsch:**
```markdown
Anthropic ist mittlerweile 965 Milliarden Dollar wert...
... 70% der Fortune-100-Unternehmen nutzen Claude...
Anthropic ist mit 965 Milliarden Dollar mehr wert als OpenAI...
```
(Die 965-Mrd-Zahl tauchten dreimal auf in drei Sektionen.)

**Richtig:**
Erste Sektion definiert die Zahl mit Marginalia-Marker:
```markdown
Anthropic erreichte im Mai 2026 eine Bewertung von [^zahl:anthropic-mai-2026].

[^zahl:anthropic-mai-2026]:
  - Wert: 965 Mrd. USD
  - Datum: 26.05.2026
  - Quelle: Vorsprung-Folge (▶ 11:44 video:ui2418ZlUYM)
```

Andere Sektionen referenzieren:
```markdown
Mit der Bewertung von [Mai 2026][^zahl:anthropic-mai-2026] hat Anthropic
OpenAI erstmals überholt.
```

### Prinzip 3: Person-Profile in Marginalia, nicht in jedem Text

Wenn eine Person erstmals erwähnt wird, wird ein **Person-Marker**
gesetzt. Die Kurzbeschreibung erscheint in der linken Marginalia-Spalte,
nicht erneut im Text.

**Falsch:**
```markdown
Leonard Schmedding, Gründer von Everlast AI, erklärt im Vortrag...
... Schmedding (Everlast-AI-Gründer) sagt im Tutorial...
```

**Richtig:**
Erste Sektion:
```markdown
[^person:leonard-schmedding] erklärt im Vortrag...

[^person:leonard-schmedding]:
  Leonard Schmedding · Gründer Everlast AI · Host des Channels
```

Spätere Sektionen:
```markdown
[Schmedding][^person:leonard-schmedding] sagt im Tutorial...
```

## Marginalia-Marker-System

### Syntax in Markdown

```markdown
Im Text steht ein Marker [^typ:slug].

Am Ende der Sektion stehen die Definitionen:

[^person:leonard-schmedding]:
  Leonard Schmedding · Gründer Everlast AI · Host

[^tool:claude-code]:
  Anthropics KI-Coding-Agent (siehe [[2.1]])

[^zahl:anthropic-mai-2026]:
  965 Mrd. USD · 26.05.2026 · (▶ video:ui2418ZlUYM?t=704)

[^begriff:harness]:
  Geruest aus Dateien, Regeln, Tools, MCP-Servern,
  das ein Agent zur Verfuegung hat (siehe [[2.1]])
```

### Typen

| Marker-Typ | Was steht in der Marginalia | Beispiel |
|------------|------------------------------|----------|
| `person:` | Vorname Nachname · Rolle · Channel-Beziehung | Leonard Schmedding · Gründer Everlast AI · Host |
| `tool:` | Was es ist · wo definiert | Anthropics KI-Coding-Agent (siehe [[2.1]]) |
| `firma:` | Branche · Sitz · was sie machen | KI-Lab San Francisco · macht Claude |
| `zahl:` | Wert · Datum · Quelle | 965 Mrd USD · 26.05.2026 · ▶ video... |
| `begriff:` | Definition in 1 Satz + Cross-Ref | Geruest fuer Agenten · siehe [[2.1]] |
| `quelle:` | Externe URL/Buch/Studie | doi:10.1234... |

### Frontend-Rendering

Im Buch-Layout (links neben Content) erscheint pro Marker eine
**Marginalia-Karte**:

```
┌───────────────────────────┐
│ 👤 Leonard Schmedding     │
│ Gründer Everlast AI · Host│
└───────────────────────────┘

┌───────────────────────────┐
│ 💰 Anthropic-Bewertung    │
│ 965 Mrd USD · 26.05.2026  │
│ → Video ▶ 11:44           │
└───────────────────────────┘
```

Klick auf die Karte:
- `person:` → Person-Detailseite (alle Sektionen wo erwähnt)
- `zahl:` → Springt zum Video an genannter Zeit
- `tool:`/`begriff:` → Springt zur definierenden Sektion

## Visualisierungs-System

### Syntax

```markdown
{{viz:type|param1=value1|param2=value2}}
```

### Verfügbare Typen

| Typ | Was es zeichnet | Parameter |
|-----|------------------|-----------|
| `viz:timeline` | Zeitleiste mit Punkten | `topic=X`, `from=Datum`, `to=Datum` |
| `viz:compare` | Vergleichs-Balken | `items=A:5,B:3,C:7` |
| `viz:evolution` | Versions-Stufen | `versions=1.0,2.0,3.0\|notes=...` |
| `viz:network` | Mini-Konzept-Netz | `center=Topic\|connects=A,B,C` |
| `viz:quote-box` | Hervorgehobenes Zitat-Pull | `text=...\|author=...` |

### Beispiel

```markdown
Die Claude-Modelle entwickelten sich in drei Sprüngen:

{{viz:evolution|versions=4.6,4.7,4.8|notes=Tokenizer-Problem,Mythos-Leak,Dynamic-Workflows}}

Im direkten Vergleich:

{{viz:compare|title=Marktanteil Business|items=Anthropic:70,OpenAI:25,Google:5}}
```

Frontend rendert diese als D3-Diagramme im Fließtext.

## Lese-Pflicht-Check (vor "fertig")

Bevor eine Sektion als fertig gilt, prüfe:

1. **Keine Wiederholungen** mit anderer Sektion? Wenn doch: refactore zu
   Cross-Reference.
2. **Zahlen markiert** mit `[^zahl:...]` und einmal definiert?
3. **Personen markiert** mit `[^person:...]` (erst-erwähnt) bzw.
   referenziert (spätere)?
4. **Tools/Begriffe** mit `[^tool:]`/`[^begriff:]` einmalig definiert?
5. **Wo passend: eine Visualisierung** statt langer Aufzählung?

## Ausnahme: Eröffnungs-Wiederholung

Die ersten 1-2 Sätze einer Sektion DÜRFEN ein Konzept kurz wiederholen,
**wenn** es Kontext für den Eröffnungs-Hook braucht. Beispiel:

> "Claude Code ist zur orchestrierenden Schicht geworden, wie wir
> in [[2.1]] gesehen haben. Was wir jetzt fragen: Wie verändert das
> die Organisation eines Unternehmens?"

Das ist Kontext-Setting, nicht Wiederholung.

## Migrations-Strategie für bestehende Sektionen

Die existierenden 39 Sektionen wurden ohne diese Regeln geschrieben.
Sie haben Wiederholungen.

**Pragmatischer Cleanup-Pass** (nicht alle auf einmal):

1. **Pro Konzept** identifizieren, wo es am besten erklaert ist
   (Anker-Sektion)
2. In den ANDEREN Sektionen: Definition durch Cross-Ref ersetzen
3. Zahlen mit häufiger Wiederholung: in Marginalia migrieren
4. Personen: gleiches

Cleanup nicht als großen Bang, sondern **Sektion für Sektion**
bei Bedarf — sobald jemand eine spürbare Wiederholung sieht.
