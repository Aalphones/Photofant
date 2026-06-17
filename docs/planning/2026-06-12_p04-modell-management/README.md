# P4 — Modell-Management (Stage 2a)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §12 · Abhängigkeiten: P1 (parallel zu P2/P3 möglich)

Registry, Beschaffung (Download / In-Place) und Gating für **Core-ONNX-Modelle** (Einzeldatei + Ordner-Modelle). Bewusste Scope-Grenze: Komponenten-Modelle (Flux: Diffusion/Encoder/VAE einzeln), VRAM-Varianten-Matrix und Kompatibilitäts-Warnungen kommen erst mit P9 — dort werden sie gebraucht.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Registry & Manifest](phase-1-registry-manifest.md) | standard | complete |
| 2 | [Download & Scan](phase-2-download-scan.md) | standard | complete |
| 3 | [In-Place-Binding & Validierung](phase-3-inplace-validierung.md) | heikel | complete |
| 4 | [Modelle-View & Gating](phase-4-modelle-view-gating.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **`GET /api/models`** → `[{ id, role, name, variant, format, path, sha256, managed, enabled, is_default, status: "active"|"available"|"missing"|"inplace", size_bytes, license_note }]`
- **`POST /api/models/{manifest_id}/download`** → `{ job_id }` (Queue; SHA-256-Prüfung am Ende; Begleitdateien inklusive).
- **`POST /api/models/register-local`** — `{ manifest_id, path }` (Einzeldatei **oder** Ordner) → validiert, registriert mit `managed = 0`; Fehler als strukturierte Codes.
- **`POST /api/models/scan`** — Download-Ordner nach manuell abgelegten Dateien durchsuchen → erkannte gegen Manifest matchen.
- **`DELETE /api/models/{id}`** — managed: Datei + Eintrag; in-place: **nur** Eintrag.
- **`GET/PATCH /api/config`** — u.a. `models_dir` (Verzeichnis-Picker im Frontend).
- **Fehlercodes** (Frontend mappt auf Meldungen nach Konzept §12.2a): `MODEL_NOT_FOUND`, `MODEL_WRONG_FORMAT`, `MODEL_WRONG_ROLE`, `MODEL_INCOMPLETE`, `MODEL_LOAD_FAILED`, `MODEL_HASH_MISMATCH`.
- **Gating-Quelle:** `GET /api/models/capabilities` → `{ tagging: bool, captioning: bool, semantic_search: bool, faces: bool, rembg: bool }` — Frontend blendet Features daran aus/ein (ein Endpoint, keine verteilte Logik).
- **Manifest:** versionierte JSON-Datei im Repo (`backend/photofant/models/manifest.json`): pro Modell Quelle-URL, SHA-256, Größe, Rolle, Format, Lizenzhinweis. Core-Umfang: buffalo_l, WD14 swinv2-v3, Florence-2-base, CLIP/SigLIP, rembg.

## Finale Akzeptanzkriterien

1. Modell ohne Bestand: Status „missing", abhängiges Feature deaktiviert mit Hinweis „Modell X fehlt".
2. In-App-Download lädt in den konfigurierten `models_dir`, prüft SHA-256, aktiviert das Modell; Fortschritt im Job-Dock; Hash-Abweichung → klare Meldung + kein halber Registry-Eintrag.
3. Vorhandene Datei/Ordner in-place einbinden: gültige Wahl → registriert ohne Kopieren/Verschieben; jede Fehlerklasse aus §12.2a liefert ihre Meldung (erwartet · gefunden · nächster Schritt).
4. `models_dir` per UI änderbar; Änderung gilt für neue Downloads, bestehende Pfade bleiben.
5. Entfernen eines In-Place-Modells lässt die Datei nachweislich unangetastet.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] rembg per In-App-Download holen → Status „active", Hash geprüft
- [ ] Vorhandenes WD14-Verzeichnis in-place einbinden → „inplace", Datei unverändert am Ort
- [ ] Absichtlich eine falsche Datei (z.B. ein VAE-safetensors) in einen Tagger-Slot binden → verständliche Fehlermeldung, kein Registry-Müll
- [ ] `models_dir` auf anderes Laufwerk legen → nächster Download landet dort
- [ ] Modell deaktivieren → zugehöriges Feature in der UI gegated

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
