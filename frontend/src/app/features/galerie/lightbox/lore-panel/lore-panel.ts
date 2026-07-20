import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';
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
import type {
  AcceptUpdateSuggestionResponse,
  AiAutonomyDto,
  ChangelogEntryDto,
  EntityRefDto,
  ExplainabilityPayload,
  Job,
  KnowledgeUpdateResult,
  LoreDto,
  PatchJobResponse,
  ResolvedRelationshipDto,
  UpdateSuggestionResponse,
} from '@photofant/models';
import { ExplainabilityPopover, Icon } from '@photofant/ui';

type LoreStatus = 'loading' | 'ready' | 'empty';

interface LoreState {
  status: LoreStatus;
  lores: LoreDto[];
}

// Lore-Panel (P25): zeigt das gebündelte Wissen zum Bild/zur Person rechts in der Lightbox.
// Domänen-agnostisch gehaltene 5-Sektionen-Sicht (Kurzbio · Beziehungen · Franchises ·
// Eigene Bilder · Quellen) — „Rollen"/„Verwandte Entitäten" aus Dok 050 §5 fallen bewusst
// weg, ihre Info steckt in „Beziehungen" (keine Kopplung an domänenspezifische Typ-Strings).
// Dockt als weitere Panel-Sektion an P15s Lightbox-Panel an (kein zweiter Container).
//
// Ein Bild kann mehrere Wissens-Blöcke tragen — einen je abgebildeter, mit Wissen
// verknüpfter Person. Der Korrektur-/Erklär-Zustand ist deshalb nach Entity-id geschlüsselt
// (jeweils genau einer offen zur Zeit), damit bei mehreren Blöcken nicht der falsche editiert
// wird.
@Component({
  selector: 'pf-lore-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ExplainabilityPopover],
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
  // Von außen hochgezählt (Lightbox), wenn eine neu angelegte Entity mit der Person
  // verknüpft wurde — assetId/personId ändern sich dabei nicht, ohne diesen Trigger
  // bliebe das Panel auf dem alten „kein Wissen"-Stand hängen.
  readonly refreshKey = input<number>(0);

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
      toObservable(this.refreshKey),
    ]).pipe(
      switchMap(([assetId, personId]: [number | null, number | null, number, number]): Observable<LoreState> => {
        if (assetId == null && personId == null) {
          return of({ status: 'empty', lores: [] });
        }
        return this.knowledgeService
          .getLore({ assetId, personId })
          .pipe(
            map((lores: LoreDto[]): LoreState => ({
              status: lores.length > 0 ? 'ready' : 'empty',
              lores,
            })),
            startWith({ status: 'loading', lores: [] } as LoreState),
            catchError((error: unknown): Observable<LoreState> => {
              console.error('[LorePanel] Lore konnte nicht geladen werden:', error);
              return of({ status: 'empty', lores: [] });
            }),
          );
      }),
    ),
    { initialValue: { status: 'loading', lores: [] } as LoreState },
  );

  protected readonly status = computed((): LoreStatus => this.state().status);
  protected readonly lores = computed((): LoreDto[] => this.state().lores);

  protected bioFor(lore: LoreDto): string | null {
    const body = lore.entity?.body?.trim();
    return body ? body : null;
  }

  // „Das stimmt nicht" macht nur bei auto/inferred-Werten Sinn — ein user-owned Wert ist
  // bereits die korrigierte Fassung (Ownership ist entity-weit, kein Per-Feld-Owner, siehe
  // KnowledgeService-Docstring).
  protected canCorrectFor(lore: LoreDto): boolean {
    return lore.entity?.owner !== 'user';
  }

  // Beziehungen ohne die Franchise-Ziele — die stehen in ihrer eigenen Sektion. Dedup
  // domänen-agnostisch über die Franchise-ids statt über den Typ-String "Franchise"
  // (P25 Phase-1-Finding: franchises[] enthält Ziele zusätzlich zu relationships[]).
  protected relationshipsFor(lore: LoreDto): ResolvedRelationshipDto[] {
    const franchiseIds = new Set(lore.franchises.map((ref: EntityRefDto) => ref.id));
    return lore.relationships.filter(
      (relationship: ResolvedRelationshipDto) => !franchiseIds.has(relationship.target.id),
    );
  }

  protected trackLore(lore: LoreDto): string {
    return lore.entity?.id ?? '';
  }

  // Korrektur-Zustand — genau eine Bearbeitung offen zur Zeit, geschlüsselt über die
  // Entity-id des gerade editierten Blocks.
  protected readonly correctingEntityId = signal<string | null>(null);
  protected readonly correctingField = signal<string | null>(null);
  protected readonly correctionValue = signal('');
  protected readonly correctionReason = signal('');
  protected readonly correctionPending = signal(false);
  protected readonly correctionError = signal<string | null>(null);

  // Erklär-Popover ebenfalls pro Block geschlüsselt (id des offenen Popovers, sonst null).
  protected readonly correctionExplainOpenId = signal<string | null>(null);
  protected readonly correctionExplainLoading = signal(false);
  protected readonly correctionExplainPayload = signal<ExplainabilityPayload | null>(null);
  private correctionExplainEntityId: string | null = null;

  // ── KI-Ergänzung (P27 Phase 3) — „Ergänzen (KI)" ─────────────────────────
  // Autonomie einmalig laden (dumme, self-contained Komponente ohne Store-Anbindung wie
  // der Rest des Panels — kein Umweg über den Wizard-NgRx-Pfad nötig). Fehler degradieren
  // still zu „aus", der Button bleibt dann versteckt statt einen kaputten Zustand zu zeigen.
  protected readonly updateAutonomy = signal<AiAutonomyDto | null>(null);
  protected readonly updateSuggestionEntityId = signal<string | null>(null);
  protected readonly updateSuggestionPending = signal(false);
  protected readonly updateSuggestionResult = signal<KnowledgeUpdateResult | null>(null);
  protected readonly updateSuggestionError = signal<string | null>(null);
  protected readonly updateAcceptPending = signal(false);

  constructor() {
    this.knowledgeService.getAiAutonomy()
      .pipe(take(1), catchError(() => of(null)))
      .subscribe((autonomy: AiAutonomyDto | null): void => { this.updateAutonomy.set(autonomy); });

    // Schließt offene Korrektur/„Warum geändert?"/KI-Ergänzung-Zustände bei jedem
    // Lore-Reload (Bildwechsel oder frische Korrektur) — sonst zeigt ein Popover/Vorschlag
    // kurz den Stand der vorigen Entity, bis der Entity-Id-Guard beim nächsten Klick nachlädt.
    effect((): void => {
      this.lores();
      this.correctingField.set(null);
      this.correctingEntityId.set(null);
      this.correctionExplainOpenId.set(null);
      this.correctionExplainPayload.set(null);
      this.correctionExplainLoading.set(false);
      this.updateSuggestionEntityId.set(null);
      this.updateSuggestionResult.set(null);
      this.updateSuggestionError.set(null);
      this.updateSuggestionPending.set(false);
    });
  }

  // Dieselbe Bedingung wie „Das stimmt nicht": nur bei auto/inferred-Werten sinnvoll (ein
  // user-owned Wert lehnt einen inferred-Schreibzugriff ohnehin über die Ownership-Prüfung
  // ab). Zusätzlich abgeschaltet, wenn `ai.autonomy.knowledge_update === 'off'`.
  protected canRequestUpdateFor(lore: LoreDto): boolean {
    return this.canCorrectFor(lore) && this.updateAutonomy()?.knowledge_update !== 'off';
  }

  protected requestUpdateSuggestion(entityId: string): void {
    this.updateSuggestionEntityId.set(entityId);
    this.updateSuggestionResult.set(null);
    this.updateSuggestionError.set(null);
    this.updateSuggestionPending.set(true);
    this.knowledgeService.requestUpdateSuggestion({ entity_id: entityId })
      .pipe(
        switchMap((response: UpdateSuggestionResponse): Observable<Job> =>
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
          this.updateSuggestionPending.set(false);
          if (job.state === 'error') {
            this.updateSuggestionError.set(job.error ?? 'Vorschlag fehlgeschlagen');
            return;
          }
          if (job.result == null) {
            this.updateSuggestionError.set('Vorschlag fehlgeschlagen');
            return;
          }
          this.updateSuggestionResult.set(job.result as unknown as KnowledgeUpdateResult);
        },
        error: (): void => {
          this.updateSuggestionPending.set(false);
          this.updateSuggestionError.set('Vorschlag fehlgeschlagen');
        },
      });
  }

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  protected cancelUpdateSuggestion(): void {
    this.updateSuggestionEntityId.set(null);
    this.updateSuggestionResult.set(null);
    this.updateSuggestionError.set(null);
  }

  protected acceptUpdateSuggestion(): void {
    const entityId = this.updateSuggestionEntityId();
    const result = this.updateSuggestionResult();
    const proposal = result?.proposal;
    if (entityId == null || result == null || proposal == null) { return; }

    this.updateAcceptPending.set(true);
    this.updateSuggestionError.set(null);
    this.knowledgeService
      .acceptUpdateSuggestion({ entity_id: entityId, body: proposal.body, reason: result.explainability.reason })
      .pipe(
        switchMap((response: AcceptUpdateSuggestionResponse): Observable<Job> =>
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
          this.updateAcceptPending.set(false);
          if (job.state === 'error') {
            this.updateSuggestionError.set(job.error ?? 'Übernahme fehlgeschlagen');
            return;
          }
          this.updateSuggestionEntityId.set(null);
          this.updateSuggestionResult.set(null);
          this.refreshTick.update((tick: number): number => tick + 1);
        },
        error: (): void => {
          this.updateAcceptPending.set(false);
          this.updateSuggestionError.set('Übernahme fehlgeschlagen');
        },
      });
  }

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

  protected startCorrection(entityId: string, field: string, currentValue: string): void {
    this.correctingEntityId.set(entityId);
    this.correctingField.set(field);
    this.correctionValue.set(currentValue);
    this.correctionReason.set('');
    this.correctionError.set(null);
  }

  protected cancelCorrection(): void {
    this.correctingField.set(null);
    this.correctingEntityId.set(null);
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
    const entityId = this.correctingEntityId();
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
          this.correctingEntityId.set(null);
          this.refreshTick.update((tick: number): number => tick + 1);
        },
        error: (): void => {
          this.correctionPending.set(false);
          this.correctionError.set('Korrektur fehlgeschlagen');
        },
      });
  }

  // ── Explainability „Warum geändert?" (P26 Phase 3) ────────────────────────
  // Dasselbe Popover-Bauteil wie die Empfehlungs-Karten (kein zweites Implementat, AK) —
  // hier gefüttert aus dem Korrektur-Changelog (P25 Phase 3) statt aus Reason-Chains.
  // Sichtbar, sobald ein Feld bereits korrigiert ist (`owner === 'user'`, das Gegenstück
  // zu `canCorrect`); lädt die Historie erst beim ersten Öffnen, danach pro Entity gecacht.

  protected onCorrectionExplainOpen(entityId: string): void {
    this.correctionExplainOpenId.set(entityId);
    if (this.correctionExplainEntityId === entityId && this.correctionExplainPayload() != null) {
      return;
    }
    this.correctionExplainEntityId = entityId;
    this.correctionExplainLoading.set(true);
    this.correctionExplainPayload.set(null);
    this.knowledgeService.getChangelog(entityId)
      .pipe(take(1))
      .subscribe({
        next: (entries: ChangelogEntryDto[]): void => {
          this.correctionExplainLoading.set(false);
          const latest = entries.find((entry: ChangelogEntryDto) => entry.field === 'body') ?? entries[0] ?? null;
          this.correctionExplainPayload.set(this.buildCorrectionPayload(latest));
        },
        error: (): void => {
          this.correctionExplainLoading.set(false);
          this.correctionExplainPayload.set({
            title: 'Korrektur',
            confidencePercent: null,
            reasons: [],
            missing: [],
            meta: [{ label: 'Fehler', value: 'Historie konnte nicht geladen werden' }],
          });
        },
      });
  }

  protected onCorrectionExplainClose(): void {
    this.correctionExplainOpenId.set(null);
  }

  private buildCorrectionPayload(entry: ChangelogEntryDto | null): ExplainabilityPayload {
    if (entry == null) {
      return {
        title: 'Korrektur',
        confidencePercent: null,
        reasons: [],
        missing: [],
        meta: [{ label: 'Historie', value: 'Keine Einträge' }],
      };
    }
    return {
      title: 'Warum geändert?',
      confidencePercent: null,
      reasons: [],
      missing: [],
      meta: [
        { label: 'Grund', value: entry.reason },
        { label: 'Quelle', value: entry.source },
        { label: 'Zeit', value: this.formatChangelogDate(entry.created_at) },
        { label: 'Job', value: entry.job_id },
      ],
    };
  }

  private formatChangelogDate(dateStr: string): string {
    return new Intl.DateTimeFormat('de-DE', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    }).format(new Date(dateStr));
  }
}
