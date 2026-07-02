# Phase 6 — Person löschen

**Tier:** standard
**Status:** pending
**Voraussetzung:** keine (unabhängig von Phase 2-5, kann vorgezogen werden)

Fasst zwei Dinge an: den neuen Löschen-Flow **und** einen Bugfix in der bereits
bestehenden `merge_persons()` — beide teilen sich dieselbe Ursache (verwaiste
`SmartTrigger.person_id`-Referenz), also gemeinsam in einem Rutsch über einen
gemeinsamen Helper gefixt statt den Merge-Fall separat nachzuziehen.

---

## Kontext (vorher lesen)

- `backend/photofant/media/person_folders.py` — `merge_persons()` (Zeilen 647-751) ist die
  fast-fertige Vorlage: Faces + Instances physisch zu einem Zielordner bewegen, Quellordner
  danach löschen. Delete = Merge in Richtung `_unknown`, **ohne** Namensübernahme und mit
  zurückgesetztem `fixed_person`. `merge_persons()` bekommt in dieser Phase zusätzlich einen
  eigenständigen Bugfix (SmartTrigger-Repointing, siehe unten) — keine Kopie, sondern eine
  kleine Ergänzung an bestehendem, bereits produktivem Code.
- `backend/photofant/media/person_folders.py` — `_safe_move()`, `ensure_person_folder()`,
  `person_folder_name()` — bestehende Bausteine, 1:1 wiederverwendet.
- `backend/photofant/api/persons.py` — `merge_persons_endpoint` (Zeilen 206-243) als Vorlage
  für Route-Aufbau (Person laden, 404/400-Guards, `asyncio.to_thread`, `session.commit()`).
- `frontend/src/app/features/personen/merge-dialog/` — Vorlage für einen eigenständigen
  Bestätigungs-Dialog (Struktur `.ts`/`.html`/`.scss`, `confirm`-Step als Layout-Vorbild).
- `frontend/src/app/features/personen/person-card/person-card.ts` + `.html` — Hover-Actions
  (Rename/Split/Dupe-Check/Import/Reveal), neue Aktion reiht sich dort ein.
- `frontend/src/app/store/persons/persons.actions.ts` + `persons.effects.ts` — `mergePersons`
  als 1:1-Vorlage für Action/Effect-Paar inkl. Reload-Effect.
- `backend/photofant/collections/engine.py` (Zeilen 76-85, `_trigger_match_ids`) — `person`-
  Trigger matchen über `AssetInstance.person_id == trigger.person_id`. Ein `SmartTrigger` mit
  `person_id`, der auf eine verschwundene Person zeigt, crasht nicht (SQLite erzwingt hier keine
  Fremdschlüssel), matcht aber für immer nichts mehr — stiller Datenrest. Betrifft **beide**
  Fälle: löschen (Person weg, keine Nachfolge) und mergen (Person weg, Fotos leben unter
  `into_person_id` weiter).
- `backend/photofant/jobs/collections_job.py` — `enqueue_reevaluate_assets()`, bereits von
  `merge_persons_endpoint` genutzt (`api/persons.py` Zeile 236-238), um `collection_item`
  nach einer Personen-Änderung neu abzugleichen. Für den Merge-Fall reicht der **bestehende**
  Reevaluate-Call unverändert — er läuft schon über alle Assets von `into_person_id`, das
  deckt auch das frisch repointete Trigger-Ergebnis mit ab.

---

## Abnahme-Kriterien

- [ ] Löschen einer Person entfernt den Datenbank-Eintrag vollständig
- [ ] Der physische Ordner der Person (inkl. `photos/ favourites/ faces/ edits/`) ist danach weg
- [ ] Alle Fotos, Edits und Gesichter der Person landen unversehrt im `_unknown`-Ordner (Dateien gehen nie verloren)
- [ ] Ein Foto, das in `_unknown` bereits eine Instanz für dasselbe Asset hat (Duplikat), wird sauber dedupliziert statt einen Datei-Konflikt zu erzeugen
- [ ] Die Person „Unbekannt" selbst kann nicht gelöscht werden (400)
- [ ] Verschobene Fotos sind wieder für Clustering/Incremental-Match verfügbar (`fixed_person` wird beim Verschieben nach `_unknown` zurückgesetzt — sonst blockieren sie sich selbst dauerhaft)
- [ ] Ein Smart-Album-Trigger, der auf die gelöschte Person zeigt, wird beim Löschen mit entfernt statt ins Leere zu zeigen; betroffene Smart-Alben werden danach automatisch neu bewertet (keine toten `collection_item`-Reste)
- [ ] **Bugfix `merge_persons`:** Ein Smart-Album-Trigger, der auf die aufgelöste (`from_id`) Person zeigt, wird beim Merge auf die Zielperson (`into_id`) umgebogen statt tot liegen zu bleiben — die Fotos, für die der Trigger stand, existieren ja unter der Zielperson weiter
- [ ] Löschen ist nur über einen expliziten Bestätigungsdialog erreichbar, der in Klartext sagt: Fotos werden **nicht** gelöscht, sondern wandern nach „Unbekannt"; die Person selbst ist danach weg
- [ ] Dialog zeigt Personenname/Avatar + Bilderzahl, damit klar ist, wer gelöscht wird

---

## Checkliste

### media/person_folders.py — gemeinsamer Helper `_resolve_person_smart_triggers()`

- [ ] Neue private Funktion, **oberhalb** von `merge_persons` und `delete_person` platziert
      (beide rufen sie auf):
  ```python
  def _resolve_person_smart_triggers(
      session: Session,
      person_id: int,
      successor_id: int | None,
  ) -> int:
      """Keep SmartTrigger.person_id from silently going stale.

      SQLite doesn't enforce the FK on SmartTrigger.person_id, so a trigger
      pointing at a person that was merged away or deleted would otherwise just
      stop matching forever — no error, just a dead trigger.

      successor_id=None → the person is gone with no replacement (delete):
        remove the trigger, there's nothing left to point at.
      successor_id set  → the identity lives on under another person (merge):
        repoint the trigger instead of losing it.

      Returns the number of triggers touched.
      """
      triggers = session.scalars(
          select(SmartTrigger).where(
              SmartTrigger.type == "person",
              SmartTrigger.person_id == person_id,
          )
      ).all()
      for trigger in triggers:
          if successor_id is None:
              session.delete(trigger)
          else:
              trigger.person_id = successor_id
      if triggers:
          log.info(
              "Smart-album trigger(s) referencing person %d %s (%d)",
              person_id,
              "removed" if successor_id is None else f"repointed to person {successor_id}",
              len(triggers),
          )
      session.flush()
      return len(triggers)
  ```

### media/person_folders.py — `delete_person()`

- [ ] Neue Funktion, analog `merge_persons`, aber Ziel ist immer `_unknown`, keine Namensübernahme,
      plus Aufräumen verwaister Smart-Album-Trigger über den neuen Helper:
  ```python
  def delete_person(
      session: Session,
      person_id: int,
      data_root: Path,
  ) -> dict[str, object]:
      """Delete a person completely — faces and photos move to _unknown, folder + row are gone.

      Unlike merge_persons (name carry-over, fixed_person untouched), a deleted
      person's assignments are dissolved: nothing survives except the raw files,
      which land back in the catch-all, free to be re-matched by clustering.
      Any smart-album trigger pointing at this person is removed too — otherwise
      it would silently stop matching forever (SQLite enforces no FK here).

      Returns {faces_moved, instances_moved, asset_ids} — asset_ids is every asset
      touched, for the caller to trigger a smart-album re-evaluation.
      """
      person = session.get(Person, person_id)
      if person is None:
          raise ValueError(f"Person {person_id} not found")
      if person.is_unknown:
          raise ValueError("Cannot delete the unknown person")

      unknown_person = session.scalar(select(Person).where(Person.is_unknown.is_(True)))
      if unknown_person is None:
          raise ValueError("No _unknown person found — database inconsistent")

      unknown_dir = ensure_person_folder(data_root, unknown_person)
      affected_asset_ids: set[int] = set()

      faces = session.scalars(select(Face).where(Face.person_id == person_id)).all()
      faces_moved = 0
      for face in faces:
          face.person_id = unknown_person.id
          if face.asset_id is not None:
              affected_asset_ids.add(face.asset_id)
          old_crop = Path(face.crop_path)
          new_crop = unknown_dir / "faces" / old_crop.name
          try:
              final = _safe_move(old_crop, new_crop)
              face.crop_path = str(final.resolve())
          except FileNotFoundError:
              log.warning("Face crop %s missing while deleting person %d — skipping", old_crop, person_id)
          faces_moved += 1
      session.flush()

      instances = session.scalars(
          select(AssetInstance).where(
              AssetInstance.person_id == person_id,
              AssetInstance.deleted_at.is_(None),
          )
      ).all()

      instances_moved = 0
      for instance in instances:
          affected_asset_ids.add(instance.asset_id)
          existing_target = session.scalar(
              select(AssetInstance).where(
                  AssetInstance.asset_id == instance.asset_id,
                  AssetInstance.person_id == unknown_person.id,
                  AssetInstance.deleted_at.is_(None),
              )
          )
          if existing_target is not None:
              # _unknown already has this asset — drop the duplicate instance/file.
              old_path = Path(instance.path)
              if old_path.exists():
                  old_path.unlink()
              session.delete(instance)
              instances_moved += 1
              continue

          subfolder = "favourites" if instance.favourite else "photos"
          old_path = Path(instance.path)
          new_path = unknown_dir / subfolder / old_path.name
          try:
              final = _safe_move(old_path, new_path)
              instance.person_id = unknown_person.id
              instance.path = str(final.resolve())
              instance.fixed_person = False  # release for future clustering/matching
              instances_moved += 1
          except FileNotFoundError:
              log.warning("Instance file %s missing while deleting person %d — skipping", old_path, person_id)

      session.flush()

      # No successor — the identity is gone, any person-trigger pointing here dies with it.
      _resolve_person_smart_triggers(session, person_id, None)

      person_dir = data_root / person_folder_name(person)
      session.delete(person)
      session.flush()

      if person_dir.exists():
          shutil.rmtree(str(person_dir), ignore_errors=True)
          log.info("Removed person folder %s", person_dir)

      log.info(
          "Deleted person %d: %d faces + %d instances moved to _unknown",
          person_id, faces_moved, instances_moved,
      )
      return {
          "faces_moved": faces_moved,
          "instances_moved": instances_moved,
          "asset_ids": list(affected_asset_ids),
      }
  ```
- [ ] `shutil` ist bereits am Dateikopf importiert — kein neuer Import nötig
- [ ] Import-Zeile am Dateikopf um `SmartTrigger` erweitern:
  ```python
  from photofant.db.models import Asset, AssetInstance, Face, Person, SmartTrigger
  ```

### media/person_folders.py — `merge_persons()` (Bugfix, bestehende Funktion)

Nachbarstellen-Fehler derselben Ursache — Zeilen 731-745 (der `if remaining == 0 and not
from_person.is_unknown:`-Block, direkt vor dem `session.delete(from_person)`) bekommen den
Helper-Aufruf **davor**, damit der Trigger noch existiert, wenn er umgebogen wird:

- [ ] Einfügen, bevor `from_person` gelöscht wird:
  ```python
  if remaining == 0 and not from_person.is_unknown:
      _resolve_person_smart_triggers(session, from_person_id, into_person_id)

      from_dir = data_root / person_folder_name(from_person)
      session.delete(from_person)
      session.flush()
      if from_dir.exists():
          import shutil as _shutil
          _shutil.rmtree(str(from_dir), ignore_errors=True)
          log.info("Removed empty person folder %s", from_dir)
  ```
- [ ] Bewusst **nur** innerhalb dieses `if`-Blocks: läuft der Merge nur teilweise durch
      (`remaining != 0`, z.B. weil eine Instance-Datei fehlte), existiert `from_person`
      danach weiter — der Trigger darf dann nicht umgebogen werden, die Person lebt ja noch
- [ ] Kein neuer Reevaluate-Call nötig — `merge_persons_endpoint` (`api/persons.py`
      Zeilen 230-238) reevaluiert bereits alle Assets von `into_id`, das deckt auch das
      Ergebnis des umgebogenen Triggers ab

### api/persons.py — `DELETE /{person_id}`

- [ ] `DeleteResultDto` (identisch zu `MergeResultDto` — kann alternativ direkt wiederverwendet werden):
  ```python
  class DeleteResultDto(BaseModel):
      faces_moved: int
      instances_moved: int
  ```
- [ ] Route — nach dem Commit die betroffenen Assets neu bewerten lassen (analog
      `merge_persons_endpoint`, Zeilen 230-238), damit verwaiste `collection_item`-Reste aus
      Smart-Alben verschwinden, deren Trigger gerade mit gelöscht wurde:
  ```python
  @router.delete("/{person_id}", response_model=DeleteResultDto)
  async def delete_person_endpoint(person_id: int, session: DbSession) -> DeleteResultDto:
      from photofant.config import get_data_root
      from photofant.media.person_folders import delete_person

      person = session.get(Person, person_id)
      if person is None:
          raise HTTPException(status_code=404, detail="Person not found")
      if person.is_unknown:
          raise HTTPException(status_code=400, detail="Cannot delete the unknown person")

      data_root = get_data_root()
      result = await asyncio.to_thread(delete_person, session, person_id, data_root)
      session.commit()
      log.info("Deleted person %d", person_id)

      asset_ids = result.pop("asset_ids", [])
      if asset_ids:
          from photofant.jobs.collections_job import enqueue_reevaluate_assets
          asyncio.ensure_future(enqueue_reevaluate_assets(asset_ids))

      return DeleteResultDto(**result)
  ```

### Frontend — Store (persons.actions.ts / persons.effects.ts)

- [ ] Neue Actions (Ergebnis-Typ: bestehendes `MergeResult` wiederverwenden, gleiche Form):
  ```typescript
  'Delete Person':         props<{ id: number }>(),
  'Delete Person Success': props<{ result: MergeResult }>(),
  'Delete Person Failure': props<{ error: string }>(),
  ```
- [ ] Effect analog `mergePersons$`/`reloadAfterMerge$`:
  ```typescript
  readonly deletePerson$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.deletePerson),
      mergeMap(({ id }) =>
        this.personService.deletePerson(id).pipe(
          map((result: MergeResult) => personsActions.deletePersonSuccess({ result })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.deletePersonFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterDelete$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.deletePersonSuccess),
      map(() => personsActions.loadPersons()),
    )
  );
  ```

### Frontend — person.service.ts

- [ ] Neue Methode:
  ```typescript
  deletePerson(id: number): Observable<MergeResult> {
    return this.http.delete<MergeResult>(`/api/persons/${id}`);
  }
  ```

### Frontend — delete-person-dialog (neu, `features/personen/delete-person-dialog/`)

- [ ] `ng generate component features/personen/delete-person-dialog --skip-tests`
- [ ] Struktur analog `merge-dialog`, aber nur der `confirm`-Step (kein Auswahl-Flow):
  ```typescript
  export class DeletePersonDialog {
    readonly person = input.required<PersonDto>();
    readonly close = output<void>();
    readonly confirmDelete = output<number>();

    protected onConfirm(): void {
      this.confirmDelete.emit(this.person().id);
    }

    protected onBackdrop(event: MouseEvent): void {
      if ((event.target as HTMLElement).classList.contains('delete-person-dialog__backdrop')) {
        this.close.emit();
      }
    }
  }
  ```
- [ ] Template — Klartext-Warnung, keine Fachbegriffe:
  ```html
  <div class="delete-person-dialog__backdrop" (click)="onBackdrop($event)">
    <div class="delete-person-dialog__card">
      <div class="delete-person-dialog__header">
        <h3>Person löschen</h3>
        <button (click)="close.emit()"><pf-icon name="x" [size]="18" /></button>
      </div>
      <div class="delete-person-dialog__body">
        <!-- Avatar + Name + count(), analog merge-dialog__confirm-person -->
        <p>
          <strong>{{ person().name }}</strong> ({{ person().count }} Bilder) wird gelöscht.
          Die Fotos bleiben erhalten und wandern zu „Unbekannt" — nur die Person
          und ihr Ordner sind danach weg.
        </p>
      </div>
      <div class="delete-person-dialog__footer">
        <button (click)="close.emit()">Abbrechen</button>
        <button class="delete-person-dialog__btn--danger" (click)="onConfirm()">
          <pf-icon name="trash" [size]="14" /> Löschen
        </button>
      </div>
    </div>
  </div>
  ```
- [ ] `.scss` analog `merge-dialog.scss` (Backdrop/Card/Header/Footer), Löschen-Button in Warnfarbe

### person-card.ts / .html — Löschen-Aktion

- [ ] Neuer Output: `deleteClick = output<void>()`
- [ ] Neuer Handler analog `onSplitClick`:
  ```typescript
  protected onDeleteClick(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsVisible.set(false);
    this.deleteClick.emit();
  }
  ```
- [ ] Neuer Hover-Button in der Actions-Leiste (`!person().is_unknown`-Block, letzter Button):
  ```html
  <button
    class="person-card__hover-btn person-card__hover-btn--danger"
    (click)="onDeleteClick($event)"
    aria-label="Person löschen"
    title="Person löschen"
  >
    <pf-icon name="trash" [size]="14" />
  </button>
  ```
- [ ] `.scss`: `--danger`-Modifier (rötlicher Hover, unterscheidet sich sichtbar von den übrigen Buttons)

### personen.ts / personen.html — Verdrahtung

- [ ] Signal + Handler:
  ```typescript
  protected readonly deletePersonTarget = signal<PersonDto | null>(null);

  protected onDeleteClick(person: PersonDto): void {
    this.deletePersonTarget.set(person);
  }

  protected onConfirmDelete(personId: number): void {
    this.store.dispatch(personsActions.deletePerson({ id: personId }));
    this.deletePersonTarget.set(null);
  }
  ```
- [ ] `<pf-person-card>`: `(deleteClick)="onDeleteClick(person)"` ergänzen
- [ ] Dialog einbinden:
  ```html
  @if (deletePersonTarget(); as target) {
    <pf-delete-person-dialog
      [person]="target"
      (close)="deletePersonTarget.set(null)"
      (confirmDelete)="onConfirmDelete($event)"
    />
  }
  ```
- [ ] `DeletePersonDialog` in `imports: [...]` der Komponente ergänzen

---

## Doc-Updates

- [ ] `docs/routes.md` — `DELETE /api/persons/{id}` ergänzen, inkl. Nebeneffekt (löscht
      zugehörige `person`-Smart-Trigger, stößt Reevaluate für betroffene Assets an)
- [ ] `docs/code-map.md` — `delete-person-dialog` unter `features/personen/` ergänzen
