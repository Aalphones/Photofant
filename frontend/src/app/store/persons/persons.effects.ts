import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap, mergeMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { PersonDto, MergeResult, SplitResult } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { personsActions } from './persons.actions';

@Injectable()
export class PersonsEffects {
  private readonly actions$ = inject(Actions);
  private readonly personService = inject(PersonService);

  readonly loadPersons$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.loadPersons),
      switchMap(() =>
        this.personService.getPersons().pipe(
          map((persons: PersonDto[]) => personsActions.loadPersonsSuccess({ persons })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.loadPersonsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly renamePerson$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.renamePerson),
      mergeMap(({ id, name }) =>
        this.personService.renamePerson(id, name).pipe(
          map((person: PersonDto) => personsActions.renamePersonSuccess({ person })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.renamePersonFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly mergePersons$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.mergePersons),
      mergeMap(({ fromId, intoId }) =>
        this.personService.mergePersons(fromId, intoId).pipe(
          map((result: MergeResult) => personsActions.mergePersonsSuccess({ result })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.mergePersonsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterMerge$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.mergePersonsSuccess),
      map(() => personsActions.loadPersons()),
    )
  );

  readonly splitPerson$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.splitPerson),
      mergeMap(({ personId, faceIds }) =>
        this.personService.splitPerson(personId, faceIds).pipe(
          map((result: SplitResult) => personsActions.splitPersonSuccess({ result })),
          catchError((error: HttpErrorResponse) =>
            of(personsActions.splitPersonFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly reloadAfterSplit$ = createEffect(() =>
    this.actions$.pipe(
      ofType(personsActions.splitPersonSuccess),
      map(() => personsActions.loadPersons()),
    )
  );
}
