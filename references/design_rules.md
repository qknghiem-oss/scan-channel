# 02 — Design-Rules: Visuelle Identitaet

## Grundprinzip

**Dark Mode First.** Ruhig, lesbar, gedaempfte Farben.
Buch-Inhalt steht im Fokus — UI tritt zurück.

## Farbpalette

### Hintergrund (Dark Mode)
```css
--bg-primary:   #0a0a0f   /* Haupthintergrund — fast schwarz mit Hauch Blau */
--bg-secondary: #12121a   /* Sekundär-Hintergrund (Header, Footer) */
--bg-card:      #181822   /* Karten, Sidebars */
--bg-hover:     #22222e   /* Hover-State */
--bg-input:     #1f1f2c   /* Inputs, Code-Bloecke */
```

### Text
```css
--text-primary:   #f1f5f9   /* Haupttext */
--text-secondary: #94a3b8   /* Sekundär (Meta, Labels) */
--text-muted:     #64748b   /* Dezent (Zahlen, Hilfslinien) */
```

### Borders
```css
--border:        #2a2a3a
--border-bright: #3f3f55   /* Hover-Borders */
```

### Kategorie-Farben (zentral für alles)

| Kategorie | Farbe | Verwendung |
|-----------|-------|------------|
| **Claude / Anthropic** | `#8b5cf6` (Lila) | Primäraktion, Active-State, Cross-Refs |
| **AI Agents & Coding** | `#3b82f6` (Blau) | Timestamps, Sekundäraktion |
| **Experten-Interviews** | `#10b981` (Gruen) | Erfolgs-/Gelesen-State |
| **Robotik & Hardware** | `#06b6d4` (Cyan) | Hardware-Themen |
| **Business & Wirtschaft** | `#f59e0b` (Orange) | Schlüsselzahlen |
| **Google & OpenAI** | `#fbbf24` (Gelb) | Warnungen |
| **Tools & Use Cases** | `#14b8a6` (Teal) | Praktische Hinweise |
| **China & Geopolitik** | `#ef4444` (Rot) | Löschen/Schließen, alarmierend |

**Regel:** Die 8 Kategorie-Farben sind die EINZIGE Farb-Quelle. Keine wilden
Eigen-Erfindungen. Wenn etwas Neues farbig markiert werden muss, Kategorie zuordnen.

## Typografie

### Fonts (Google Fonts)
```css
--font-ui:      'Inter', -apple-system, sans-serif   /* UI-Elemente */
--font-reading: 'Lora', Georgia, serif                /* Lesetext */
--font-mono:    'JetBrains Mono', monospace          /* Code, Timestamps */
```

### Wo welcher Font?
- **Inter** — alle UI-Elemente (Header, Buttons, Tabs, Sidebar, Karten)
- **Lora** — Buch-Lesetext (Artikel-Body, Blockquotes)
- **JetBrains Mono** — Section-IDs (1.1), Timestamps (▶ 7:23), Code-Snippets

### Größen
```css
H1:    30px / weight 800 / letter-spacing -0.02em
H2:    22px / weight 700 / letter-spacing -0.01em
H3:    17px / weight 700
Body:  16.5px / line-height 1.72   /* Lese-Optimal */
UI:    14px / weight 500
Meta:  13px / color secondary
Mini:  11px / weight 600 / uppercase / letter-spacing 0.04em
```

## Layout-Architektur

### Buch-View (Full-Bleed)
Das Buch nutzt die VOLLE Viewport-Breite (bricht aus `#main { max-width: 1600px }` aus).

```
[300px Sidebar] [gap 28px] [Content max 820px] [gap 28px] [320px Aside]
←am Rand                                                        am Rand→
```

CSS-Trick (full-bleed via negative Margin):
```css
.view.active.book-view {
  width: 100vw;
  left: 50%;
  margin-left: -50vw;
  margin-top: -32px;
  margin-bottom: -80px;
  padding: 24px 28px 80px;
}
```

### Andere Views (Centered, max 1600)
Konzept-Wiki, Timeline, Bibliothek bleiben in `#main` mit max-width.

## Spacing-System

Basis-Einheit: **4px**. Skala: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 56.

- Karten-Padding: `24px 28px`
- Buch-Content-Padding: `48px 56px` (luftig, gut zum Lesen)
- Sidebar-Padding: `18px 14px`

## Komponenten

### Karte (`.card`)
```css
background: var(--bg-card)
border: 1px solid var(--border)
border-radius: 14px
padding: 24px
box-shadow: 0 4px 20px rgba(0,0,0,0.35)
```

### Sticky-Sidebar (TOC + Aside)
```css
position: sticky
top: 130px
max-height: calc(100vh - 150px)
overflow-y: auto
```

### Quote (Buch-Blockquote)
```css
border-left: 4px solid var(--cat-claude)
background: linear-gradient(135deg, color-mix(..., cat-claude 10%), color-mix(..., cat-agents 5%))
padding: 16px 22px
border-radius: 0 8px 8px 0
font-style: italic
```

### Cross-Reference (`a.crossref`)
```css
background: color-mix(in srgb, var(--cat-claude) 15%, transparent)
color: var(--cat-claude)
padding: 1px 7px
border-radius: 4px
/* Hover: vollfarbig */
```

### Timestamp-Link (`a.timestamp-link`)
```css
background: color-mix(in srgb, var(--cat-agents) 18%, transparent)
color: var(--cat-agents)
font-family: 'JetBrains Mono'
font-size: 13px
```

## Animationen

- **Transitions:** `0.18s ease` als Standard
- **Hover-Lift:** `transform: translateY(-2px)` für Karten
- **Keine Auto-Play-Animationen** — nichts soll Lesefluss stoeren
- **D3-Knowledge-Graph:** Force-Simulation laeuft natürlich aus

## Icons

**Emoji** statt SVG-Icon-Set:
- 📖 Wissensbuch
- 🎯 Lesepfade
- 🕸️ Konzept-Wiki
- 📅 Timeline
- 📺 Quellen / Videos
- ⏱ Lesezeit
- 🏷 Tags
- 🔗 Cross-Refs
- 💬 Zitate
- 📊 Statistiken
- ⚡ Schnell-Einstieg

## Responsive Breakpoints

| Breite | Was passiert |
|--------|--------------|
| `> 1100px` | Volles 3-Spalten-Layout (Sidebar + Content + Aside) |
| `< 1100px` | Aside (Quellen) wird ausgeblendet |
| `< 768px` | Sidebar wird non-sticky, max-height 300px |

## Accessibility

- Kontrast-Ratio mindestens 4.5:1 (alle Text-Hintergrund-Kombinationen geprüft)
- Keine reine Farb-Indikation (Icons + Farbe + Text)
- Tab-Navigation funktioniert
- Modal-Schließen via `Esc`-Taste
- Klick-Targets mindestens 32x32px

## Lese-Erfahrung (Prio 1)

- Zeilenlaenge max **~70 Zeichen** (Content max 820px bei 16.5px Font)
- Zeilenhöhe **1.72** im Body
- Absatz-Abstand `0 0 16px` (atmungsaktiv)
- Blockquotes haben spuerbar mehr Padding (16px 22px) — kein Quetsch-Layout
