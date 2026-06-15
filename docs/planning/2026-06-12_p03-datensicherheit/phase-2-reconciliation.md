# P3 · Phase 2 — FS↔DB-Reconciliation

> Rating: **heikel** (Klassifikations-Logik; falsche Repair-Aktion kann Daten kosten) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Report-Form, Repair-Actions)
- [Konzept](../../Konzept-Photofant.md) §13.2, §4 (Pfad-Führung in der DB)
- Move-Modul aus P2 Phase 5 (Wiederverwendung für `fix_path`)

## Akzeptanzkriterien

- Scan vergleicht `Data/`-Bestand gegen `asset_instance.path`: **verwaist** (FS ohne DB), **fehlend** (DB ohne FS), **Drift** (Datei woanders gefunden — Match über Content-Hash).
- Drift-Erkennung rehasht nur Kandidaten (Dateiname/Größe-Vorfilter), nicht die ganze Bibliothek; Fortschritt über die Queue.
- Repair-Aktionen: verwaist → neu indizieren (Import-Pfad) oder Papierkorb; fehlend → als fehlend markieren (UI-Kennzeichnung) oder Eintrag in Papierkorb; Drift → Pfad korrigieren.
- Report bleibt bis zum nächsten Scan abrufbar; keine Repair-Aktion läuft ohne explizite Auswahl (kein Auto-Repair).

## Checkliste

- [ ] Scan-Job (Walk über `Data/`, Abgleich, Vorfilter + gezieltes Rehashing)
- [ ] Report-Persistenz (app_config oder eigene Tabelle) + Endpoints
- [ ] Repair-Endpoint, der pro Item die gewählte Aktion ausführt (Move-Modul nutzen)
- [ ] Unit-Tests für die Klassifikation (drei Fälle + Hash-Match) — datenkritisch, siehe testing.md
- [ ] UI: Report-Tabelle mit Aktions-Auswahl pro Zeile + „Ausführen"
- [ ] Doc-Update: routes.md

## Report-Back
