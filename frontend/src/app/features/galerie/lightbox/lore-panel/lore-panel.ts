import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  catchError,
  combineLatest,
  filter,
  map,
  of,
  startWith,
  switchMap,
  take,
  type Observable,
} from 'rxjs';
import { JobsService, KnowledgeService } from '@photofant/services';
import type { EntityRefDto, Job, LoreDto, MediaRefDto, PatchJobResponse, ResolvedRelationshipDto } from '@photofant/models';
import { Icon } from '@photofant/ui';

type LoreStatus = 'loading' | 'ready' | 'empty';

interface LoreState {
  status: LoreStatus;
  lore: LoreDto | null;
}

// Lore-Panel (P25): zeigt das gebündelte Wissen zum Bild/zur Person rechts in der Lightbox.
// Domänen-agnostisch gehaltene 5-Sektionen-Sicht (Kurzbio · Beziehungen · Franchises ·
// Eigene Bilder · Quellen) — „Rollen"/„Verwandte Entitäten" aus Dok 050 §5 fallen bewusst
// weg, ihre Info steckt in „Beziehungen" (keine Kopplung an domänenspezifische Typ-Strings).
// Dockt als weitere Panel-Sektion an P15s Lightbox-Panel an (kein zweiter Container).
@Component({
  selector: 'pf-lore-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './lore-panel.html',
  styleUrl: './lore-panel.scss',
})
export class LorePanel {
  private readonly knowledgeService = inject(KnowledgeService);
  private readonly jobsService = inject(JobsService);

  readonly assetId = input<number | null>(null);
  readonly personId = input<number | null>(null);
  // Ob Wissen hier überhaupt sinnvoll wäre (Bild zeigt Personen) — steuert, ob der
  // „Noch kein Wissen — anlegen"-Zustand erscheint oder das Panel still ausgeblendet bleibt.
  readonly hasPersonContext = input(false);

  readonly entitySelected = output<EntityRefDto>();
  readonly createRequested = output<void>();

  // Bump nach einer erfolgreichen Korrektur (P25 Phase 3) — löst über den `switchMap`
  // unten einen erneuten `getLore`-Read aus, ohne dass der Nutzer die Lightbox schließen muss.
  private readonly refreshTick = signal(0);

  // Lazy: lädt erst, wenn eine der ids gesetzt ist (Lightbox offen). catchError degradiert
  // still zum Leer-Zustand statt das Signal für den Rest der Session zu vergiften.
  private readonly state = toSignal(
    combineLatest([
      toObservable(this.assetId),
      toObservable(this.personId),
      toObservable(this.refreshTick),
    ]).pipe(
      switchMap(([assetId, personId]: [number | null, number | null, number]): Observable<LoreState> => {
        if (assetId == null && personId == null) {
          return of({ status: 'empty', lore: null });
        }
        return this.knowledgeService
          .getLore({ assetId, personId })
          .pipe(
            map((lore: LoreDto): LoreState => ({
              status: lore.entity != null ? 'ready' : 'empty',
              lore,
            })),
            startWith({ status: 'loading', lore: null } as LoreState),
            catchError((error: unknown): Observable<LoreState> => {
              console.error('[LorePanel] Lore konnte nicht geladen werden:', error);
              return of({ status: 'empty', lore: null });
            }),
          );
      }),
    ),
    { initialValue: { status: 'loading', lore: null } as LoreState },
  );

  protected readonly status = computed((): LoreStatus => this.state().status);
  protected readonly entity = computed(() => this.state().lore?.entity ?? null);

  protected readonly bio = computed((): string | null => {
    const body = this.entity()?.body?.trim();
    return body ? body : null;
  });

  // „Das stimmt nicht" macht nur bei auto/inferred-Werten Sinn — ein user-owned Wert ist
  // bereits die korrigierte Fassung (Ownership ist entity-weit, kein Per-Feld-Owner, siehe
  // KnowledgeService-Docstring).
  protected readonly canCorrect = computed((): boolean => this.entity()?.owner !== 'user');

  protected readonly correctingField = signal<string | null>(null);
  protected readonly correctionValue = signal('');
  protected readonly correctionReason = signal('');
  protected readonly correctionPending = signal(false);
  protected readonly correctionError = signal<string | null>(null);

  // Beziehungen ohne die Franchise-Ziele — die stehen in ihrer eigenen Sektion. Dedup
  // domänen-agnostisch über die Franchise-ids statt über den Typ-String "Franchise"
  // (P25 Phase-1-Finding: franchises[] enthält Ziele zusätzlich zu relationships[]).
  protected readonly relationships = computed((): ResolvedRelationshipDto[] => {
    const lore = this.state().lore;
    if (lore == null) {
      return [];
    }
    const franchiseIds = new Set(lore.franchises.map((ref: EntityRefDto) => ref.id));
    return lore.relationships.filter(
      (relationship: ResolvedRelationshipDto) => !franchiseIds.has(relationship.target.id),
    );
  });

  protected readonly franchises = computed((): EntityRefDto[] => this.state().lore?.franchises ?? []);
  protected readonly relatedMedia = computed((): MediaRefDto[] => this.state().lore?.related_media ?? []);
  protected readonly sources = computed((): string[] => this.state().lore?.sources ?? []);

  protected readonly showEmptyState = computed((): boolean =>
    this.status() === 'empty' && this.hasPersonContext(),
  );

  // Ein Ziel ist nur navigierbar, wenn es eine aufgelöste Entity hat; unbekannte Ziele
  // kommen mit leerem Typ zurück (P25 Phase-1-Finding) — dann kein Navigationsziel.
  protected isNavigable(ref: EntityRefDto): boolean {
    return ref.type !== '';
  }

  protected selectEntity(ref: EntityRefDto): void {
    if (this.isNavigable(ref)) {
      this.entitySelected.emit(ref);
    }
  }

  protected requestCreate(): void {
    this.createRequested.emit();
  }

  protected relationTypeLabel(type: string): string {
    return type.replaceAll('_', ' ');
  }

  protected isUrl(source: string): boolean {
    return source.startsWith('http://') || source.startsWith('https://');
  }

  protected sourceLabel(source: string): string {
    try {
      return new URL(source).hostname.replace(/^www\./, '');
    } catch {
      return source;
    }
  }

  protected startCorrection(field: string, currentValue: string): void {
    this.correctingField.set(field);
    this.correctionValue.set(currentValue);
    this.correctionReason.set('');
    this.correctionError.set(null);
  }

  protected cancelCorrection(): void {
    this.correctingField.set(null);
    this.correctionError.set(null);
  }

  protected onCorrectionValueInput(value: string): void {
    this.correctionValue.set(value);
  }

  protected onCorrectionReasonInput(value: string): void {
    this.correctionReason.set(value);
  }

  // Löst den PatchJob aus (P25 Phase 3) und wartet über den SSE-Job-Stream auf
  // done/error (gleiches Muster wie `editor.effects.ts::onRunGenerativePoll$`) — erst
  // dann gilt die Korrektur als übernommen und das Panel lädt die Lore neu.
  protected submitCorrection(): void {
    const field = this.correctingField();
    const entityId = this.entity()?.id;
    const reason = this.correctionReason().trim();
    if (field == null || entityId == null || reason === '') {
      return;
    }

    this.correctionPending.set(true);
    this.correctionError.set(null);
    this.knowledgeService
      .patchEntity(entityId, { field, value: this.correctionValue(), reason })
      .pipe(
        switchMap((response: PatchJobResponse): Observable<Job> =>
          this.jobsService.streamJobs().pipe(
            filter((job: Job): boolean =>
              job.id === response.job_id && (job.state === 'done' || job.state === 'error'),
            ),
            take(1),
          ),
        ),
      )
      .subscribe({
        next: (job: Job): void => {
          this.correctionPending.set(false);
          if (job.state === 'error') {
            this.correctionError.set(job.error ?? 'Korrektur fehlgeschlagen');
            return;
          }
          this.correctingField.set(null);
          this.refreshTick.update((tick: number): number => tick + 1);
        },
        error: (): void => {
          this.correctionPending.set(false);
          this.correctionError.set('Korrektur fehlgeschlagen');
        },
      });
  }
}
