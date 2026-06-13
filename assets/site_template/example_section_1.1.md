---
section_id: "1.1"
title: "Was sich in 90 Tagen geändert hat"
chapter: "Die neue KI-Landschaft 2026"
chapter_number: 1
tier: "mittel"
word_count: 900
read_minutes: 5
sources: ["lHU6jFHWAkM", "Yob3R9Kb4vg", "ui2418ZlUYM", "Rg7lvSakZpE", "bKK0GP8OXlo"]
---

# 1.1 Was sich in 90 Tagen geändert hat

⏱ 5 Min Lesezeit · 🎯 Mittel-Thema · 🏷 Einstieg in die Landschaft 2026

Drei Monate sind in der KI-Welt eine Aera. Wer im März 2026 in einen Tiefschlaf gefallen wäre und Mitte Juni wieder aufwachen würde, würde sich verlaufen: Anthropic hat Open AI bei der Bewertung überholt, Opus ist im dritten Sprung von 4.6 über 4.7 zu 4.8, China senkt Open-Source-Preise um 75 Prozent, humanoide Roboter packen in Rossmann-Logistikzentren Pakete und bekommen in Shenzhen alle 15 Minuten ein Schwester-Exemplar an die Seite gestellt. Es ist nicht ein Update, das die Landschaft verschoben hat — es sind fuenf parallele Erdbeben. Wer nur eines davon mitbekommen hat, hat die neue Lage noch nicht gesehen. Diese Sektion ordnet die Verschiebungen so, dass du danach weißt, wo wir am 11. Juni 2026 wirklich stehen.

## Der Opus-Sprung von 4.6 über 4.7 zu 4.8

Im April 2026 launcht Anthropic Opus 4.7 — und es ist kein gewöhnliches Update. Der gleiche Listenpreis wie 4.6 (5 Dollar Input, 25 Dollar Output pro Million Token), aber ein Reasoning-Level namens "X High", ein neuer Tokenizer und ein 1-Million-Token-Kontextfenster. Auf der Vending Bench 2, einer Simulation, in der das Modell ein Jahr lang autonom einen Getraenkeautomaten betreibt, erreicht 4.7 rund 10.937 Dollar Endkontostand gegenüber 8.000 Dollar bei 4.6 — ein Sprung von 36 Prozent.

Doch der Hype verpufft schnell. Die Community kritisiert den Rushed Release, das aufgezwungene "Adaptive Thinking" und gewachsene Restriktionen. Sechs Wochen später, Ende Mai, kommt Opus 4.8 als Korrektur. Es ist ehrlicher, erkennt eigene Fehler viermal besser und bringt einen Ultramode plus Dynamic Workflows, mit denen Hunderte Agenten selbst orchestriert werden. Kim Isenberg ordnet den Release ernuechtert ein:

> "Aber und das gehoert zur Ehrlichkeit dazu, ich habe da ehrlich gesagt gerade meine Zweifel ein wenig dran. (...) Für mich war es ein Good-Dish Release, aber nicht der Sprung, den ich mir ehrlich gesagt erhofft habe."
>
> — *Es ist hochgefährlich, was hier beginnt* ([▶ 03:24](video:ui2418ZlUYM?t=204))

Bezeichnend ist auch, was nicht passiert: Sonnet bleibt unverändert, Haiku seit 4.5 still. Anthropic richtet sich konsequent auf den professionellen Markt aus. Welches Modell wofür taugt, vertieft [[3.1 Modell-Evolution]].

## Agentic Workflows werden Standard-Modus

Was im Dezember 2025 noch Experiment war, ist im Juni 2026 Default. Anthropic launcht **Cloud Routines** — wiederkehrende Aufgaben laufen auf Anthropics Cloud, nicht mehr auf deinem Laptop. **Managed Agents** bekommen Multi-Agent-Sessions und Webhook-Integration. Und mit **Agent View** ist die Unübersichtlichkeit von fuenf bis zehn parallel offenen Terminal-Tabs Geschichte: Eine einzige Session orchestriert beliebig viele Subagenten — Titel-Generator, Blogpost-Skill, LinkedIn-Post-Skill, Instagram-Story-Skill, alles parallel, alles steuerbar per Leertaste.

Das ist mehr als Komfort. Es ist die Marktwende, vor der Make und n8n stehen — und die im Newscast offen ausgesprochen wird:

> "Make versteht ihr diesen fundamentalen Schift, den ich ja schon vor mehreren Monaten hier (...) angepriesen habe, wofür ich auch angefeindet wurde. (...) Es ist doch vollkommen offensichtlich, dass wir über Agenten Workflows bauen und eben direkt über das CLI."
>
> — *DAS kommt NACH KI-Agenten* ([▶ 22:41](video:bKK0GP8OXlo?t=1361))

Der visuelle Workflow-Builder wird zur Nische, das CLI mit Subagenten zur Norm. Wie genau dieser Bruch funktioniert, behandelt [[2.1 Was Claude Code wirklich ist]].

## Anthropic überholt Open AI bei der Bewertung

Ende Mai 2026 sammelt Anthropic 65 Milliarden Dollar bei einer Bewertung von 965 Milliarden ein — und zieht damit erstmals an Open AI vorbei. Die Run-Rate springt von 9 Milliarden Dollar Ende 2025 auf 30 Milliarden im April 2026, eine Verdreifachung in vier Monaten. Open AI liegt offiziell bei etwa 25 Milliarden, bilanziert aber nach der Nettomethode. Damit ist der Vergleich nicht so eindeutig, wie es Schlagzeilen suggerieren — aber das Momentum ist klar.

Das eigentliche Nadeloehr heißt Compute. Laut Dylan Patel von SemiAnalysis braeuchte Anthropic bis Ende 2026 mehr als 5 Gigawatt Inferenzkapazitaet, committed sind erst 2 Gigawatt. Das führt zu spuerbaren Konsequenzen:

> "Rechenleistung ist im Moment also einfach alles und Anthropic hat einfach nicht genug davon und genau deshalb wird die Opus Performance gerade einfach degradiert."
>
> — *Opus 4.7: Ist es VORBEI für Claude?* ([▶ 14:32](video:Yob3R9Kb4vg?t=872))

Der Broadcom-Google-TPU-Deal über 3,5 Gigawatt greift erst 2027. Bis dahin ist die Luecke der Schauplatz des gesamten Wettkampfs. Wer im Frontrunner-Rennen wirklich vorne liegt, klärt [[1.3 Wer ist wirklich vorne]].

## China senkt Preise — und baut ein Hardware-Imperium

Während im Westen der Compute-Engpass die Margen frisst, öffnet China die Schleusen. Open-Source-KI-Preise fallen um 75 Prozent. ByteDance — die Mutter von TikTok — baut erstmals eine eigene CPU, um sich von Engpaessen zu lösen. Nvidia kontert mit "ViRA", einer CPU, die laut ersten Benchmarks Intel und AMD schlagen soll. Der Hintergrund: Agenten-Workflows sind nicht mehr nur GPU-lastig.

> "Du hattest das vorhin gesagt, Leo, mit dem Dynamic Workflow bei Anthropic, da hast du Agents, Subagents und das muss alles orchestriert werden. (...) Und das macht nicht die GPU, sondern das macht die CPU."
>
> — *Es ist hochgefährlich, was hier beginnt* ([▶ 39:21](video:ui2418ZlUYM?t=2361))

Gleichzeitig vergibt China als erstes Land digitale Personalausweise für humanoide Roboter — über 28.000 Stück sind bereits registriert. Auf der Fertigungsseite öffnet Unitree eine Fabrik, die alle 15 Minuten einen Humanoiden vom Band laufen lässt (Jahresziel 10.000 Stück). Genesis AI liefert Simulationen, die 430.000-mal schneller als Echtzeit Trainingsdaten erzeugen — bei 89 Prozent Übereinstimmung mit echten physischen Tests. Boston Dynamics' Atlas balanciert im Rabona, Figure AI löst mit induktiver Fusssohlen-Ladung das Schichtbetrieb-Problem, Rossmann testet im Logistikzentrum Burgwedel den Walker S2 als erstes europaeisches Live-Pilotprojekt. KI ist nicht länger nur Software. Sie hat Beine bekommen — und Adressen. Die Player-Karte der Big Three entfaltet [[1.2 Die Big-Three]].

## Was du jetzt konkret damit anfangen kannst

Drei Konsequenzen ziehen sich aus diesen 90 Tagen. **Erstens:** Halte deine Modellwahl beweglich. Opus 4.8 ist nicht automatisch besser für jeden Anwendungsfall als 4.6 — gerade bei Benchmarks wie der Vending Bench liegt es hinter GPT 5.5 und sogar 4.7, weil es ehrlicher agiert. Lies Releases nicht als Sprung, sondern als Trade-off. **Zweitens:** Wenn du noch in Make oder n8n Workflows bastelst, plane den Umzug aufs CLI. Agent View, Subagents und Managed Agents sind keine Spielerei — sie sind das neue Operating Model für wiederkehrende Arbeit. **Drittens:** Beobachte China nicht aus Distanz. Ob CPU-Rennen, Roboter-IDs oder Open-Source-Preisstürze — die nächste Schicht der KI-Landschaft entsteht dort, wo Hardware, Daten und Modell zusammenfallen. Wer nur westliche Releases tracked, sieht die Haelfte der Karte nicht.

---

## 📺 Quellen dieser Sektion

- **Claude Opus 4.8: DIESE 7 Dinge ändern jetzt ALLES!** (25 min, 48k Views)
  → lHU6jFHWAkM
- **Opus 4.7: Ist es VORBEI für Claude?** (38 min, 74k Views)
  → Yob3R9Kb4vg
- **"Es ist hochgefährlich, was hier beginnt!" Die neue KI-Jobluege** (117 min, 36k Views)
  → ui2418ZlUYM
- **KI-News: Claude verbessert sich IM SCHLAF!** (33 min, 44k Views)
  → Rg7lvSakZpE
- **KI-News: DAS kommt NACH KI-Agenten!** (27 min, 41k Views)
  → bKK0GP8OXlo

## 🔗 Verwandtes Wissen

- [[1.2 Die Big-Three]] — Die Player-Karte 2026
- [[1.3 Wer ist wirklich vorne]] — Der ehrliche Vergleich
- [[2.1 Was Claude Code wirklich ist]] — Vom Tool zum Betriebssystem
- [[3.1 Modell-Evolution]] — Opus, Sonnet, Haiku im Detail

---

## 📎 Quick-Reference (Marginalia)

[^firma:anthropic]:
  Anthropic · KI-Lab San Francisco · macht Claude
  Mai 2026 erstmals höher bewertet als OpenAI

[^firma:openai]:
  OpenAI · KI-Lab San Francisco · macht ChatGPT und Codex
  Februar 2025 noch 90% Business-Marktanteil

[^zahl:opus-preis]:
  - 5 USD Input / 25 USD Output pro Million Token
  - Unverändert seit Opus 4.6

[^zahl:vending-bench-4-7]:
  - 10.937 USD Endkontostand (Opus 4.7)
  - 8.000 USD (Opus 4.6)
  - +36% Verbesserung

[^zahl:china-preissenkung]:
  - 75% Preissenkung bei Open-Source-KI-Modellen
  - China · Mai 2026

[^begriff:vending-bench]:
  Simulation: Modell betreibt 1 Jahr autonom einen Getränkeautomaten.
  Misst Reasoning, Geduld, langes Planen.

## 📈 Drei-Modell-Sprung

{{viz:evolution|versions=Opus 4.6,Opus 4.7,Opus 4.8|notes=Basis Frühjahr,+36% Vending Bench,Dynamic Workflows + UltraCode}}

{{viz:compare|title=Business-Marktanteil KI-Modelle|items=Februar 2025 ChatGPT:90,Juni 2026 Claude:70,Juni 2026 GPT-5.5:25,Juni 2026 Gemini:5}}
