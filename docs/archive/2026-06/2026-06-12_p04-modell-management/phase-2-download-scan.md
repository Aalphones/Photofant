# P4 · Phase 2 — Download & Scan

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §12.2 Flow A, §12.1 (drei Beschaffungswege)
- Job-Queue (P1) — Download läuft als Job

## Akzeptanzkriterien

- Download-Job: holt Haupt- + Begleitdateien in `models_dir`, Fortschritt (Bytes/Total) über SSE, Resume bei Abbruch oder sauberer Neustart, SHA-256-Prüfung gegen Manifest am Ende; erst dann Registry-Eintrag (`managed = 1`).
- Hash-Mismatch → Datei als `.partial` markiert/entfernt, Fehlercode `MODEL_HASH_MISMATCH`, Registry bleibt sauber.
- Scan-Endpoint erkennt manuell in `models_dir` abgelegte Dateien (Hash-Match gegen Manifest) → `managed = 1`.
- Dies ist der **einzige** legitime Netzwerkpfad der App (Critical Rule 1) — Download-Client explizit nur hier, kein globaler HTTP-Client.

## Checkliste

- [x] Download-Job (httpx, Streaming, Range-Resume, Temp-Datei + Rename nach Prüfung)
- [x] SHA-Prüfung + Registrierung als letzter Schritt (transaktional)
- [x] Scan-Endpoint (Dateien hashen, Manifest-Match, registrieren)
- [x] Lizenz-Bestätigung im Flow verankern (Manifest-Flag `requires_license_ack` → Frontend-Dialog in Phase 4)
- [x] Doc-Update: routes.md

## Report-Back

Neue Dateien: `backend/photofant/jobs/download_job.py` (Download-Job, Scan-Helper).

Geändert:
- `backend/pyproject.toml` — `httpx>=0.28`, `huggingface_hub>=0.26` in Haupt-Deps (von dev)
- `backend/photofant/config.py` — `get_models_dir(session)` Helper
- `backend/photofant/models/loader.py` — `requires_license_ack` in `ManifestEntry`
- `backend/photofant/jobs/queue.py` — `DOWNLOAD = "download_model"` in `JobKind`
- `backend/photofant/api/models.py` — `POST /{manifest_id}/download`, `POST /scan`
- `docs/routes.md` — Models-Sektion mit allen Endpoints + Typen + Fehler-Codes

SHA-256 in manifest.json sind noch null — Download-Job loggt Warning und überspringt Hash-Check. Werte müssen manuell eingetragen werden (FINDING bleibt offen bis nach erstem tatsächlichem Download).
