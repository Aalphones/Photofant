# FINDINGS — P13 Person-Bulk-Import

Unerwartete Erkenntnisse und Entscheidungen während der Umsetzung.

---

- [x] → Phase 2: `face_job.py` hatte bereits einen Ad-hoc-Fix (Commit `544c95a`,
  24.06., vor Plan-Umsetzung) für den Single-Face-Fall (`len(faces) == 1`) —
  ohne Sortierung nach Score und ohne Skip von `_run_incremental_match` für
  das fixierte Gesicht. Ersetzt durch die im Plan spezifizierte
  `face_index == 0`-Logik (funktioniert jetzt auch bei 2+ Gesichtern).

- [x] → Phase 3: Der Plan-Entwurf für `_move_asset_to_person` schrieb eine
  eigene naive Dateibewegung vor (immer nach `photos/`, keine Kollisionsprüfung).
  Das hätte den DB-Unique-Constraint `(asset_id, person_id)` verletzen können,
  wenn beim Ziel schon eine Instanz existiert (z.B. Bulk-Assign ein zweites Mal
  auf dieselbe Auswahl). Stattdessen `materialize_assignment` +
  `move_face_crops_to_person` + `prune_orphaned_instances` aus
  `person_folders.py` wiederverwendet — dieselbe crash-sichere Logik, die
  `assign_person_to_asset` (assets.py) schon für den Einzelfall nutzt.
  Ergebnis ist funktional gleichwertig zu den AK, nur robuster.
