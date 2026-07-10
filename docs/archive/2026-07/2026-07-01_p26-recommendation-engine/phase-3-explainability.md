# Phase 3 — Explainability „Warum? / Warum nicht?"

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Kontrakt (Explainability-Payload, geteilt mit P25)
- Konzept Dok 050 §10, Dok 040 §12, Konzept-ADR-007 (Explainability Pflicht)
- Phase 1/2: Reason-Chain, `why-not`, Karten · **P25 Phase 3:** Explainability-Eintrag der Korrekturen
- Bestand: Popover/Tooltip-Muster (`ui/`), `features/galerie/lightbox/`

## AK
- [x] Zu jeder Empfehlung über ein kleines Symbol „Warum?": verwendete Signale, Confidence/Score, Job, ggf. Modell/Capability (Dok 050 §10). — Job/Modell entfallen mangels Datenbasis (Recommendation-Cache hat keine `job_id`-Spalte; kein Fake-Wert, siehe Deviation).
- [x] „Warum nicht?" für ein nicht empfohlenes Bild (nutzt `why-not`) — erklärt fehlende/unterschwellige Signale. Angebunden an die „Ähnliche Bilder"-Rail (P36) — genau die Bilder, bei denen sich „warum nicht empfohlen?" natürlich stellt.
- [x] **Dasselbe** Element erklärt auch die P25-Korrekturen (Grund, Quelle=user, Zeit, Job) — kein zweites Implementat. Lore-Panel-Bio zeigt „Warum geändert?" sobald `owner === 'user'`, gespeist aus `getChangelog`.
- [x] Dezent (kleines Symbol, Popover), kein Dauer-Sichtbares, kein Chat.

## Umsetzung
- [x] Wiederverwendbares Explainability-Popover (`ui/explainability-popover/`) — generisches `{title, confidencePercent, reasons[], missing[], meta[]}`-Payload, kein eigener HTTP-Call (Aufrufer füttert `payload`/`loading`, steuert `open`).
- [x] Anbinden an: Empfehlungs-Karten (Warum?, Payload synchron aus dem schon geladenen Score/Reasons) + „Ähnliche Bilder"-Karten (Warum nicht?, live via `why-not`, pro Zielbild gecacht) + Lore-Panel-Korrektur (Warum geändert?, via Changelog).
- [x] `services/recommendation.service.ts` um `whyNot()`-Call.
- [x] Doc: `docs/code-map.md`.
- [x] **Gesamt-P26:** finale AK + Smoke-Checkliste der README gegenprüfen — **MVP + Recommendation komplett**

## Deviations
- **Kein Job-Feld am Empfehlungs-Popover:** `recommendation_cache` hat keine `job_id`-Spalte (Phase 1), `why-not` rechnet synchron ohne Job. Statt eines erfundenen Werts bleibt `meta` dort leer — nur die Korrektur-Historie (die echte `job_id` aus dem Changelog hat) füllt `meta`. Kein Kontraktbruch (`job` war „ggf.").
- **Positionierung als `position: fixed` statt `absolute`:** die Empfehlungs-/Ähnliche-Bilder-Rail steht in einem `overflow-x: auto`-Streifen, der jeden `absolute`-Overflow abgeschnitten hätte (CSS-Spezialfall: `overflow-x: auto` erzwingt `overflow-y: auto`). Popover berechnet seine Position aus der Trigger-BoundingRect.
- **„Warum nicht?" an der P36-Rail statt eigenem Bild-Picker:** AK nennt „ein nicht empfohlenes Bild", ohne UI-Weg festzulegen. Die „Ähnliche Bilder"-Karten (CLIP-ähnlich, aber ggf. nicht in den Top-Empfehlungen) sind der natürliche Ort dafür — kein zusätzlicher Picker-Dialog nötig.
