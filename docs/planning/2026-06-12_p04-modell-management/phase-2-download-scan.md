# P4 · Phase 2 — Download & Scan

> Rating: standard · Status: pending

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

- [ ] Download-Job (httpx, Streaming, Range-Resume, Temp-Datei + Rename nach Prüfung)
- [ ] SHA-Prüfung + Registrierung als letzter Schritt (transaktional)
- [ ] Scan-Endpoint (Dateien hashen, Manifest-Match, registrieren)
- [ ] Lizenz-Bestätigung im Flow verankern (Manifest-Flag `requires_license_ack` → Frontend-Dialog in Phase 4)
- [ ] Doc-Update: routes.md

## Report-Back
