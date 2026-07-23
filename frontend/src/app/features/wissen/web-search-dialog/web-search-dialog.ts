import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, filter, map, of, startWith, switchMap, take, type Observable } from 'rxjs';
import type {
  DiscoveryApplyResponse,
  DiscoveryResponse,
  Job,
  KnowledgeDiscoveryEntitySuggestion,
  KnowledgeDiscoveryFact,
  KnowledgeDiscoveryResult,
  PersonDto,
} from '@photofant/models';
import { JobsService, KnowledgeService } from '@photofant/services';
import { Icon } from '../../../ui/icon/icon';
import { WizardShell } from '../wizard-shell/wizard-shell';
import type { WizardTarget } from '../interview-dialog/interview-dialog';

type Step = 'pick' | 'searching' | 'results';

interface SearchState {
  status: 'idle' | 'pending' | 'done' | 'error';
  result: KnowledgeDiscoveryResult | null;
  error: string | null;
}

interface ApplyState {
  pending: boolean;
  response: DiscoveryApplyResponse | null;
  error: string | null;
}

const IDLE_SEARCH_STATE: SearchState = { status: 'idle', result: null, error: null };
const IDLE_APPLY_STATE: ApplyState = { pending: false, response: null, error: null };

// P38 Phase 7 — Web-Suche-Wizard (`phase-7-wizards.md` Aufgabe 3). Selbstständige Komponente
// ohne NgRx-Anbindung — gleiches Muster wie die „Ergänzen (KI)"-Ecke in `lore-panel.ts`
// (KnowledgeService + JobsService.streamJobs() direkt), weil der Discovery-Kontrakt keine
// eigenen Store-Actions hat (Phase 3/4 haben keine gebraucht).
@Component({
  selector: 'pf-web-search-dialog',
  imports: [Icon, WizardShell],
  templateUrl: './web-search-dialog.html',
  styleUrl: './web-search-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WebSearchDialog {
  private readonly knowledgeService = inject(KnowledgeService);
  private readonly jobsService = inject(JobsService);

  // Nur Personen mit bestehender Wissens-Notiz sind sinnvolle Ziele — die Recherche schreibt
  // auf eine vorhandene Entity (Kontrakt `entity_id`), es gibt keinen "leg für mich an"-Weg.
  readonly persons = input<PersonDto[]>([]);
  readonly target = input<WizardTarget | null>(null);

  readonly close = output<void>();
  readonly applied = output<{ writtenCount: number }>();

  protected readonly candidatePersons = computed<PersonDto[]>(() =>
    this.persons().filter((person: PersonDto) => person.linked_entity !== null)
  );

  // Direktes Entity-Ziel (aus einer Aufgabe wie "Feld fehlt") gewinnt gegenüber der
  // Personen-Auflösung — deckt auch unverknüpfte, nicht-private Notizen ab, für die es keine
  // Photofant-Person gibt (Erweiterung über die Plan-Basisform von `WizardTarget` hinaus,
  // siehe Report-Back).
  private readonly presetEntityId = computed<string | null>(() => {
    const target = this.target();
    if (target === null) { return null; }
    if (target.entityId !== null) { return target.entityId; }
    if (target.personId !== null) {
      return this.persons().find((person: PersonDto) => person.id === target.personId)?.linked_entity?.id ?? null;
    }
    return null;
  });

  protected readonly hasPreset = computed<boolean>(() => this.presetEntityId() !== null);

  protected readonly pickedPersonId = signal<number | null>(null);

  private readonly resolvedEntityId = computed<string | null>(() => {
    const preset = this.presetEntityId();
    if (preset !== null) { return preset; }
    const picked = this.pickedPersonId();
    if (picked === null) { return null; }
    return this.candidatePersons().find((person: PersonDto) => person.id === picked)?.linked_entity?.id ?? null;
  });

  protected readonly name = computed<string>(() => {
    const target = this.target();
    if (target?.name) { return target.name; }
    const picked = this.pickedPersonId();
    if (picked !== null) {
      return this.candidatePersons().find((person: PersonDto) => person.id === picked)?.name ?? '';
    }
    return '';
  });

  protected readonly hint = signal('');

  protected readonly step = signal<Step>('pick');

  protected readonly checked = signal<Record<number, boolean>>({});
  protected readonly checkedEntities = signal<Record<number, boolean>>({});

  private readonly searchRequested = signal(false);
  private readonly searchState = toSignal(
    toObservable(this.searchRequested).pipe(
      switchMap((requested: boolean): Observable<SearchState> => {
        const entityId = this.resolvedEntityId();
        if (!requested || entityId === null) { return of(IDLE_SEARCH_STATE); }
        const trimmedHint = this.hint().trim();
        const request = trimmedHint.length > 0 ? { entity_id: entityId, hint: trimmedHint } : { entity_id: entityId };
        return this.knowledgeService.requestDiscovery(request).pipe(
          switchMap((response: DiscoveryResponse): Observable<Job> =>
            this.jobsService.streamJobs().pipe(
              filter((job: Job): boolean => job.id === response.job_id && (job.state === 'done' || job.state === 'error')),
              take(1),
            ),
          ),
          map((job: Job): SearchState => {
            if (job.state === 'error' || job.result == null) {
              return { status: 'error', result: null, error: job.error ?? 'Recherche fehlgeschlagen' };
            }
            return { status: 'done', result: job.result as unknown as KnowledgeDiscoveryResult, error: null };
          }),
          startWith({ status: 'pending', result: null, error: null } as SearchState),
          catchError((): Observable<SearchState> => of({ status: 'error', result: null, error: 'Recherche fehlgeschlagen' })),
        );
      }),
    ),
    { initialValue: IDLE_SEARCH_STATE },
  );

  protected readonly searchResult = computed<KnowledgeDiscoveryResult | null>(() => this.searchState().result);
  protected readonly searchError = computed<string | null>(() => this.searchState().error);

  private readonly applyRequested = signal(false);
  private readonly applyState = toSignal(
    toObservable(this.applyRequested).pipe(
      switchMap((requested: boolean): Observable<ApplyState> => {
        const entityId = this.resolvedEntityId();
        const facts = this.acceptedFacts();
        if (!requested || entityId === null) { return of(IDLE_APPLY_STATE); }
        return this.knowledgeService
          .applyDiscovery({ entity_id: entityId, facts, entity_suggestions: this.acceptedEntitySuggestions() })
          .pipe(
            map((response: DiscoveryApplyResponse): ApplyState => ({ pending: false, response, error: null })),
            startWith({ pending: true, response: null, error: null } as ApplyState),
            catchError((): Observable<ApplyState> => of({ pending: false, response: null, error: 'Übernahme fehlgeschlagen' })),
          );
      }),
    ),
    { initialValue: IDLE_APPLY_STATE },
  );

  protected readonly applyResponse = computed<DiscoveryApplyResponse | null>(() => this.applyState().response);
  protected readonly applyPending = computed<boolean>(() => this.applyState().pending);
  protected readonly applyError = computed<string | null>(() => this.applyState().error);

  protected readonly acceptedEntitySuggestions = computed<KnowledgeDiscoveryEntitySuggestion[]>(() => {
    const suggestions = this.searchResult()?.entity_suggestions ?? [];
    return suggestions.filter(
      (_suggestion: KnowledgeDiscoveryEntitySuggestion, index: number) => this.isEntityChecked(index),
    );
  });

  protected readonly acceptedCount = computed<number>(() => {
    const factCount = this.searchResult()?.facts.length ?? 0;
    const acceptedFactCount = Array.from({ length: factCount }, (_unused, index: number) => index)
      .filter((index: number) => this.isChecked(index)).length;
    return acceptedFactCount + this.acceptedEntitySuggestions().length;
  });

  protected readonly canStartSearch = computed<boolean>(() => this.resolvedEntityId() !== null);

  protected readonly canGoBack = computed<boolean>(() => this.step() === 'results' && this.applyResponse() === null);

  protected readonly primaryLabel = computed<string | null>(() => {
    if (this.step() === 'searching') { return null; }
    if (this.step() === 'pick') { return 'Suchen'; }
    if (this.applyResponse() !== null) { return null; }
    return `${this.acceptedCount()} Einträge übernehmen`;
  });

  protected readonly primaryDisabled = computed<boolean>(() => {
    if (this.step() === 'pick') { return !this.canStartSearch(); }
    if (this.step() === 'results') { return this.acceptedCount() === 0 || this.applyPending(); }
    return false;
  });

  constructor() {
    // Sobald der Such-Job fertig ist (done/error), von der Ladeanzeige zur Ergebnisliste
    // wechseln — der Stream selbst kennt keinen Schritt-Begriff, nur den Job-Zustand.
    effect(() => {
      const state = this.searchState();
      if (this.step() === 'searching' && (state.status === 'done' || state.status === 'error')) {
        this.step.set('results');
      }
    });

    // Meldet dem Elternteil sofort, sobald geschrieben wurde (Entities/Aufgaben neu laden,
    // Toast) — der Wizard bleibt trotzdem offen, damit Schritt 3 (Ergebnis) sichtbar bleibt.
    let reported = false;
    effect(() => {
      const response = this.applyResponse();
      if (response !== null && !reported) {
        reported = true;
        this.applied.emit({ writtenCount: response.written_fields.length });
      }
    });
  }

  protected pickPerson(personId: number): void {
    this.pickedPersonId.set(personId);
  }

  protected isChecked(index: number): boolean {
    return this.checked()[index] ?? true;
  }

  protected toggleFact(index: number): void {
    this.checked.update((current: Record<number, boolean>) => ({ ...current, [index]: !this.isChecked(index) }));
  }

  protected isEntityChecked(index: number): boolean {
    return this.checkedEntities()[index] ?? true;
  }

  protected toggleEntity(index: number): void {
    this.checkedEntities.update((current: Record<number, boolean>) => ({
      ...current,
      [index]: !this.isEntityChecked(index),
    }));
  }

  protected confidenceClass(confidence: number): string {
    return confidence >= 0.75 ? 'high' : 'mid';
  }

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  protected createdTitles(entities: { title: string }[]): string {
    return entities.map((entity: { title: string }) => entity.title).join(', ');
  }

  private acceptedFacts(): KnowledgeDiscoveryFact[] {
    const facts = this.searchResult()?.facts ?? [];
    return facts.filter((_fact: KnowledgeDiscoveryFact, index: number) => this.isChecked(index));
  }

  protected onShellBack(): void {
    if (this.step() === 'results') {
      this.step.set('pick');
      this.searchRequested.set(false);
    }
  }

  protected onShellPrimary(): void {
    if (this.step() === 'pick') {
      this.startSearch();
      return;
    }
    if (this.step() === 'results') {
      this.applyAccepted();
    }
  }

  private startSearch(): void {
    if (!this.canStartSearch()) { return; }
    this.checked.set({});
    this.checkedEntities.set({});
    this.step.set('searching');
    this.searchRequested.set(true);
  }

  private applyAccepted(): void {
    this.applyRequested.set(true);
  }
}
