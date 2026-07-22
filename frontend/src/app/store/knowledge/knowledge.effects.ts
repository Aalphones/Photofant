import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { catchError, filter, map, mergeMap, of, switchMap, withLatestFrom } from 'rxjs';
import type { HttpErrorResponse } from '@angular/common/http';
import type { AiAutonomyDto, DomainDto, EntityDto, ImportSuggestionResponse, InterviewSynthesizeResponse, Job, KnowledgeImportResult, KnowledgeInterviewResult, TaskDto } from '@photofant/models';
import { KnowledgeService } from '@photofant/services';
import { jobsActions } from '../jobs/jobs.actions';
import { knowledgeActions } from './knowledge.actions';
import { knowledgeFeature } from './knowledge.reducer';

@Injectable()
export class KnowledgeEffects {
  private readonly actions$ = inject(Actions);
  private readonly store = inject(Store);
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

  readonly loadEntities$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.loadEntities),
      switchMap(() =>
        this.knowledgeService.listEntities().pipe(
          map((entities: EntityDto[]) => knowledgeActions.loadEntitiesSuccess({ entities })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.loadEntitiesFailure({ error: error.message }))
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

  readonly updateEntity$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.updateEntity),
      mergeMap(({ entityId, patch }) =>
        this.knowledgeService.updateEntity(entityId, patch).pipe(
          map((entity: EntityDto) => knowledgeActions.updateEntitySuccess({ entity })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.updateEntityFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly loadTasks$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.loadTasks),
      switchMap(() =>
        this.knowledgeService.listTasks('open').pipe(
          map((tasks: TaskDto[]) => knowledgeActions.loadTasksSuccess({ tasks })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.loadTasksFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly resolveTask$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.resolveTask),
      mergeMap(({ taskId }) =>
        this.knowledgeService.resolveTask(taskId).pipe(
          map((task: TaskDto) => knowledgeActions.resolveTaskSuccess({ task })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.resolveTaskFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly dismissTask$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.dismissTask),
      mergeMap(({ taskId }) =>
        this.knowledgeService.dismissTask(taskId).pipe(
          map((task: TaskDto) => knowledgeActions.dismissTaskSuccess({ task })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.dismissTaskFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // P27 Phase 2 — KI-Vorschlag im Wizard
  readonly loadAiAutonomy$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.loadAiAutonomy),
      switchMap(() =>
        this.knowledgeService.getAiAutonomy().pipe(
          map((autonomy: AiAutonomyDto) => knowledgeActions.loadAiAutonomySuccess({ autonomy })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.loadAiAutonomyFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // Einstellungen › KI — Teil-Update, Server-Antwort trägt den vollen (frischen) Stand zurück
  readonly updateAiAutonomy$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.updateAiAutonomy),
      switchMap(({ patch }) =>
        this.knowledgeService.updateAiAutonomy(patch).pipe(
          map((autonomy: AiAutonomyDto) => knowledgeActions.updateAiAutonomySuccess({ autonomy })),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.updateAiAutonomyFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  readonly requestImportSuggestion$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.requestImportSuggestion),
      // switchMap: nur der zuletzt angeforderte Vorschlag zählt (ein zweiter Klick verwirft den ersten)
      switchMap(({ request }) =>
        this.knowledgeService.requestImportSuggestion(request).pipe(
          map((response: ImportSuggestionResponse) =>
            knowledgeActions.requestImportSuggestionSuccess({ jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.requestImportSuggestionFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // Der Import-Job liefert sein Ergebnis über den Job-Stream (kein eigener Kanal). Hier
  // fischen wir aus dem Strom aller Job-Updates genau den erwarteten Job heraus und wandeln
  // sein Fertig-/Fehler-Signal in ein Vorschlags-Ergebnis um.
  readonly correlateSuggestionJob$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      withLatestFrom(this.store.select(knowledgeFeature.selectSuggestionJobId)),
      filter(([{ job }, jobId]: [{ job: Job }, string | null]) =>
        jobId !== null && job.id === jobId && (job.state === 'done' || job.state === 'error')
      ),
      map(([{ job }]: [{ job: Job }, string | null]) => {
        if (job.state === 'error') {
          return knowledgeActions.importSuggestionFailed({
            error: job.error ?? 'Der KI-Vorschlag ist fehlgeschlagen.',
          });
        }
        if (job.result === null) {
          return knowledgeActions.importSuggestionFailed({
            error: 'Der KI-Vorschlag lieferte kein Ergebnis.',
          });
        }
        return knowledgeActions.importSuggestionReady({
          result: job.result as unknown as KnowledgeImportResult,
        });
      }),
    )
  );

  // P27 Phase 4 — Interview-Mode. Löst den InterviewJob aus (Gemma fasst die Antworten
  // zusammen); das Ergebnis kommt wie beim Import über den Job-Stream.
  readonly requestInterview$ = createEffect(() =>
    this.actions$.pipe(
      ofType(knowledgeActions.requestInterview),
      switchMap(({ request }) =>
        this.knowledgeService.requestInterviewSynthesis(request).pipe(
          map((response: InterviewSynthesizeResponse) =>
            knowledgeActions.requestInterviewSuccess({ jobId: response.job_id })
          ),
          catchError((error: HttpErrorResponse) =>
            of(knowledgeActions.requestInterviewFailure({ error: error.message }))
          ),
        )
      ),
    )
  );

  // Denselben Job-Stream-Korrelations-Trick wie beim Import: den erwarteten Interview-Job
  // aus dem Strom aller Job-Updates herausfischen und done/error in ein Ergebnis wandeln.
  readonly correlateInterviewJob$ = createEffect(() =>
    this.actions$.pipe(
      ofType(jobsActions.upsertJob),
      withLatestFrom(this.store.select(knowledgeFeature.selectInterviewJobId)),
      filter(([{ job }, jobId]: [{ job: Job }, string | null]) =>
        jobId !== null && job.id === jobId && (job.state === 'done' || job.state === 'error')
      ),
      map(([{ job }]: [{ job: Job }, string | null]) => {
        if (job.state === 'error') {
          return knowledgeActions.interviewFailed({
            error: job.error ?? 'Das Interview ist fehlgeschlagen.',
          });
        }
        if (job.result === null) {
          return knowledgeActions.interviewFailed({
            error: 'Das Interview lieferte kein Ergebnis.',
          });
        }
        return knowledgeActions.interviewReady({
          result: job.result as unknown as KnowledgeInterviewResult,
        });
      }),
    )
  );
}
