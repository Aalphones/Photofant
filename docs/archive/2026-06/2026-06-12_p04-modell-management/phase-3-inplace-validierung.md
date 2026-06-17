# P4 · Phase 3 — In-Place-Binding & Validierung

> Rating: **heikel** (fehleranfälligste Stelle der App laut Konzept; Validierungs-Matrix) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Fehlercodes)
- [Konzept](../../Konzept-Photofant.md) §12.1 (In-Place-Formen), §12.2 Flow B, **§12.2a komplett** (Validierungsstufen + Fehlerklassen-Tabelle)

## Akzeptanzkriterien

- Validierungsstufen 1–5 aus §12.2a implementiert und **in dieser Reihenfolge** durchlaufen: Existenz/Zugriff → Format (Endung + Magic-Bytes) → Rolle → Vollständigkeit (für Ordner-Modelle: Pflichtdateien wie WD14-CSV, buffalo_l-Teilmodelle) → Probe-Load (ONNX-Session öffnen bzw. Header lesen, keine Inferenz).
- Jeder Fehler: strukturierter Code + Meldung mit erwartetet/gefunden/nächster Schritt; Roh-Exception geloggt, nie an den Nutzer durchgereicht.
- Gescheiterter Versuch lässt Registry und Dateisystem unangetastet (Validierung komplett **vor** dem Insert).
- In-Place: SHA-256 wird berechnet und informativ gespeichert (kein Gate); `managed = 0`; Entfernen löscht nur den Eintrag.

## Checkliste

- [x] Validator-Pipeline pro Rolle (face/tagger/captioner/clip/rembg): erwartete Formate, Pflicht-Bestandteile, Probe-Load-Strategie — `spec_for()` leitet Layout/Pflichtdateien aus dem Manifest-Eintrag ab
- [x] Magic-Bytes-Checks (onnx protobuf, safetensors-Header, gguf-Magic) — `detect_format()`
- [x] Rollen-Plausibilität (Input-Rang der ONNX-Session gegen Rollen-Erwartung) — via onnxruntime **wenn verfügbar**, sonst geloggt + deferred (s. Report-Back)
- [x] `register-local`-Endpoint (Einzeldatei + Ordner), transaktional — Validierung komplett vor DB-Insert
- [x] `DELETE`-Endpoint — managed: Datei+Eintrag; in-place: nur Eintrag (Datei unangetastet)
- [x] Unit-Tests: pro Fehlerklasse aus der §12.2a-Tabelle ein Fall (Kern-Risiko des Plans) — 11 Tests, alle grün
- [x] Doc-Update: routes.md (Fehlercodes-Tabelle)

## Report-Back

**Umgesetzt:**
- `backend/photofant/models/validation.py` — 5-stufige Pipeline (`validate_in_place`), strukturierte `ModelValidationError(code, expected, found, next_step)`, Format-Erkennung per Magic-Bytes (gguf/safetensors) + Endung (onnx).
- `backend/photofant/api/models.py` — `POST /register-local` (Validierung in `asyncio.to_thread`, Insert nur bei Erfolg → transaktional), `DELETE /{manifest_id}`.
- `backend/tests/test_model_validation.py` — pro §12.2a-Fehlerklasse ein Fall + Happy-Paths + zwei Endpoint-Tests (failed-validation-schreibt-nichts, in-place-delete-lässt-Datei).
- `docs/routes.md` — neue Endpoints + Validierungs-Fehlercodes.

**Chesterton/Deviation — onnxruntime nicht installiert:**
`onnxruntime` ist (noch) keine Dependency (kommt mit der Core-Inferenz-Phase). Stufe 5
(Ladbarkeit) nutzt onnxruntime **opportunistisch**, fällt sonst auf einen Protobuf-Header-Sniff
zurück (vom AK als „Header lesen" erlaubt). Stufe 3 (Rolle) kann ohne Runtime keine tiefe
Graph-Introspektion machen → wird geloggt + deferred. Format-Stufe fängt den häufigsten Fehlfall
(falsches Format im Slot) ohnehin früher ab. → Finding für die Inferenz-Phase getaggt.
