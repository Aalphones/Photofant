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

- [ ] Validator-Pipeline pro Rolle (face/tagger/captioner/clip/rembg): erwartete Formate, Pflicht-Bestandteile, Probe-Load-Strategie
- [ ] Magic-Bytes-Checks (onnx protobuf, safetensors-Header, gguf-Magic)
- [ ] Rollen-Plausibilität (z.B. Input-Shape/Metadaten der ONNX-Session gegen Rollen-Erwartung)
- [ ] `register-local`-Endpoint (Einzeldatei + Ordner), transaktional
- [ ] Unit-Tests: pro Fehlerklasse aus der §12.2a-Tabelle ein Fall (Kern-Risiko des Plans)
- [ ] Doc-Update: routes.md (Fehlercodes-Tabelle)

## Report-Back
