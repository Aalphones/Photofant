# P7 · Phase 6 — Face-Import, Duplikate & Rebuild

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (faces/import, duplicates/search)
- [Konzept](../../Konzept-Photofant.md) §6.1b (eigenständige Faces), §10 (Duplikate mit %), §13.3 (Face-Rebuild)
- `docs/design/js/dupecheck.jsx`, `compare.jsx`

## Akzeptanzkriterien

- Direkter Face-Import: Bild als eigenständiges Face-Original (`asset_id = NULL`, `origin = manual_original`) — keine Detection/Extraction, Embedding wird berechnet, matchbar und editierbar (§6.1b).
- Duplikat-Suche innerhalb eines Person-Ordners: pHash-Hamming → %-Anzeige, Schwellwert einstellbar; Modal-Grid nach Prototyp, Markieren + Batch → Papierkorb.
- Face-Rebuild als P3-Rebuild-Target `faces`: re-extrahiert abgeleitete Crops; manuelle Originale werden nie überschrieben.

## Checkliste

- [x] Face-Import-Endpoint + UI-Einstieg (Personen-Karte / Personen-Detail)
- [x] Duplikat-Endpoint (pHash über Instanzen einer Person, Paar-Bildung, %-Umrechnung) + Dupe-Modal
- [x] Rebuild-Erweiterung (`target: "faces"`, Schutz `origin = manual_original`)
- [x] Doc-Update: routes.md; README Features-Stand

## Report-Back
