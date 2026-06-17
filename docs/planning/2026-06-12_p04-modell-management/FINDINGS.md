# FINDINGS — P4 Modell-Management

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [x] → Phase 2: SHA-256 in `manifest.json` sind `null` — vor Download-Verifikation alle 5 Core-Modelle einmalig herunterladen, SHA-256 berechnen (`sha256sum`/`certutil`) und ins Manifest eintragen. Ohne Hash kann die Integritätsprüfung nach managed-Download nicht greifen. **Eingearbeitet:** Download-Job loggt Warning + überspringt Check wenn SHA-256 null. Manuelle Befüllung bleibt TO-DO nach ersten Downloads.
- [x] → Phase 2: `florence-2-base` ist ein HuggingFace Multi-File-Repo (`onnx-community/Florence-2-base`) — kein einzelner Download-URL. Der Download-Job muss hier `huggingface_hub.snapshot_download()` oder `hf_hub_download()` je Datei nutzen statt eines simplen HTTP-GET. Das Manifest-Flag `hf_repo` ist bereits gesetzt; Phase 2 Loader muss dieses Feld auswerten. **Eingearbeitet:** `_hf_snapshot_sync()` in download_job.py.
