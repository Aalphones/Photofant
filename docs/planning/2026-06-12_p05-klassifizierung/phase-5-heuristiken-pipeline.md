# P5 · Phase 5 — Heuristiken & Pipeline-Integration

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Rerun)
- [Konzept](../../Konzept-Photofant.md) §6.1 (Schritte 4–7 + Queue), §6.2 (Matrix)

## Akzeptanzkriterien

- Qualitäts-Score: Auflösung + Blur (Laplacian-Varianz) → `quality_score` 0–1; **Framing bleibt offen** (braucht Face-BBox → P7 trägt nach; Konzept-Stage-2-Listung ist hier bewusst beschnitten).
- Import-Fluss orchestriert alle Steps nach §6.1 (Metadaten → Heuristiken → Tags → Caption → Embedding), Ledger-Flags pro Step, Steps einzeln überspringbar wenn Modell fehlt.
- `POST /api/classify/rerun` (Auswahl/alle, Step-Auswahl, optional Preset) + UI-Aktion in Bulk-Bar und Detail-Panel.
- Bulk-Lauf über 1000+ Bilder bleibt bedienbar: Fortschritt, Abbruch, Fortsetzung (Ledger).

## Checkliste

- [ ] Qualitäts-Modul (OpenCV/Pillow, Blur-Messung)
- [ ] Pipeline-Orchestrierung (ein Job pro Asset oder Batch-Job mit Sub-Fortschritt — bei Umsetzung entscheiden, Findung in FINDINGS)
- [ ] Rerun-Endpoint + Ledger-Reset-Logik
- [ ] Frontend: Rerun-Aktion (Bulk-Bar, Detail-Panel) mit Step-Auswahl-Dialog
- [ ] Doc-Update: routes.md

## Report-Back
