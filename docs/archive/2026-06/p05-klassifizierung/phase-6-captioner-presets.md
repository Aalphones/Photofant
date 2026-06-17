# P5 · Phase 6 — Captioner-Settings & Presets (UI)

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Capabilities-Descriptor)
- [Konzept](../../Konzept-Photofant.md) **§12.6 komplett** (drei Modi, Florence-Tabelle, UI-Hinweise)
- `docs/design/js/settings.jsx` (Settings-Patterns), Modelle-View aus P4

## Akzeptanzkriterien

- Settings-Panel rendert die Captioner-Steuerelemente **deklarativ aus dem `capabilities`-JSON** des Modells — für Florence-2: Task-Token-Dropdown, `max_new_tokens`, `num_beams`, Info-Box („kein System-Prompt-Feld") nach §12.6. Die Renderer-Architektur trägt die `instruct`/`instruct_guided`-Modi schon (P9 liefert nur neue Descriptoren, keinen neuen Renderer).
- Preset-Verwaltung: anlegen/bearbeiten/löschen/Default-setzen; Preset-Auswahl beim Caption-Lauf (Rerun-Dialog aus Phase 5).
- Erstnutzer-tauglich: Jedes Steuerelement hat die Erklärungs-Zeile aus der Konzept-Tabelle; Defaults sind sofort brauchbar, kein Pflicht-Tuning.

## Checkliste

- [x] Descriptor-Schema festlegen (Feld-Typen: dropdown/number/slider/textarea/checkbox + Erklärtext) und für Florence-2 im Manifest/Registry hinterlegen
- [x] Deklarativer Form-Renderer (Reactive Forms, generiert aus Descriptor)
- [x] Preset-CRUD-UI + `presets`-Slice (NgRx)
- [x] Verdrahtung in den Rerun-Dialog (Modell + Preset wählen)
- [ ] Doc-Update: routes.md (caption-presets), docs/models.md

## Report-Back
