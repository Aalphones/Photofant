# FINDINGS — P13 Person-Bulk-Import

Unerwartete Erkenntnisse und Entscheidungen während der Umsetzung.

---

- [x] → Phase 2: `face_job.py` hatte bereits einen Ad-hoc-Fix (Commit `544c95a`,
  24.06., vor Plan-Umsetzung) für den Single-Face-Fall (`len(faces) == 1`) —
  ohne Sortierung nach Score und ohne Skip von `_run_incremental_match` für
  das fixierte Gesicht. Ersetzt durch die im Plan spezifizierte
  `face_index == 0`-Logik (funktioniert jetzt auch bei 2+ Gesichtern).
