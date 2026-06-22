# Phase 3 — Bulk-Personenzuweisung (BulkBar + Backend-Job)

**Tier:** standard
**Status:** pending
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

- [ ] BulkBar zeigt „Person zuweisen" wenn ≥1 Bild ausgewählt und ≥1 benannte Person existiert
- [ ] Klick öffnet `AssignPersonDialog` mit Liste aller benannten Personen (ohne `_unknown`)
- [ ] Zuweisung läuft als Job in der Job-Queue (Dock zeigt Fortschritt)
- [ ] Nach Abschluss: `AssetInstance.person_id` auf Zielperson gesetzt, `fixed_person=True`
- [ ] Dateien physisch in `target_person/photos/` verschoben, `AssetInstance.path` aktualisiert
- [ ] Gesicht auf Asset war `_unknown`: bestes Gesicht → Zielperson, Rest bleibt `_unknown`
- [ ] Per-Asset-Fehler (Datei fehlt, Person gelöscht) loggen + weitermachen, Job bricht nicht ab

---

## Checkliste

### Backend: bulk_assign_person_job.py (neu)

Neue Datei: `backend/photofant/jobs/bulk_assign_person_job.py`

- [ ] `_get_unknown_person_id() -> int | None` — einmalig aus DB lesen
- [ ] `_move_asset_to_person(asset_id: int, target_person_id: int, data_root: Path) -> bool`:
  - Lade `AssetInstance` (non-deleted) für das Asset
  - Lade `Person` für `target_person_id` → `ensure_person_folder(data_root, person)`
  - `photos_dir = person_dir / "photos"` anlegen falls nicht vorhanden
  - Quell-Datei nach `photos_dir / filename` verschieben (`shutil.move` oder copy+delete)
  - `instance.person_id = target_person_id`, `instance.fixed_person = True`, `instance.path = str(new_path)`
  - Commit; bei Fehler: loggen + `return False`
- [ ] `_reassign_faces(asset_id: int, target_person_id: int, unknown_person_id: int) -> None`:
  - Alle `Face`-Zeilen mit `asset_id == asset_id` und `person_id == unknown_person_id` laden
  - Nach `score` absteigend sortieren
  - `faces[0].person_id = target_person_id`; Commit
  - Rest: unverändert
- [ ] `run_bulk_assign_person_job(status: JobStatus, asset_ids: list[int], person_id: int) -> None`:
  ```python
  data_root = get_data_root()
  unknown_id = _get_unknown_person_id()
  total = max(len(asset_ids), 1)

  for index, asset_id in enumerate(asset_ids):
      try:
          moved = await asyncio.to_thread(_move_asset_to_person, asset_id, person_id, data_root)
          if moved and unknown_id is not None:
              await asyncio.to_thread(_reassign_faces, asset_id, person_id, unknown_id)
      except Exception:
          log.exception("Bulk-assign failed for asset %d", asset_id)
      job_queue.update(status, progress=(index + 1) / total, state=JobState.RUNNING)
  ```
- [ ] `enqueue_bulk_assign_person(asset_ids: list[int], person_id: int) -> JobStatus`
- [ ] `JobKind` — neuen Wert `BULK_ASSIGN_PERSON` ergänzen (oder `BULK_EDIT` wiederverwenden):
  🟡 Prüfen ob `JobKind.BULK_EDIT` passt oder ein eigener Kind-Wert sauberer ist.
  Empfehlung: eigener Wert `BULK_ASSIGN` damit Job-Dock die Aktion beschreiben kann.

### Backend: persons.py (Endpoint)

- [ ] Neues Pydantic-Modell:
  ```python
  class BulkAssignRequest(BaseModel):
      asset_ids: list[int]
  ```
- [ ] Neuer Endpoint in `router`:
  ```python
  @router.post("/{person_id}/bulk-assign", response_model=PersonImportResponse)
  async def bulk_assign_to_person(
      person_id: int,
      body: BulkAssignRequest,
      session: DbSession,
  ) -> PersonImportResponse:
      person = session.get(Person, person_id)
      if person is None:
          raise HTTPException(status_code=404, detail="Person not found")
      if person.is_unknown:
          raise HTTPException(status_code=400, detail="Cannot assign to unknown person")
      if not body.asset_ids:
          raise HTTPException(status_code=422, detail="asset_ids must not be empty")
      from photofant.jobs.bulk_assign_person_job import enqueue_bulk_assign_person
      status = await enqueue_bulk_assign_person(body.asset_ids, person_id)
      return PersonImportResponse(job_id=status.id)
  ```

### Frontend: AssignPersonDialog (neu)

- [ ] `ng generate component ui/assign-person-dialog --skip-tests`
  → `assign-person-dialog.ts`, `.html`, `.scss`

- [ ] **assign-person-dialog.ts:**
  ```typescript
  readonly persons = input.required<PersonDto[]>()
  readonly close   = output<void>()
  readonly confirm = output<number>()    // emittiert personId

  protected readonly namedPersons = computed((): PersonDto[] =>
    this.persons().filter((person: PersonDto) => !person.is_unknown)
  )

  protected pick(personId: number): void {
    this.confirm.emit(personId);
  }
  ```

- [ ] **assign-person-dialog.html:** Modal mit scrollbarer Personen-Liste.
  Jeder Eintrag: Portrait-Thumbnail (wenn vorhanden) + Name + Bildanzahl + Klick → `pick()`.
  BEM-Block: `assign-person-dialog`.

- [ ] **assign-person-dialog.scss:** Analog zu `merge-dialog.scss` (gleiche Modal-Optik,
  Liste statt Dropdown).

### Frontend: ui/index.ts

- [ ] `AssignPersonDialog` re-exportieren.

### Frontend: bulk-bar.ts

- [ ] Neue Imports: `PersonDto` aus `@photofant/models`
- [ ] Neues Input:
  ```typescript
  readonly persons = input<PersonDto[]>([])
  ```
- [ ] Neues Output:
  ```typescript
  readonly assignPersonAction = output<void>()
  ```
- [ ] Computed für Sichtbarkeit:
  ```typescript
  protected readonly hasNamedPersons = computed((): boolean =>
    this.persons().some((person: PersonDto) => !person.is_unknown)
  )
  ```
- [ ] Handler:
  ```typescript
  protected openAssignPerson(): void {
    this.assignPersonAction.emit();
  }
  ```

### Frontend: bulk-bar.html

- [ ] Neuen Button einfügen (nur wenn `hasNamedPersons()`):
  ```html
  @if (hasNamedPersons()) {
    <button class="bulk-bar__action" (click)="openAssignPerson()" title="Person zuweisen">
      <pf-icon name="user" [size]="14" />
      <span>Person</span>
    </button>
  }
  ```

### Frontend: person.service.ts

- [ ] Neue Methode:
  ```typescript
  bulkAssignPerson(personId: number, assetIds: number[]): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>(
      `/api/persons/${personId}/bulk-assign`,
      { asset_ids: assetIds },
    );
  }
  ```

### Frontend: galerie.ts

- [ ] `PersonService` via `inject()` ergänzen
- [ ] `persons`-Signal aus Store:
  ```typescript
  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  ```
  + `personsActions` + `personsSelectors` zu den Store-Imports ergänzen
- [ ] `showAssignPersonDialog = signal(false)` ergänzen
- [ ] Handler:
  ```typescript
  protected onBulkAssignPersonOpen(): void {
    this.store.dispatch(personsActions.loadPersons());
    this.showAssignPersonDialog.set(true);
  }

  protected onBulkAssignPersonConfirm(personId: number): void {
    this.showAssignPersonDialog.set(false);
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.personService.bulkAssignPerson(personId, ids)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.store.dispatch(jobsActions.toggleDock());
        this.store.dispatch(galleryActions.clearSelection());
      });
  }

  protected onBulkAssignPersonCancel(): void {
    this.showAssignPersonDialog.set(false);
  }
  ```

### Frontend: galerie.html

- [ ] `AssignPersonDialog` in imports ergänzen
- [ ] `BulkBar` bekommt neuen Input + Output:
  ```html
  <pf-bulk-bar
    [count]="selectedCount()"
    [albums]="albums()"
    [persons]="persons()"
    (close)="onBulkClose()"
    (tagAction)="onBulkTag($event)"
    (addToAlbum)="onAddToAlbum($event)"
    (rerunAction)="onBulkRerunOpen()"
    (editAction)="onBulkEditOpen()"
    (dupeScanAction)="onBulkDupeScan()"
    (trashAction)="onBulkTrash()"
    (assignPersonAction)="onBulkAssignPersonOpen()"
  />
  ```
- [ ] Dialog-Instanz am Ende einfügen:
  ```html
  @if (showAssignPersonDialog()) {
    <pf-assign-person-dialog
      [persons]="persons()"
      (close)="onBulkAssignPersonCancel()"
      (confirm)="onBulkAssignPersonConfirm($event)"
    />
  }
  ```

---

## Doc-Updates

- [ ] Keine neuen Settings-Keys
- [ ] FINDINGS.md: Beobachtungen zur Datei-Bewegung und `JobKind`-Wahl festhalten
