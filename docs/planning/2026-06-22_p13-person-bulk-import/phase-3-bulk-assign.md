# Phase 3 — Bulk-Personenzuweisung (BulkBar + Backend-Job)

**Tier:** standard
**Status:** complete
**Voraussetzung:** Phase 1 abgeschlossen (Personen im Store vorhanden)

---

## Kontext (vorher lesen)

- `backend/photofant/api/persons.py` — bestehende Endpoints, Router-Prefix `/persons`
- `backend/photofant/media/person_folders.py` — `ensure_person_folder`, `merge_persons` (Muster für Dateibewegung)
- `backend/photofant/jobs/queue.py` — `JobKind`, `JobStatus`, `job_queue.enqueue()`
- `frontend/src/app/ui/bulk-bar/bulk-bar.ts` + `.html` — bestehende Aktionen
- `frontend/src/app/features/galerie/galerie.ts` + `.html`
- `frontend/src/app/services/person.service.ts`
- `frontend/src/app/store/persons/` — selectors + actions (aus Phase 1)

---

## Abnahme-Kriterien

- [x] BulkBar zeigt „Person zuweisen" wenn ≥1 Bild ausgewählt und ≥1 benannte Person existiert
- [x] Klick öffnet `AssignPersonDialog` mit Liste aller benannten Personen (ohne `_unknown`)
- [x] Zuweisung läuft als Job in der Job-Queue (Dock zeigt Fortschritt)
- [x] Nach Abschluss: `AssetInstance.person_id` auf Zielperson gesetzt, `fixed_person=True`
- [x] Dateien physisch in `target_person/`-Unterordner (`photos/`, ggf. `favourites/`/`edits/`)
  verschoben, `AssetInstance.path` aktualisiert — via `materialize_assignment` (s. Deviation unten)
- [x] Gesicht auf Asset war `_unknown`: bestes Gesicht → Zielperson, Rest bleibt `_unknown`
- [x] Per-Asset-Fehler (Datei fehlt, Person gelöscht) loggen + weitermachen, Job bricht nicht ab

---

## Checkliste

### Backend: bulk_assign_person_job.py (neu)

Neue Datei: `backend/photofant/jobs/bulk_assign_person_job.py`

🟡 **Deviation** (siehe FINDINGS.md): statt der hier skizzierten eigenen
`_move_asset_to_person` wurde `materialize_assignment` +
`move_face_crops_to_person` + `prune_orphaned_instances` aus
`person_folders.py` wiederverwendet — Grund: Kollisionsschutz für den
DB-Unique-Constraint `(asset_id, person_id)`, den die skizzierte naive
Variante nicht abdeckt. Funktional gleichwertig zu den AK.

- [x] `_get_unknown_person_id() -> int | None` — einmalig aus DB lesen
- [x] Dateibewegung + `fixed_person=True` (via `materialize_assignment`, s. Deviation)
- [x] `_reassign_unknown_faces(asset_id, target_person_id, unknown_person_id)`:
  bestes `_unknown`-Gesicht (score desc) → Zielperson, Rest bleibt unverändert
- [x] `run_bulk_assign_person_job(status, asset_ids, person_id)`: Progress pro Asset,
  Per-Asset-Fehler gesammelt + geloggt, Job bricht nicht ab
- [x] `enqueue_bulk_assign_person(asset_ids, person_id) -> JobStatus`
- [x] `JobKind.BULK_ASSIGN` ergänzt (eigener Wert, wie empfohlen)

### Backend: persons.py (Endpoint)

- [x] `BulkAssignRequest`-Pydantic-Modell
- [x] `POST /{person_id}/bulk-assign` — wie spezifiziert umgesetzt

### Frontend: AssignPersonDialog (neu)

- [x] `assign-person-dialog.ts` / `.html` / `.scss` unter `ui/assign-person-dialog/`
  angelegt (manuell statt `ng generate`, gleiches Ergebnis)

- [x] **assign-person-dialog.ts:** wie spezifiziert (`persons`, `close`, `confirm`,
  `namedPersons`, `pick`) + `portraitUrl`/`onBackdrop` analog `merge-dialog.ts`

- [x] **assign-person-dialog.html:** Modal mit scrollbarer Personen-Liste,
  Portrait-Thumbnail + Name + Bildanzahl, BEM-Block `assign-person-dialog`.

- [x] **assign-person-dialog.scss:** analog `merge-dialog.scss`.

### Frontend: ui/index.ts

- [x] `AssignPersonDialog` re-exportiert.

### Frontend: bulk-bar.ts

- [x] Neue Imports: `PersonDto` aus `@photofant/models`
- [x] Neues Input: `readonly persons = input<PersonDto[]>([])`
- [x] Neues Output: `readonly assignPersonAction = output<void>()`
- [x] Computed `hasNamedPersons` für Sichtbarkeit
- [x] Handler `openAssignPerson()`

### Frontend: bulk-bar.html

- [x] Neuen Button eingefügt (nur wenn `hasNamedPersons()`) — Klasse
  `bulkbar__action` statt der im Plan skizzierten `bulk-bar__action`
  (die echte BEM-Konvention in dieser Datei ist `bulkbar__*`, nicht `bulk-bar__*`)

### Frontend: person.service.ts

- [x] `bulkAssignPerson(personId, assetIds): Observable<PersonImportResponse>` —
  bestehenden `PersonImportResponse`-Typ wiederverwendet statt eines neuen
  Inline-Typs (identische Form `{ job_id: string }`)

### Frontend: galerie.ts

- [x] `PersonService` via `inject()` ergänzt
- [x] `persons`-Signal aus Store + `personsSelectors` zu den Store-Imports ergänzt
  (`personsActions` war schon importiert)
- [x] `showAssignPersonDialog = signal(false)` ergänzt
- [x] Handler `onBulkAssignPersonOpen` / `onBulkAssignPersonConfirm` / `onBulkAssignPersonCancel`
  wie spezifiziert

### Frontend: galerie.html

- [x] `AssignPersonDialog` in imports ergänzt
- [x] `BulkBar` bekommt `[persons]` + `(assignPersonAction)`
- [x] Dialog-Instanz am Ende eingefügt

---

## Doc-Updates

- [x] Keine neuen Settings-Keys
- [x] FINDINGS.md: Deviation zur Datei-Bewegung (`materialize_assignment` statt
  eigener naiver Move-Logik) festgehalten
