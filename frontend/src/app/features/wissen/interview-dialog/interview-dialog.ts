import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import type {
  CreateEntityRequest,
  DomainDto,
  EntityType,
  InterviewAnswer,
  InterviewSynthesizeRequest,
  KnowledgeInterviewResult,
} from '@photofant/models';
import { Icon } from '../../../ui/icon/icon';

// Fester Fragen-Satz für den geführten Interview-Dialog (kein freies Chat, AK Phase 4).
// Der Name wird im Intro-Schritt erfasst, die Fragen bauen darauf auf. Person und Haustier
// bekommen leicht andere Fragen; leere Antworten sind erlaubt (das Backend überspringt sie).
type DialogPhase = 'stepper' | 'synthesizing' | 'summary';

@Component({
  selector: 'pf-interview-dialog',
  imports: [Icon],
  templateUrl: './interview-dialog.html',
  styleUrl: './interview-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterviewDialog {
  // Nur private Domänen kommen für das Interview infrage (Konzept-ADR-009). Der Aufrufer
  // reicht alle Domänen herein; hier wird auf die privaten gefiltert.
  readonly domains = input.required<DomainDto[]>();
  readonly isSaving = input<boolean>(false);
  readonly saveError = input<string | null>(null);
  readonly loading = input<boolean>(false);
  readonly result = input<KnowledgeInterviewResult | null>(null);
  readonly error = input<string | null>(null);

  readonly close = output<void>();
  readonly requestInterview = output<InterviewSynthesizeRequest>();
  readonly save = output<CreateEntityRequest>();

  protected readonly privateDomains = computed<DomainDto[]>(() =>
    this.domains().filter((domain: DomainDto) => domain.private)
  );

  protected readonly selectedDomain = signal('');
  protected readonly selectedType = signal('');
  protected readonly name = signal('');
  protected readonly nameTouched = signal(false);

  protected readonly phase = signal<DialogPhase>('stepper');
  // 0 = Intro (Name + Typ), 1..N = je eine Frage.
  protected readonly stepIndex = signal(0);
  protected readonly answers = signal<Record<number, string>>({});

  protected readonly entityTypes = computed<EntityType[]>(() =>
    this.privateDomains().find((domain: DomainDto) => domain.name === this.selectedDomain())?.entity_types ?? []
  );

  protected readonly questions = computed<string[]>(() => {
    const label = this.name().trim() || 'die Person';
    if (this.selectedType() === 'Pet') {
      return [
        `Wem gehört ${label}, und was für ein Tier ist es?`,
        `Was macht ${label} besonders? (Rasse, Charakter, Vorlieben)`,
        `Welche wichtigen Ereignisse verbindest du mit ${label}?`,
      ];
    }
    return [
      `In welcher Beziehung steht ${label} zu dir?`,
      `Was ist über ${label} wichtig zu wissen? (Beruf, Herkunft, Eigenheiten)`,
      `Welche wichtigen Ereignisse verbindest du mit ${label}?`,
    ];
  });

  protected readonly totalSteps = computed<number>(() => 1 + this.questions().length);
  protected readonly atIntro = computed<boolean>(() => this.stepIndex() === 0);
  protected readonly atLastQuestion = computed<boolean>(() => this.stepIndex() === this.questions().length);
  protected readonly currentQuestion = computed<string>(() => this.questions()[this.stepIndex() - 1] ?? '');
  protected readonly currentAnswer = computed<string>(() => this.answers()[this.stepIndex() - 1] ?? '');

  protected readonly nameError = computed<string | null>(() =>
    this.nameTouched() && this.name().trim().length === 0 ? 'Name darf nicht leer sein.' : null
  );

  protected readonly canAdvanceIntro = computed<boolean>(() =>
    this.name().trim().length > 0 && this.selectedType().trim().length > 0 && this.selectedDomain().trim().length > 0
  );

  constructor() {
    // Erste private Domäne + ihren ersten Typ vorbelegen, sobald die Domänen geladen sind.
    effect(() => {
      const privateDomains = this.privateDomains();
      if (privateDomains.length === 0 || this.selectedDomain() !== '') { return; }
      const first = privateDomains[0];
      if (first === undefined) { return; }
      this.selectedDomain.set(first.name);
      this.selectedType.set(first.entity_types[0]?.name ?? '');
    });

    // Sobald der Interview-Job ein Ergebnis (oder einen Fehler) liefert, aus der
    // Synthese-Warteansicht in die Zusammenfassung wechseln.
    effect(() => {
      if (this.phase() !== 'synthesizing') { return; }
      if (this.result() !== null || this.error() !== null) {
        this.phase.set('summary');
      }
    });
  }

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  protected onDomainChange(domainName: string): void {
    this.selectedDomain.set(domainName);
    this.selectedType.set(this.entityTypes()[0]?.name ?? '');
  }

  protected setCurrentAnswer(value: string): void {
    const index = this.stepIndex() - 1;
    this.answers.update((current: Record<number, string>) => ({ ...current, [index]: value }));
  }

  protected back(): void {
    if (this.stepIndex() > 0) {
      this.stepIndex.update((index: number) => index - 1);
    }
  }

  protected next(): void {
    if (this.atIntro()) {
      this.nameTouched.set(true);
      if (!this.canAdvanceIntro()) { return; }
      this.stepIndex.set(1);
      return;
    }
    if (this.atLastQuestion()) {
      this.submit();
      return;
    }
    this.stepIndex.update((index: number) => index + 1);
  }

  private submit(): void {
    const answers: InterviewAnswer[] = this.questions().map((question: string, index: number) => ({
      question,
      answer: this.answers()[index] ?? '',
    }));
    const request: InterviewSynthesizeRequest = {
      title: this.name().trim(),
      domain: this.selectedDomain(),
      type: this.selectedType(),
      answers,
    };
    this.phase.set('synthesizing');
    this.requestInterview.emit(request);
  }

  // Zurück aus der Zusammenfassung in den Fragen-Dialog (z.B. nach Validierungs-Abweisung).
  protected editAnswers(): void {
    this.phase.set('stepper');
    this.stepIndex.set(this.questions().length);
  }

  protected onConfirm(): void {
    const suggestion = this.result()?.suggestion;
    if (suggestion === null || suggestion === undefined) { return; }
    const type = this.selectedType();
    const folder = this.entityTypes().find((entityType: EntityType) => entityType.name === type)?.folder
      ?? type.toLowerCase();
    const request: CreateEntityRequest = {
      id: `${folder}/${this.slugify(this.name())}`,
      type,
      title: this.name().trim(),
      domain: this.selectedDomain(),
      // owner bleibt Default (user) im Backend — der Nutzer hat die Fakten selbst genannt.
      body: suggestion.body,
    };
    this.save.emit(request);
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('iv-scrim')) {
      this.close.emit();
    }
  }

  private slugify(value: string): string {
    return value
      .toLowerCase()
      .normalize('NFKD')
      .replace(/\p{Diacritic}/gu, '')
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }
}
