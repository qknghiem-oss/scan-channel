---
section_id: "2.1"
title: "Was Claude Code wirklich ist"
chapter: "Claude Code — Das neue Betriebssystem für Wissensarbeit"
tier: "mega"
word_count: 1400
read_minutes: 7
sources: ["Lu95f1ZBIos", "9nnsszlfE0w", "yOFb95LgnoM", "U07CLU73PEc"]
---

# 2.1 Was Claude Code wirklich ist

⏱ 7 Min Lesezeit · 🎯 Mega-Thema · 🏷 Anfänger bis Fortgeschritten

Im Dezember 2025 funktionierten Coding-Agenten "praktisch nicht". So formuliert es [Andrej Karpathy][^person:andrej-karpathy] — und genau dieser Satz ist der Schlüssel zum Verständnis dessen, was sich seitdem verändert hat. Drei Monate später, im März 2026, schreibt derselbe Mann, man programmiere "99% des Codes nicht mehr selbst, sondern orchestriert Agenten". Dazwischen liegt das, was [Leonard Schmedding][^person:leonard-schmedding] im Vortrag den **Claude Code Moment** nennt: jener Augenblick, in dem ein Werkzeug zur Stille aufruckt und plötzlich nicht mehr nur Software baut, sondern Arbeit erledigt. Wer Claude Code im März 2026 noch für einen "besseren Copilot" hält, hat den entscheidenden Sprung verpasst. Genau diesen Sprung schauen wir uns jetzt an.

## Vom Copilot zum Agent — der konzeptionelle Sprung

Die meisten Menschen sind gedanklich noch in einer Welt, in der KI ein Vorschlagsautomat war. Du tippst, sie ergänzt. Du fragst, sie antwortet. Schmedding bringt diese alte Welt im Vortrag pointiert zu Grabe:

> "Coding Agenten funktionierten vor Dezember praktisch nicht. Und das ist jetzt halt wichtig gedanklich zu verstehen, weil viele immer noch gedanklich vor ein paar Monaten sind, wo sie gesagt haben, ja, das hat nicht funktioniert. Ich habe da schon mal Dokumente erstellen wollen, Präsentation. Ja, am Ende war schneller, wenn ich selber gemacht habe. Das gibt es nicht mehr."
>
> — Leonard Schmedding (Zitat Karpathy), *Der Claude Code Moment* ([▶ 11:44](video:yOFb95LgnoM?t=704))

Daraus folgt: Wer seine Einschätzung von Claude Code aus dem Sommer 2025 stehen lässt, urteilt über ein Produkt, das es so nicht mehr gibt. Die entscheidende Veränderung ist keine Schnelligkeitsfrage und keine Frage besserer Autovervollständigung. Es ist eine Wesensverschiebung. Aus einem Assistenten, der antwortet, wird ein Agent, der **handelt** — der Dateien anlegt, Browser öffnet, APIs aufruft, eigene Subagenten startet und Ergebnisse zurück integriert. Anders gesagt: Du delegierst nicht mehr Sprach-Arbeit an ein Modell, du delegierst **Vorgänge** an ein System.

Anthropic selbst hat diesen Sprung in Zahlen sichtbar gemacht. Im Tutorial-Video erklärt der Autor, dass das gesamte Growth-Marketing-Team von Anthropic über zehn Monate aus einer einzigen Person bestand — diese eine Person hat mit Claude Code allein "bezahlte Social Media und Google Werbung, App Stores, E-Mail Marketing sowie SEO für das 380 Milliarden Dollarunternehmen betrieben". Das ist kein Marketing-Stunt, sondern der greifbare Beweis dafür, was sich konzeptionell verändert hat: Claude Code ist nicht länger Werkzeug **am Rand** der Arbeit, sondern das Betriebssystem **für** die Arbeit selbst. Wer das verstehen will, muss die zugrundeliegende Formel verstehen.

## Die Formel: Agent = Modell + Harness

Im Vortrag beschreibt Schmedding eine ganz konkrete Beobachtung, die im März 2026 durch die KI-Szene wanderte: das Phänomen rund um das Open-Source-Projekt **Open Claw**. Es übertraf in Stern-Bewertungen sogar React und Linux — ohne eigentlich eine technische Innovation zu sein. Warum? Schmedding analysiert es so:

> "Das was uns OpenCla gezeigt hat, ist, dass die Macht oder die Stärke von KI liegt nicht im Modell, also im ChatGPT, in Cloud Modellen, sondern um dem, was wir drumherum bauen. Also dem Kontext, den wir mitgeben."
>
> — Leonard Schmedding, *Der Claude Code Moment* ([▶ 5:04](video:yOFb95LgnoM?t=304))

Damit ist die zentrale Formel des gesamten Kapitels ausgesprochen: **Agent = Modell + Harness**. Das Modell (Opus, Sonnet, Haiku) liefert Sprache und Reasoning. Aber der eigentliche Hebel liegt im [**Harness**][^begriff:harness] — also im Gerüst aus Dateien, Regeln, Tools, Skills, MCP-Servern und Hooks, das du um das Modell herum baust. Im Tutorial wird das auf eine fast lehrbuchhafte Faustregel verdichtet: **"Was der Agent nicht sehen kann, existiert für ihn nicht."** Alles, was der Agent wissen muss, muss als Datei in seinem Arbeitsbereich liegen — nicht in deinem Kopf, nicht in einer Slack-Nachricht, nicht in der Mail. Daraus folgt eine zweite, ebenso wichtige Faustregel aus demselben Video:

> "Frag nicht, warum der Agent scheitert, frag, welche Fähigkeit ihm fehlt."
>
> — *Automatisiere ALLES mit Claude Code* ([▶ 11:38](video:Lu95f1ZBIos?t=698))

Das ist ein vollständiger Mindset-Shift. Wenn Claude etwas falsch macht, ist die Antwort nicht ein besserer Prompt, sondern eine bessere Umgebung. Du gibst dem Agenten ein neues Tool, eine neue Regel, eine neue Referenzdatei. Das ist die Brückensteinleger-Logik, die Mitchell Hashimoto (HashiCorp-Gründer) sinngemäß so beschreibt: Jeder Fehler wird zur Gelegenheit, eine Lösung einzubauen, sodass dieser Fehler nie wieder passiert. In dieser Logik ist Claude Code kein Chatbot — es ist ein **lernender Prozess**, der mit jedem Reibungspunkt stärker wird. Wer die Tiefe dieses Prinzips erkunden will, findet sie in [[2.2 Die 5 Prinzipien des Context Engineering]].

## Warum "Coding" nur die halbe Wahrheit ist

Der Name Claude **Code** ist irreführend — und Anthropic gibt das mittlerweile offen zu. Im Tutorial heißt es wörtlich:

> "Anthropic, das Unternehmen hinter Claude, hat selbst nicht damit gerechnet, dass nicht nur Softwareentwickler ihr Limit Claude Code dramatisch vereinfachen, sondern dass gerade Nicht-Programmierer wie Juristen, Marketer, Designer und Wissensarbeiter damit Dinge bauen, die vorher ein ganzes Entwicklerteam erfordert hätten."
>
> — *Automatisiere ALLES mit Claude Code* ([▶ 0:00](video:Lu95f1ZBIos?t=0))

Anders gesagt: Wer Claude Code mit "ist nur was für Entwickler" abtut, missversteht das Werkzeug fundamental. Im Video wird das praktisch vorgeführt: ein **Website-Audit-Skill**, der vor einem Sales-Meeting in Minuten eine fremde Unternehmenswebsite auseinandernimmt; ein **Google-Workspace-CLI**, das E-Mails liest, Google Docs anlegt, Slides erstellt; **Excel- und PowerPoint-Skills**, die über ein Add-In direkt in den Microsoft-Apps leben und einen "Shared Context" zwischen beiden Programmen herstellen. Im Update-Video formuliert es der Autor so:

> "Beide Apps, Excel und PowerPoint, teilen sich über dieses Add-in einen gemeinsamen Kontext. Das heißt, eine PowerPoint Datei, ich lasse diese jetzt hier gerade von Claude erstellen, sollte den gleichen Kontext haben wie das, was du hier in Excel mit Claude schreibst."
>
> — *Vergiss ChatGPT, Claude Code ist nicht mehr einzuholen* ([▶ 20:47](video:9nnsszlfE0w?t=1247))

Was bedeutet das praktisch? Du kannst eine Vergleichsmatrix in Excel anlegen lassen — und ohne weiteren Prompt entsteht aus demselben Kontext eine passende PowerPoint-Präsentation. Du kannst Skills im Unternehmen teilen: ein Branding-Skill, der vor jeder Kundenpräsentation drüber laeuft. Ein finaler Check, der jede Slide vor der Freigabe validiert. Wiederkehrende Prozesse werden über standardisierte Skills genormt — direkt in den Tools, in denen Wissensarbeiter ohnehin sitzen. Genau das ist der Überbau, den [[2.4 Die 44 versteckten Features]] im Detail aufschlüsselt.

Und dann sind da noch die **MCP-Server** — das Model Context Protocol, von Anthropic selbst entwickelt. Damit verbindet sich Claude Code mit Figma, Slack, Notion, Canva, Trello — oder, über den Playwright-MCP, mit dem Browser selbst, um Designanalysen durchzuführen, für die keine API existiert. Coding war der Türsteher. Was dahinter beginnt, ist Knowledge Work in Reinform.

## Was 99% nicht verstehen — der Claude Code Moment für Unternehmen

Karpathy nennt das Geschehen "ein Erdbeben der Stärke 9 — da hält kein deutsches Haus stand". Schmedding übersetzt das für Unternehmen: Wer heute Prozesse plant, ohne Agenten mitzudenken, baut für eine Welt, die es bald nicht mehr gibt. Sein Schlüsselsatz im Vortrag:

> "Du darfst nicht mehr nur an den Menschen denken, sondern musst du auch daran denken, wie optimiere ich das gleich für Agenten oder Agententeams in meinem Unternehmen mit. (...) Kompatibilität für das Agentenzeitalter ist jetzt die wichtigste Grundlage. Ohne saubere API und strukturierte Daten verliert man den Anschluss."
>
> — Leonard Schmedding, *Der Claude Code Moment* ([▶ 15:22](video:yOFb95LgnoM?t=922))

Die Zahlen geben ihm Recht. Im Februar 2025 hielt ChatGPT noch 90% Marktanteil im Business-Segment. Ein Jahr später liegt Claude bei rund 70%. Anthropics Umsatz schoss von 1 Milliarde im Dezember 2024 auf 19 Milliarden im März 2026 — schneller als bei jedem Unternehmen der Geschichte. Allein Claude Code kommt auf eine Run-Rate von 2,5 Milliarden Dollar. 70% der Fortune-100-Unternehmen nutzen es. Microsoft — die Firma hinter GitHub Copilot — setzt es intern ein und hat mit "Microsoft GPT Cowork" einen Wrapper darum herum veröffentlicht. Die Produktivitätssteigerung liegt im Schnitt bei 50%. Der sogenannte **Unlocked-Work-Effekt** sorgt dafür, dass 27% aller Aufgaben, die Mitarbeiter mit Claude erledigen, ohne KI **schlicht nicht gemacht worden wären**. Das ist nicht Effizienz — das ist neuer Output, der vorher gar nicht existierte. Wer diesen Hebel jetzt ignoriert, ignoriert nicht ein Tool. Er ignoriert eine neue Wertschöpfungsklasse. Die Tiefe dieser Verschiebung für Organisationen entfaltet [[2.5 Der Claude Code Moment für Unternehmen]].

## Was du jetzt konkret damit anfangen kannst

Drei Dinge sind ab heute praktisch wichtig. **Erstens:** Hoer auf, Claude Code als Chat zu denken. Denk es als Arbeitsumgebung. Jede Datei in deinem Projektordner ist Teil des Agenten. Was nicht im Workspace liegt, existiert für ihn nicht. **Zweitens:** Wenn etwas nicht klappt, frag nie zuerst nach einem besseren Prompt. Frag, welche Fähigkeit der Agent nicht hat — ein Skill, eine Regel, eine Referenzdatei, ein MCP-Server. Genau dieser Reflex trennt produktive Nutzer von frustrierten. **Drittens:** Beginn klein, aber realistisch. Ein Website-Audit vor dem nächsten Kundentermin. Ein wiederkehrender Bericht, der direkt im Google Workspace landet. Eine Excel-Tabelle, aus der per geteiltem Kontext eine PowerPoint wird. Jeder dieser Mini-Workflows zeigt dir live, wo der Sprung vom Copilot zum Agenten passiert — und warum Schmedding mit seinem Befund recht hat: Wer Claude Code nur als bessere Antwortmaschine begreift, hat den Sprung nicht verstanden. Die nächsten Sektionen geben dir das Methoden- und Feature-Gerüst, um den Sprung selbst zu vollziehen.

---

## 📺 Quellen dieser Sektion

- **Automatisiere ALLES mit Claude Code: Das ultimative Tutorial** (134 min, 167k Views)
  → Lu95f1ZBIos
- **Vergiss ChatGPT, Claude Code ist nicht mehr einzuholen!** (31 min, 88k Views)
  → 9nnsszlfE0w
- **Der Claude Code Moment: DAS müssen Unternehmen jetzt machen!** (39 min, 37k Views)
  → yOFb95LgnoM
- **KI-Agenten: DAS übersehen gerade ALLE!** (46 min, 34k Views)
  → U07CLU73PEc

## 🔗 Verwandtes Wissen

- [[2.2 Die 5 Prinzipien des Context Engineering]] — Die Methodik dahinter
- [[2.3 Die Evolution in 90 Tagen]] — Was sich konkret verändert hat
- [[2.4 Die 44 versteckten Features]] — Skills, MCPs, Hooks im Detail
- [[2.5 Der Claude Code Moment für Unternehmen]] — Was Organisationen jetzt tun müssen
- [[5.1 Claude Code vs. Codex]] — Der direkte Vergleich

---

## 📎 Quick-Reference (Marginalia)

[^person:leonard-schmedding]:
  Leonard Schmedding · Gründer Everlast AI
  Host des Channels, Vortragender

[^person:andrej-karpathy]:
  Andrej Karpathy · Ex-AI-Director Tesla, Mitgründer OpenAI

[^begriff:harness]:
  - Gerüst aus Dateien, Regeln, Tools, MCP-Servern und Hooks
  - Bestimmt was der Agent "sehen" und tun kann
  - Siehe [[2.2 Die 5 Prinzipien des Context Engineering]]

[^tool:claude-code]:
  - Anthropics KI-Coding-Agent (autonom, nicht nur Copilot)
  - Run-Rate 2.5 Mrd. USD
  - 70% der Fortune-100 nutzen es

[^zahl:claude-marktanteil]:
  - 70% Business-Marktanteil (vorher 90% ChatGPT)
  - Anthropic-Umsatz: 19 Mrd USD (März 2026, zuvor 1 Mrd. Dezember 2024)

## 📈 Drei-Monats-Sprung visualisiert

{{viz:evolution|versions=Dez 2025,März 2026,Juni 2026|notes=funktioniert praktisch nicht,Claude Code 2.0,Dynamic Workflows + 70% Marktanteil}}

{{viz:compare|title=Business-Marktanteil KI-Modelle (Juni 2026)|items=Claude:70,GPT-5.5:25,Gemini:5}}
