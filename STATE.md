# STATE

**Aktiver Plan:** Falsche Personen-Zuordnungen — Wartungs-UI (Backend fertig, Frontend offen)
**Nächster Schritt:** „misassigned"-Bucket in der Reconcile-Report-UI anzeigen + bereinigbar machen

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

**Frontend — TODO (das ist der nächste Schritt):**
1. **Erst lesen:** `features/review/review-reconcile/review-reconcile.{ts,html}` —
   das ist die echte Reconcile-Report-UI (Tabs + Issue-Liste + Repair-Buttons).
   (`features/wartung/wartung.ts` ist NUR Cache/Thumbnails, nicht der Report.)
2. **Modell nachziehen:** [models/maintenance.model.ts](frontend/src/app/models/maintenance.model.ts)
   hinkt hinterher — kennt nur `orphan`/`missing`/`drift`. Hinzufügen:
   `MisassignedInstance`-Interface, Feld `misassigned_instances` in `ReconcileReport`,
   `'misassigned'` zu `ISSUE_KINDS`, `'fix_assignment'` zu `REPAIR_ACTIONS`.
   (Hinweis: auch `orphaned_faces` + `acknowledged_missing` fehlen im Modell komplett —
   **Entscheidung offen:** nur `misassigned` nachziehen oder gleich alle Backend-Buckets.)
3. **UI:** neuer Tab/Abschnitt „Falsch zugeordnet" in review-reconcile mit
   Bereinigen-Button → `dispatchRepair({ kind: 'misassigned', instance_id }, 'fix_assignment')`.
   `RepairItem` trägt `instance_id` bereits.
4. **Verifizieren:** `npm run lint && npm run build`; danach echten Reconcile-Lauf in
   der App, Bucket prüfen.

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
