# STATE

**Aktiver Plan:** Falsche Personen-Zuordnungen — Wartungs-UI (Backend + Frontend fertig, User-Smoke offen)
**Nächster Schritt:** Echten Reconcile-Lauf in der App machen, die neuen Buckets prüfen (siehe „User-Smoke" unten), dann Plan archivieren.

## Aktive Arbeit: falsche Personen-Zuordnungen

**Worum geht's:** Bilder, die einer falschen Person zugeordnet sind (Import oder
veraltetes Clustering), blieben beim Löschen/Umhängen des Gesichts in der falschen
Person hängen — in DB *und* im Ordner. Quelle: `issues.txt` (untracked).

**Backend — FERTIG & committet & getestet:**
- `fix(faces)` Commit `a070f02`: `prune_orphaned_instances` in
  [person_folders.py](backend/photofant/media/person_folders.py#L454) prüft jetzt
  das ganze Asset (nicht nur die Person des Gesichts). Letzte Instance ohne Gesicht
  → nach `_unknown` verschieben statt löschen (nie Foto-Verlust). Genutzt von
  `delete_face` (faces.py) und `reassign_face`. Frontend lädt Galerie neu
  ([lightbox.ts](frontend/src/app/features/galerie/lightbox/lightbox.ts#L433)).
  Tests: `tests/test_person_folders.py` (prune + reassign-Integration, grün).
- `feat(maintenance)` Commit `4be433e`: Reconcile findet Altlasten. Neuer Report-
  Bucket `misassigned_instances`
  ([reconcile_job.py `_gather_misassigned_instances`](backend/photofant/jobs/reconcile_job.py#L138)),
  Repair-Aktion [`fix_misassigned`](backend/photofant/maintenance/repair.py#L85)
  (ruft dieselbe prune-Logik).

**Backend-Vertrag für die UI:**
- `GET /api/maintenance/reconcile/report` → liefert jetzt zusätzlich
  `misassigned_instances: [{ instance_id, asset_id, path, person_name, detail }]`.
- `POST /api/maintenance/reconcile/repair`, Body
  `{ actions: [{ item: { kind: "misassigned", instance_id }, action: "fix_assignment" }] }`.

**Frontend — FERTIG (Lint + Build grün):**
Entscheidung getroffen: **alle drei** neuen Buckets sichtbar gemacht, und die UI per
**generischer `rr-section`-Child-Komponente** refactored (Shell wurde sonst ein
6-Sektionen-Monolith, über der Aufspaltungs-Schwelle).
- `models/maintenance.model.ts` + Barrel: `OrphanedFace`/`MisassignedInstance`/
  `AcknowledgedMissing`-Interfaces, drei Felder in `ReconcileReport`, drei Kinds in
  `ISSUE_KINDS`, `'purge'`+`'fix_assignment'` in `REPAIR_ACTIONS`, `face_id?` in `RepairItem`.
- `store/maintenance.reducer.ts`: `pruneReport` prunet jetzt alle sechs Buckets optimistisch.
- Neu: `features/review/review-reconcile/review-reconcile.types.ts` (RrRow/RrAction/…) +
  `rr-section/` (generische Section-Child: Selection, Bulk-/Row-Buttons, BEM `rr-section__*`).
- `review-reconcile.{ts,html,scss}`: Shell ist jetzt dünne Konfig — sechs `<pf-rr-section>`
  mit Row-Projektion + Action-Configs, `onRepair(kind, event)` baut die `RepairAction[]`.
- `docs/code-map.md`: Wartungs-Zeile um `features/review/review-reconcile/` ergänzt.

**Diagnose zum „No-Op"-Verdacht (geklärt):** Der Abgleich ist **kein** No-Op. Job läuft,
schreibt den Report, API ([maintenance.py](backend/photofant/api/maintenance.py)) liefert
alle Buckets aus, Effect lädt nach dem Job neu. Der „immer alles in Ordnung"-Eindruck kam
allein daher, dass die UI drei Buckets (misassigned, orphaned_faces, acknowledged_missing)
verworfen hat. Genau das ist jetzt behoben. (`orphan/missing/drift` = 0 ist der gesunde
Normalfall bei synchronem FS↔DB — kein Bug.)

**⏳ User-Smoke (offen, vor Archivierung):**
1. App starten, Wartung/Review → Reconcile-Scan auslösen.
2. Erscheinen die neuen Sektionen, wenn das Backend was findet? (Wenn alles synchron ist
   und keine Fehlzuordnung existiert → „Alles in Ordnung", das ist korrekt.)
3. Gegencheck bei Zweifel: `SELECT payload FROM reconcile_report WHERE id=1;` gegen
   `Data/.photofant/db.sqlite` nach einem Lauf — stehen `misassigned_instances` etc. drin?
4. Bereinigen-Button auf einem „Falsch zugeordnet"-Eintrag testen → verschwindet die Zeile,
   und ist die Person-Zuordnung in DB + Ordner korrigiert?

---

## Backlog & Abgeschlossenes

**Abgeschlossen:**
- P9 Phase 1–5: Generative Features vollständig — archiviert in `docs/archive/2026-06/2026-06-12_p09-generativ/` (2026-06-23)
- P12: Konfigurierbare Gesichtserkennung-Parameter — complete (2026-06-22)
- P14 Job-Queue Zwei-Spuren + Prio — archiviert in `docs/archive/2026-06/2026-06-27_p14-job-queue-prio-parallelisierung.md` (2026-06-27)

**Backlog-Pläne (größere Features):**
- P10 Trainingssets: `docs/planning/2026-06-12_p10-trainingssets-export/`
- P11 Duale Duplikaterkennung: `docs/planning/2026-06-22_p11-duale-duplikaterkennung/`
- P13 Person-Bulk-Import: `docs/planning/2026-06-22_p13-person-bulk-import/`
