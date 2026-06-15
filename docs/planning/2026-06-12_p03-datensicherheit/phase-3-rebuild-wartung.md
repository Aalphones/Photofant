# P3 · Phase 3 — Rebuild & Wartungs-View

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt
- [Konzept](../../Konzept-Photofant.md) §13.3
- [docs/design/README.md](../../design/README.md) — Einstellungen-Sektionen; `docs/design/js/maintenance.jsx`, `docs/design/maintenance.css`

## Akzeptanzkriterien

- Thumbnail-Rebuild regeneriert die komplette Cache-DB aus den Bilddateien (Queue, Fortschritt); jederzeit abbrechbar ohne Schaden.
- Wartungs-View nach Prototyp fasst zusammen: Backup (Phase 1), Reconcile (Phase 2), Rebuild — mit Status, letzter Ausführung, laufenden Jobs.
- Rebuild-Endpoint ist um weitere Targets erweiterbar (P7 hängt `faces` an).

## Checkliste

- [ ] Rebuild-Job (Cache-DB leeren/neu aufbauen, Batch über alle Instanzen)
- [ ] `maintenance`-Slice (Status, Report, letzte Läufe)
- [ ] Wartungs-View (Gruppen nach Prototyp-Settings-Pattern: Row + Aktion + Sub-Text)
- [ ] Doc-Update: routes.md; AGENTS.md Critical Rules prüfen (nichts Neues nötig?)

## Report-Back
