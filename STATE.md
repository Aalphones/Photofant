# STATE

**Aktiver Plan:** `docs/planning/2026-07-02_p29-personen-suche-gruppen/`
**Phase:** 6/6 fertig — alle Phasen complete.
**Nächster Schritt:** Smoke-Checkliste (finale Abnahme-Kriterien in der Plan-README)
durch den User prüfen, danach Plan archivieren.

Phase 6 fertig: Person-Löschen-Flow (Backend `delete_person()` + `DELETE
/api/persons/{id}`, Frontend Dialog + Store-Wiring), plus Bugfix in
`merge_persons()` — verwaiste `SmartTrigger.person_id`-Referenzen werden beim
Löschen entfernt, beim Merge auf die Zielperson umgebogen (gemeinsamer Helper
`_resolve_person_smart_triggers`). `npm run lint` + `ng build` + `ruff check`
sauber.
