# Phase 2 — Frontend Store: Persistenz für Gruppen-Zuweisung

**Tier:** standard
**Status:** pending
**Voraussetzung:** Phase 1 abgeschlossen (Backend liefert `group_name`/`created_at`)

---

## Kontext (vorher lesen)

- `frontend/src/app/models/person.model.ts` — `PersonDto`
- `frontend/src/app/store/persons/persons.actions.ts`
- `frontend/src/app/store/persons/persons.effects.ts`
- `frontend/src/app/store/persons/persons.reducer.ts`
- `frontend/src/app/services/person.service.ts` — bestehende `renamePerson`-Methode als Vorlage

🟡 Suche/Sortierung/Gruppen-Filter/View-Modus sind **kein** Store-State (siehe
Risiken in README) — diese Phase deckt ausschließlich die persistente
Gruppen-Zuweisung ab.

---

## Abnahme-Kriterien

- [ ] `store.dispatch(personsActions.setPersonGroup({ id, groupName }))` persistiert die Gruppe im Backend
- [ ] Nach Erfolg: Person im Store aktualisiert (`group_name` sichtbar in `selectAll`)
- [ ] Fehlerfall: `error`-State gesetzt, keine optimistische UI-Änderung, die hängen bleibt

---

## Checkliste

### models/person.model.ts

- [ ] `PersonDto` um `group_name: string | null` und `created_at: string | null` erweitern

### services/person.service.ts

- [ ] Neue Methode (oder bestehende `renamePerson` umbauen, falls Backend-PATCH vereinheitlicht wurde):
  ```typescript
  setPersonGroup(id: number, groupName: string | null): Observable<PersonDto> {
    return this.http.patch<PersonDto>(`/api/persons/${id}`, { group_name: groupName });
  }
  ```

### store/persons/persons.actions.ts

- [ ] Neue Events ergänzen:
  ```typescript
  'Set Person Group':         props<{ id: number; groupName: string | null }>()
  'Set Person Group Success': props<{ person: PersonDto }>()
  'Set Person Group Failure': props<{ error: string }>()
  ```

### store/persons/persons.effects.ts

- [ ] `setPersonGroup$`-Effect (analog `renamePerson$`):
  ```typescript
  readonly setPersonGroup$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.setPersonGroup),
      switchMap(({ id, groupName }) =>
        this.personService.setPersonGroup(id, groupName).pipe(
          map((person: PersonDto) => personsActions.setPersonGroupSuccess({ person })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.setPersonGroupFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
  ```

### store/persons/persons.reducer.ts

- [ ] `on(personsActions.setPersonGroupSuccess, ...)`:
  ```typescript
  on(personsActions.setPersonGroupSuccess, (state: PersonsState, { person }) =>
    adapter.updateOne({ id: person.id, changes: person }, state)
  ),
  on(personsActions.setPersonGroupFailure, (state: PersonsState, { error }) => ({
    ...state,
    error,
  })),
  ```

---

## Doc-Updates

- [ ] `docs/clients.md` — `PersonService.setPersonGroup` ergänzen, falls die Datei existiert
