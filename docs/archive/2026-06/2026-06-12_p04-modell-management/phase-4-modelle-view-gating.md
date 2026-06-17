# P4 · Phase 4 — Modelle-View & Gating

> Rating: standard · Status: complete

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

- [x] `store/models/` (Modelle, Capabilities, Config) + ModelService
- [x] Modelle-View (Gruppen, Karten, Badges, Drawer)
- [x] Download-Dialog + Bind-Dialog (Fehlerdarstellung: Meldung + ausklappbares Detail)
- [x] „Core-Setup"-Sammelaktion (alle fünf Core-Modelle nacheinander laden)
- [x] Gating-Direktive/Komponente (`pf-gated-feature`) für Feature-Hinweise (wiederverwendbar für P5–P9)
- [x] Doc-Update: README Features-Stand

## Report-Back

**Abweichungen vom Plan:**
- `store/settings/` → `store/models/` (spezifischerer Name, konsistent mit anderen Slices)
- Slice-Benennungen: Slice-Ordner heißt `models/`, State-Interface `ModelsState`
- `models_dir`-Picker in Einstellungen: Text-Input statt nativer File-Picker (native Picker kommt mit Electron/Tauri-Integration in späterem Plan)
- Captioner-Settings-Dialog (aus Prototyp) nicht implementiert — `capabilities`-Descriptor fehlt noch im Backend-API-Response; wird in P5+ ergänzt wenn Inferenz-Pipeline steht

**Neue Dateien (Frontend):**
- `models/model.model.ts` — ModelDto, ModelView, CapabilitiesDto, Enrichment-Map, Helper
- `services/model.service.ts` — HTTP-Calls zu /api/models, /api/models/capabilities, /api/config
- `store/models/` — NgRx-Slice (actions, reducer, effects, selectors)
- `ui/gated-feature/` — `pf-gated-feature`-Komponente
- `ui/icon/icon.ts` — Icons ergänzt: pencil, cpu, shield, alertTriangle, text
- `features/modelle/` — vollständig: Seite + model-card + model-drawer + download-dialog + bind-dialog
