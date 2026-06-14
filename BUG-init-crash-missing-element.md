# Bug: Ein fehlendes optionales DOM-Element bricht den gesamten Buch-Render

**Status:** offen → Fix in diesem Commit (defensiver Guard)
**Betroffen:** `assets/site_template/assets/app.js` (`bindUsecaseSearch`), Frontend-Boot
**Schweregrad:** hoch (whitescreen — das ganze Wissensbuch rendert nicht)
**Entdeckt:** 2026-06-14, bei einem Deployment aus diesem Skill

## Symptom

Die App zeigt nur eine Fehlerkarte statt des Buchs:

```
⚠️ Fehler beim Laden
TypeError: Cannot read properties of null (reading 'addEventListener')
    at bindUsecaseSearch (app.js:1886:7)
    at init (app.js:61:3)
    at loadData (app.js:39:5)
```

## Root Cause

`init()` ruft nacheinander viele `bind*()`-Funktionen auf (Z.61). `bindUsecaseSearch()` holt
zwei Elemente per `getElementById` und hängt **ohne Null-Prüfung** Listener an:

```js
function bindUsecaseSearch() {
  const input = document.getElementById("usecase-input");
  const btn   = document.getElementById("usecase-btn");
  // ...
  btn.addEventListener("click", runSearch);   // <-- wirft, wenn btn === null
```

Fehlt eines dieser **optionalen** Elemente (z.B. weil eine deployte `index.html` älter ist als
die `app.js` — Versions-Drift zwischen Template und Skript), wirft `null.addEventListener`. Da
der Aufruf ungeschützt in `init()` steht, **bricht der gesamte Render** — nicht nur das
Usecase-Such-Feature.

### Reproduktion
1. Eine `index.html` ohne `#usecase-input`/`#usecase-btn` ausliefern (z.B. ein älteres Deployment).
2. Das aktuelle `app.js` laden → Boot bricht mit obigem Stacktrace, Buch erscheint nie.

(Beobachtet an einem live laufenden Deployment, dessen `index.html` älter war als die `app.js`.)

## Fix (in diesem Commit)

Defensiver Early-Return in `bindUsecaseSearch()`:

```js
const input = document.getElementById("usecase-input");
const btn   = document.getElementById("usecase-btn");
if (!input || !btn) return;   // <-- optionales Feature, kein harter Abbruch
```

## Empfehlung (Folge-Härtung)

Alle `bind*()`-/`render*()`-Funktionen, die `getElementById(...).addEventListener` nutzen,
sollten ihre Elemente vorher auf `null` prüfen (oder `init()` sollte jeden Schritt in
`try/catch` kapseln), damit **ein** fehlendes optionales Element nie den kompletten Buch-Render
verhindert. Kandidaten u.a.: `bindModal`, `bindDeepDiveTab`, `bindPerVideoTabs`,
`bindPraxisCatFilter`.
