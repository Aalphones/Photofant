# Falsche Personen-Zuordnungen — Wartungs-UI

**Abgeschlossen:** 2026-06-28 (Smoke-Test grün)

## Was war das Problem

Bilder, die einer falschen Person zugeordnet waren, blieben beim Löschen/Umhängen
des Gesichts in der falschen Person hängen — in DB und im Ordner.

## Was wurde gebaut

**Backend (`fix(faces)` → `a070f02`):**
- `prune_orphaned_instances` in `backend/photofant/media/person_folders.py` prüft
  jetzt das ganze Asset (nicht nur die Person des Gesichts).
- Letzte Instance ohne Gesicht → nach `_unknown` verschieben statt löschen.
- Genutzt von `delete_face` (faces.py) und `reassign_face`.

**Backend Reconcile (`feat(maintenance)` → `4be433e`):**
- Neuer Report-Bucket `misassigned_instances` in `reconcile_job.py`.
- Repair-Aktion `fix_misassigned` in `maintenance/repair.py`.

**Frontend (`feat(maintenance)` → `716a835`):**
- Alle drei neuen Buckets (`misassigned_instances`, `orphaned_faces`,
  `acknowledged_missing`) in der Reconcile-UI sichtbar.
- UI per generischer `rr-section`-Child-Komponente refactored (Shell bleibt schlank).
- Models, Store, Types, SCSS aktualisiert.
