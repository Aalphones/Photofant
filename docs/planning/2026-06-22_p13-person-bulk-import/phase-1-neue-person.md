# Phase 1 — Neue Person anlegen (Personen-UI + NgRx)

**Tier:** standard
**Status:** pending

---

## Kontext (vorher lesen)

- `frontend/src/app/features/personen/personen.ts` — Personen-Seite
- `frontend/src/app/features/personen/personen.html`
- `frontend/src/app/store/persons/persons.actions.ts`
- `frontend/src/app/store/persons/persons.effects.ts`
- `frontend/src/app/store/persons/persons.reducer.ts`
- `frontend/src/app/services/person.service.ts` — `createPerson()` bereits vorhanden ✅

---

## Abnahme-Kriterien

- [ ] „Neue Person"-Button in der Personen-Toolbar sichtbar
- [ ] Dialog öffnet sich: Name-Eingabe + Bestätigen/Abbrechen
- [ ] Leerer Name → Bestätigen-Button disabled, kein API-Call
- [ ] Nach Bestätigung: neue Person erscheint in der Personen-Liste
- [ ] Nach Bestätigung: Galerie öffnet sich mit Personen-Filter auf die neue Person gesetzt

---

## Checkliste

### persons.actions.ts

- [ ] 3 neue Events in `createActionGroup` ergänzen:
  ```typescript
  'Create Person':         props<{ name: string }>()
  'Create Person Success': props<{ person: PersonDto }>()
  'Create Person Failure': props<{ error: string }>()
  ```

### persons.effects.ts

- [ ] `createPerson$`-Effect ergänzen — ruft `personService.createPerson(name)`:
  ```typescript
  readonly createPerson$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.createPerson),
      switchMap(({ name }) =>
        this.personService.createPerson(name).pipe(
          map((person: PersonDto) => personsActions.createPersonSuccess({ person })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.createPersonFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
  ```
- [ ] `navigateAfterCreate$`-Effect ergänzen — nach `createPersonSuccess` in Galerie navigieren:
  ```typescript
  readonly navigateAfterCreate$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.createPersonSuccess),
      tap(({ person }) => {
        this.store.dispatch(filtersActions.setPersonId({ personId: person.id }));
        void this.router.navigate(['/galerie']);
      }),
    ),
    { dispatch: false }
  );
  ```
  Imports ergänzen: `Router`, `tap`, `Store`, `filtersActions`.

### persons.reducer.ts

- [ ] `on(personsActions.createPersonSuccess, ...)` — neue Person an `ids`/`entities` anhängen:
  ```typescript
  on(personsActions.createPersonSuccess, (state, { person }) =>
    personsAdapter.addOne(person, state)
  ),
  ```

### CreatePersonDialog-Komponente (neu)

- [ ] `ng generate component features/personen/create-person-dialog --skip-tests`
  → erzeugt `create-person-dialog.ts`, `.html`, `.scss`
- [ ] **create-person-dialog.ts:**
  ```typescript
  close   = output<void>()
  confirm = output<string>()    // emittiert den Namen

  protected readonly nameValue = signal('')

  protected readonly canConfirm = computed((): boolean =>
    this.nameValue().trim().length > 0
  )

  protected onConfirm(): void {
    const name = this.nameValue().trim();
    if (!name) { return; }
    this.confirm.emit(name);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && this.canConfirm()) { this.onConfirm(); }
    if (event.key === 'Escape') { this.close.emit(); }
  }
  ```
- [ ] **create-person-dialog.html:** Modal mit Name-Input, Bestätigen-Button (disabled wenn !canConfirm()), Schließen-Button.
  BEM-Block: `create-person-dialog`
- [ ] **create-person-dialog.scss:** Analog zu `merge-dialog.scss` stylen (gleiche Modal-Optik).

### personen.ts

- [ ] `CreatePersonDialog` importieren + in `imports: []` aufnehmen
- [ ] `showCreateDialog = signal(false)` ergänzen
- [ ] Handler ergänzen:
  ```typescript
  protected onCreatePerson(name: string): void {
    this.store.dispatch(personsActions.createPerson({ name }));
    this.showCreateDialog.set(false);
  }
  ```

### personen.html

- [ ] „Neue Person"-Button in `personen__toolbar` neben „Zusammenführen":
  ```html
  <button class="personen__action-btn" (click)="showCreateDialog.set(true)">
    <pf-icon name="plus" [size]="14" />
    Neue Person
  </button>
  ```
- [ ] `CreatePersonDialog`-Instanz am Ende des Templates einfügen:
  ```html
  @if (showCreateDialog()) {
    <pf-create-person-dialog
      (close)="showCreateDialog.set(false)"
      (confirm)="onCreatePerson($event)"
    />
  }
  ```
- [ ] „Noch keine Personen"-Leerstate: ebenfalls „Neue Person"-Button anzeigen (gleiche Action).

### Store-Barrel (persons/index.ts)

- [ ] Prüfen, ob neue Actions automatisch re-exportiert werden — falls `index.ts` explizit listed, neue Action-Names ergänzen.

---

## Doc-Updates

- [ ] Keine neuen Settings-Keys → settings.json bleibt unverändert
- [ ] `docs/clients.md` falls vorhanden: `PersonService.createPerson` ist bereits dokumentiert, kein Update nötig
