# P10 · Phase 3 — Caption-Tools & Near-Dupes

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (captions-Action, duplicates)
- [Konzept](../../Konzept-Photofant.md) §9 (Caption-Tools, Near-Dupe-Vergleich)
- `docs/design/js/compare.jsx` (Links-Rechts-Vergleich)

## Akzeptanzkriterien

- Set-weite Caption-Aktionen: Trigger-Word voranstellen, Prefix/Suffix anhängen, Find-Replace — wirken auf `caption_override` (Original-Captions der Galerie bleiben unberührt), mit Vorher/Nachher-Vorschau (Stichprobe) vor dem Ausführen.
- Near-Dupe-Endpoint (pHash-Paare im Set, Schwelle einstellbar) + Links-Rechts-Review-UI: pro Paar links/rechts/beide behalten; Verworfene → Papierkorb (P2-Strecke).
- Beide Strecken über die Queue (große Sets), Fortschritt sichtbar.

## Checkliste

- [ ] captions-Action-Endpoint (4 Aktionen, idempotent formuliert: Trigger-Word nicht doppelt voranstellen)
- [ ] Vorschau-Dialog (5 Beispiel-Captions vorher/nachher)
- [ ] Dupe-Paar-Endpoint + Review-UI (Vergleich, Tastatur: ←/→/B)
- [ ] Doc-Update: routes.md

## Report-Back
