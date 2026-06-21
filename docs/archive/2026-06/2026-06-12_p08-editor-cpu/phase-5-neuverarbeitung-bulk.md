# P8 · Phase 5 — Neuverarbeitung, Vergleich & Bulk

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (bulk-edit)
- [Konzept](../../Konzept-Photofant.md) **§8.3 komplett** (pHash-Dedupe-Logik, Upscale-Sonderfall)

## Akzeptanzkriterien

- Neue Version → keine Re-Klassifizierung (Tags/Caption/Quelle erben), nur Messwerte neu (Auflösung, Qualität); Face-Detection + pHash-Vergleich gegen Crops derselben Lineage: quasi identisch → kein neues Face; abweichend → neues Face mit Provenienz (`origin_type`, `source_version_id`). (Voll wirksam mit P7; vorher No-op mit FINDINGS-Notiz.)
- Bulk-Edit über Auswahl (Bulk-Bar „Bearbeiten"): Op + Params einmal wählen → Queue-Job, pro Asset direkte Version (`new_copy`), Fortschritt + Fehler-Sammelbericht.
- Side-by-side-Vergleich poliert (Slider oder Nebeneinander nach Prototyp).

## Checkliste

- [x] Vererbungs-Logik + Mess-Refresh für neue Versionen
- [x] pHash-Dedupe nach §8.3 (inkl. Upscale-Ausnahme als vorbereitete Flagge für P9)
- [x] Bulk-Edit-Endpoint + Dialog (Op-Auswahl, Params, Save-Mode)
- [x] Doc-Update: routes.md; README Features-Stand

## Report-Back

Alle vier Punkte umgesetzt.

**Vererbung**: Tags/Caption erben via `parent_id`-Kette implizit — kein explizites Kopieren nötig. Auflösung (width/height) schreibt `_build_version_params` schon korrekt. No-Code-Item.

**pHash-Dedupe** (`_run_version_phash_dedupe` in `edit_sessions.py`): nach `save_session` (overwrite + new_copy) wird in einem Executor-Thread `buffalo_l` gestartet, Faces gescannt, dhash-Hamming gegen Lineage-Faces verglichen (Schwelle: 10). Quasi-identisch → Skip; neu → `Face`-Row mit `origin_type="edit"`, `source_version_id`. `is_upscale_source=False` als P9-Stub.

**Bulk-Edit**: `POST /api/assets/bulk-edit` → BULK_EDIT Queue-Job (`bulk_edit_job.py`). Dialog `pf-bulk-edit-dialog` (Op-Radio + per-Op-Params), eingebunden in Galerie via BulkBar `(editAction)`.

**Side-by-side-Vergleich**: Toggle-Button in Editor-Topbar (`ed-compare-btn`, nur sichtbar wenn Steps > 0), schaltet `compareMode`-Signal; Canvas-Area zeigt dann zwei `<img>`-Panes (Original | Aktuell) statt `pf-zoom-stage`. CSS: `.ed-compare-wrap`, `.ed-compare-pane`, `.ed-compare-label`, `.ed-compare-divider`.

**Doc-Update**: `docs/routes.md` um Abschnitt „Bulk-Edit (P8 Phase 5)" ergänzt.
