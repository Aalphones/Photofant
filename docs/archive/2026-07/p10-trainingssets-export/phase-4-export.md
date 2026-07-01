# P10 · Phase 4 — Export-Workflows

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (export-Endpoints)
- [Konzept](../../Konzept-Photofant.md) §11 (Export-Liste), §9 (Sidecar-Regeln, Train/Val)

## Akzeptanzkriterien

- Trainingsset-Export: Bilder + Sidecar-`.txt` (Tags/Caption/beides — effektive Caption inkl. Override und Set-Präfixen), optional Train/Val-Split (Ratio aus settings, deterministisch per Seed) in `train/`/`val/`.
- Allgemeine Exporte: aktueller Filter, aktuelle Gruppierung (z.B. komplette Lineage), Collections, alle Favoriten (Ordner pro Person), Zufalls-Favoriten (n Sets × m Bilder, distinct über alle Sets, Personen-Name im Dateinamen).
- Alle Exporte als Queue-Jobs (Fortschritt, Abbruch); Ziel-Ordner-Wahl; „Im Dateisystem anzeigen" für Einzelbilder und Export-Ergebnis.
- Export verändert nie den Bestand (reine Kopien).

## Checkliste

- [x] Export-Engine (Quelle → Ziel-Layout-Strategien) + Endpoints — bereits vorhandene Favoriten-/Album-Exporte generalisiert (Ziel-Ordner-Wahl, Filter nicht mehr favoriten-fest) + neuer Trainingsset-Export mit Sidecar/Split
- [x] Sidecar-Writer (Format-Optionen, Encoding UTF-8 ohne BOM) — Kohya-Style `.txt` (tags/caption/both), `write_text(..., encoding="utf-8")`
- [x] Zufalls-Favoriten-Logik (distinct, Seeds) — bereits vorhanden (distinct über alle Sets); Seed-Determinismus stattdessen für den Train/Val-Split umgesetzt (siehe Deviations)
- [x] Export-Dialoge (Scope-abhängig) + reveal-Aktion — gemeinsamer `ExportDialog` (Galerie + Favoriten) nach `ui/` verschoben, neuer `TrainingSetExport`-Dialog; Einzelbild-Reveal (`/assets/{id}/reveal`) war schon da
- [x] Doc-Update: routes.md; README Features-Stand (Projekt feature-complete bis auf Optionales)

## Report-Back

Ein Großteil der Favoriten-/Album-Exporte existierte bereits aus einer früheren Phase
(`export_job.py`, `api/export.py`, Favoriten-Export-Dialog) — diese Phase hat sie generalisiert
(Ziel-Ordner-Wahl, Filter-Export nicht mehr zwingend favoriten-beschränkt) statt sie neu zu bauen,
und den fehlenden Teil ergänzt: Trainingsset-Export mit Sidecar-`.txt` + deterministischem
Train/Val-Split, sowie den Export-Zugang in der Galerie (bisher nur in Favoriten verfügbar).
