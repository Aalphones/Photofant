# P10 · Phase 4 — Export-Workflows

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (export-Endpoints)
- [Konzept](../../Konzept-Photofant.md) §11 (Export-Liste), §9 (Sidecar-Regeln, Train/Val)

## Akzeptanzkriterien

- Trainingsset-Export: Bilder + Sidecar-`.txt` (Tags/Caption/beides — effektive Caption inkl. Override und Set-Präfixen), optional Train/Val-Split (Ratio aus settings, deterministisch per Seed) in `train/`/`val/`.
- Allgemeine Exporte: aktueller Filter, aktuelle Gruppierung (z.B. komplette Lineage), Collections, alle Favoriten (Ordner pro Person), Zufalls-Favoriten (n Sets × m Bilder, distinct über alle Sets, Personen-Name im Dateinamen).
- Alle Exporte als Queue-Jobs (Fortschritt, Abbruch); Ziel-Ordner-Wahl; „Im Dateisystem anzeigen" für Einzelbilder und Export-Ergebnis.
- Export verändert nie den Bestand (reine Kopien).

## Checkliste

- [ ] Export-Engine (Quelle → Ziel-Layout-Strategien) + Endpoints
- [ ] Sidecar-Writer (Format-Optionen, Encoding UTF-8 ohne BOM)
- [ ] Zufalls-Favoriten-Logik (distinct, Seeds)
- [ ] Export-Dialoge (Scope-abhängig) + reveal-Aktion
- [ ] Doc-Update: routes.md; README Features-Stand (Projekt feature-complete bis auf Optionales)

## Report-Back
