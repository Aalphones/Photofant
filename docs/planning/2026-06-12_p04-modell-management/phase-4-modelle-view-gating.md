# P4 · Phase 4 — Modelle-View & Gating

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Status, Capabilities)
- [docs/design/README.md](../../design/README.md) — Modelle-View; `docs/design/js/models.jsx`, `models-dialogs.jsx`, `docs/design/models.css`
- [Konzept](../../Konzept-Photofant.md) §12.1 (Gating), §12.2a (Meldungs-Muster)

## Akzeptanzkriterien

- Modelle-View nach Prototyp: Tier-Gruppen (Core/Optional/Generierung als leere Gruppe mit „kommt später"-Hinweis), Karten mit Status-Badge, Inline-Drawer mit Details.
- Download-Dialog (Lizenz-Ack falls nötig, Fortschritt) + Bind-Dialog (Pfad-Eingabe/Picker, Validierungs-Fehler inline mit den §12.2a-Meldungen).
- `models_dir`-Picker in den Einstellungen (PathRow-Pattern).
- Gating wirkt: `settings`-Slice hält Capabilities; gegatete Features zeigen Hinweis + Link zur Modelle-View statt toter Buttons.
- Erstnutzer-tauglich: Ein leerer Modell-Bestand erklärt sich selbst (was ist ein Modell, warum brauche ich es, ein Klick zum Default-Setup „Core-Modelle laden").

## Checkliste

- [ ] `store/settings/` (Modelle, Capabilities, Config) + ModelService
- [ ] Modelle-View (Gruppen, Karten, Badges, Drawer)
- [ ] Download-Dialog + Bind-Dialog (Fehlerdarstellung: Meldung + ausklappbares Detail)
- [ ] „Core-Setup"-Sammelaktion (alle fünf Core-Modelle nacheinander laden)
- [ ] Gating-Direktive/Komponente für Feature-Hinweise (wiederverwendbar für P5–P9)
- [ ] Doc-Update: routes.md, README Features-Stand

## Report-Back
