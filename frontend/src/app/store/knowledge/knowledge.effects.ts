import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, mergeMap, of, switchMap } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { DomainDto, EntityDto } from '@photofant/models';
import { KnowledgeService } from '@photofant/services';
import { knowledgeActions } from './knowledge.actions';

@Injectable()
export class KnowledgeEffects {
  private readonly actions$ = inject(Actions);
  private readonly knowledgeService = inject(KnowledgeService);

  readonly loadDomains$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.loadDomains),
      switchMap(() =>
        this.knowledgeService.listDomains().pipe(
          map((domains: DomainDto[]) => knowledgeActions.loadDomainsSuccess({ domains })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.loadDomainsFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly createEntity$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.createEntity),
      mergeMap(({ request }) =>
        this.knowledgeService.createEntity(request).pipe(
          map((entity: EntityDto) => knowledgeActions.createEntitySuccess({ entity })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.createEntityFailure({ error: error.message }))
          ),
        )
      ),
    )
  );
}
