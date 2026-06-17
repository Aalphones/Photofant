# FINDINGS — P5 Klassifizierung

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [ ] → Phase 5: Caption läuft bisher **nur im Import-Fluss** (analog Tagging). Der `POST /classify/rerun`-Endpoint (Bulk/Single-Neuberechnung mit Ledger-Reset, optional `caption_preset_id`) ist noch nicht gebaut — gehört in die Pipeline-Integration. Caption-Job-Bausteine liegen bereit: `enqueue_caption(asset_id, path)` + Ledger `caption_done`.
- [ ] → Phase 6: `model_registry.capabilities` (deklarativer UI-Descriptor §12.6) ist für Florence **noch nicht befüllt**; die Settings-UI-Steuerelemente (Task-Token-Dropdown etc.) sind Phase-6-Sache. Default-Preset ist aktuell **global** (`model_id = NULL`), nicht je-Captioner — bei mehreren Captionern in Phase 6 auf per-Modell-Default umstellen.
- [ ] → Phase 4: Florence-Preprocessing wurde von 224er-CLIP-Center-Crop auf **768² Squash-Resize** korrigiert (`resize_squash` in `preprocessing.py`); CLIP/SigLIP (Phase 4) bleibt beim 224er Center-Crop — Funktionen sind getrennt, nicht versehentlich zusammenlegen.
