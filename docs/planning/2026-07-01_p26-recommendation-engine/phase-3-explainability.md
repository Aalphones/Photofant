# Phase 3 — Explainability „Warum? / Warum nicht?"

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt (Explainability-Payload, geteilt mit P25)
- Konzept Dok 050 §10, Dok 040 §12, Konzept-ADR-007 (Explainability Pflicht)
- Phase 1/2: Reason-Chain, `why-not`, Karten · **P25 Phase 3:** Explainability-Eintrag der Korrekturen
- Bestand: Popover/Tooltip-Muster (`ui/`), `features/galerie/lightbox/`

## AK
- [ ] Zu jeder Empfehlung über ein kleines Symbol „Warum?": verwendete Signale, Confidence/Score, Job, ggf. Modell/Capability (Dok 050 §10).
- [ ] „Warum nicht?" für ein nicht empfohlenes Bild (nutzt `why-not`) — erklärt fehlende/unterschwellige Signale.
- [ ] **Dasselbe** Element erklärt auch die P25-Korrekturen (Grund, Quelle=user, Zeit, Job) — kein zweites Implementat.
- [ ] Dezent (kleines Symbol, Popover), kein Dauer-Sichtbares, kein Chat.

## Umsetzung
- [ ] Wiederverwendbares Explainability-Popover (nimmt die geteilte Payload aus Phase 1)
- [ ] Anbinden an: Empfehlungs-Karten (Warum?) + Nicht-empfohlen (Warum nicht?) + P25-Korrektur-Einträge
- [ ] `services/` um `why-not`-Call
- [ ] Doc: `docs/code-map.md`
- [ ] **Gesamt-P26:** finale AK + Smoke-Checkliste der README gegenprüfen — **MVP + Recommendation komplett**
