# P8 · Phase 5 — Neuverarbeitung, Vergleich & Bulk

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (bulk-edit)
- [Konzept](../../Konzept-Photofant.md) **§8.3 komplett** (pHash-Dedupe-Logik, Upscale-Sonderfall)

## Akzeptanzkriterien

- Neue Version → keine Re-Klassifizierung (Tags/Caption/Quelle erben), nur Messwerte neu (Auflösung, Qualität); Face-Detection + pHash-Vergleich gegen Crops derselben Lineage: quasi identisch → kein neues Face; abweichend → neues Face mit Provenienz (`origin_type`, `source_version_id`). (Voll wirksam mit P7; vorher No-op mit FINDINGS-Notiz.)
- Bulk-Edit über Auswahl (Bulk-Bar „Bearbeiten"): Op + Params einmal wählen → Queue-Job, pro Asset direkte Version (`new_copy`), Fortschritt + Fehler-Sammelbericht.
- Side-by-side-Vergleich poliert (Slider oder Nebeneinander nach Prototyp).

## Checkliste

- [ ] Vererbungs-Logik + Mess-Refresh für neue Versionen
- [ ] pHash-Dedupe nach §8.3 (inkl. Upscale-Ausnahme als vorbereitete Flagge für P9)
- [ ] Bulk-Edit-Endpoint + Dialog (Op-Auswahl, Params, Save-Mode)
- [ ] Doc-Update: routes.md; README Features-Stand

## Report-Back
