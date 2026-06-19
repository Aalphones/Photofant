# Phase 1 — Reconciliation-Sweep (Inventar)

> Rating: standard · Status: pending

Erzeugt die **verbindliche Abweichungsliste** über alle gebauten Views. Repariert nichts — liefert nur das Inventar, das Phase 2–4 steuert. Ohne diese Phase plant Phase 4 blind.

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, finale AK
- [docs/design/README.md](../../design/README.md) — Soll-Layouts aller 10 Views + Design-Tokens
- `docs/design/js/*.jsx` — die Prototyp-Quellen pro View (app, gallery, detail, models, albums, settings, review, training, import, relation, compare, dupecheck)
- [Konzept](../../Konzept-Photofant.md) — Voll-Spezifikation; **bei Widerspruch gewinnt das Konzept** (AGENTS.md), das Mockup ist die visuelle Referenz
- Implementierung: `frontend/src/app/shell/`, `frontend/src/app/features/*`, `frontend/src/app/ui/*`

## Akzeptanzkriterien

- `docs/design-reconciliation.md` angelegt. Tabelle mit **einer Zeile pro gebauter View**: Galerie, Lightbox/Detail, Shell (Nav/Top-Bar/Job-Dock/Bulk-Bar), Modelle, Alben, Personen, Trainingssets, Tags, Wartung, Einstellungen, Import-Dialog.
- Pro View festgehalten:
  - **Design-Status**: vorhanden (Mockup zeichnet den Screen) / nur Nav-Slot (Label ohne Entwurf) / fehlt
  - **Abweichungstyp**: keine / Design-missachtet / Design-Lücke-erfunden / sauber-verschoben (Backlog)
  - **Schweregrad** je konkretem Punkt: GROSS (ganze Komponente/Layout) / MITTEL (vereinfacht) / KLEIN (Detail)
  - **Belege**: `datei:zeile` auf beiden Seiten (Design + Impl)
- Jeder GROSS/MITTEL-Punkt der **übrigen** Views (alles außer Einstellungen & Tags — die haben eigene Phasen) bekommt einen getaggten Eintrag in `FINDINGS.md` → Phase 4.
- **Abgrenzung Backlog**: Was laut STATE.md/geparkten Plänen (P7 Personen, P8 Editor, P9, P10, ComfyUI) schlicht noch nicht gebaut ist, wird als „sauber-verschoben" markiert und **nicht** als Abweichung gezählt.

## Checkliste

- [ ] Sweep durchführen (Mockup + Konzept gegen Impl), View für View
- [ ] `docs/design-reconciliation.md` schreiben (Tabelle + pro View ein kurzer Abschnitt mit den konkreten Punkten)
- [ ] GROSS/MITTEL der übrigen Views als `→ Phase 4`-Findings taggen
- [ ] Einstellungen-Detailbefunde als `→ Phase 2`-Finding, Tags-Detailbefunde als `→ Phase 3`-Finding taggen
- [ ] Doc-Update: in `AGENTS.md` unter „Planung" einen Verweis auf `docs/design-reconciliation.md` setzen (Lebensdauer: bis Plan archiviert)

## Report-Back
