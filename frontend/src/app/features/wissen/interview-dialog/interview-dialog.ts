import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
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
  PersonDto,
  UpdateEntityRequest,
} from '@photofant/models';
import { PersonService } from '@photofant/services';
import { Icon } from '../../../ui/icon/icon';
import { WizardShell } from '../wizard-shell/wizard-shell';

// P38 Phase 7 — die fünf Fragen wörtlich aus `design/js/data.js` Zeile 455-461 (reine
// Oberfläche, kein Backend-Konzept mehr wie die alte Person/Pet-Unterscheidung).
const INTERVIEW_QUESTIONS: readonly string[] = [
  'Was schätzt du an dieser Person am meisten?',
  'Gibt es eine Geschichte oder ein Erlebnis, das sie/ihn gut beschreibt?',
  'Welche Vorlieben, Hobbys oder Eigenheiten fallen dir ein?',
  'Wie würdest du eure Beziehung zueinander beschreiben?',
  'Sonst noch etwas Wichtiges, das man wissen sollte?',
];

type DialogPhase = 'stepper' | 'synthesizing' | 'summary';

// Preset, mit dem der Wizard aus einem Personen-Kontext (Karte, Detail, Aufgabe) geöffnet
// wird — trägt nur, was zur Anzeige/Verknüpfung nötig ist (Aufgabe 4, gemeinsames Signal).
export interface WizardTarget {
  personId: number | null;
  entityId: string | null;
  name: string | null;
}

@Component({
  selector: 'pf-interview-dialog',
  imports: [Icon, WizardShell],
  templateUrl: './interview-dialog.html',
  styleUrl: './interview-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterviewDialog {
  private readonly personService = inject(PersonService);

  // Nur private Domänen kommen für das Interview infrage (Konzept-ADR-009) — automatisch
  // aufgelöst (erste private Domäne + ihr erster Typ), keine eigene Auswahl mehr im Design.
  readonly domains = input.required<DomainDto[]>();
  readonly persons = input<PersonDto[]>([]);
  readonly target = input<WizardTarget | null>(null);
  readonly isSaving = input<boolean>(false);
  readonly saveError = input<string | null>(null);
  readonly loading = input<boolean>(false);
  readonly result = input<KnowledgeInterviewResult | null>(null);
  readonly error = input<string | null>(null);

  readonly close = output<void>();
  readonly requestInterview = output<InterviewSynthesizeRequest>();
  readonly save = output<CreateEntityRequest>();
  // Zielt das Interview auf eine Person mit bereits bestehender Notiz (`target.entityId`),
  // muss die Zusammenfassung dorthin gepatcht werden statt eine zweite Notiz mit derselben
  // ID anzulegen — das Backend lehnt den doppelten Slug sonst mit 409 ab.
  readonly update = output<{ entityId: string; patch: UpdateEntityRequest }>();

  protected readonly questions = INTERVIEW_QUESTIONS;

  protected readonly privateDomains = computed<DomainDto[]>(() =>
    this.domains().filter((domain: DomainDto) => domain.private)
  );

  private readonly resolvedDomain = computed<DomainDto | null>(() => this.privateDomains()[0] ?? null);

  private readonly resolvedType = computed<EntityType | null>(() => {
    const domain = this.resolvedDomain();
    if (domain === null) { return null; }
    return domain.entity_types.find((entityType: EntityType) => entityType.name === 'Person')
      ?? domain.entity_types[0] ?? null;
  });

  // Schritt 0: entfällt, wenn ein Preset mitkommt (Bestätigungszeile statt Auswahl).
  protected readonly hasTarget = computed<boolean>(() => this.target() !== null);

  protected readonly pickedPersonId = signal<number | null>(null);
  protected readonly freetextName = signal('');

  protected readonly phase = signal<DialogPhase>('stepper');
  // 0 = Intro (Personen-Wahl oder Bestätigungszeile), 1..N = je eine Frage.
  protected readonly stepIndex = signal(0);
  protected readonly answers = signal<Record<number, string>>({});

  protected readonly name = computed<string>(() => {
    const target = this.target();
    if (target !== null) { return target.name ?? ''; }
    const picked = this.pickedPersonId();
    if (picked !== null) {
      return this.persons().find((person: PersonDto) => person.id === picked)?.name ?? '';
    }
    return this.freetextName().trim();
  });

  protected readonly linkedPersonId = computed<number | null>(() => {
    const target = this.target();
    if (target !== null) { return target.personId; }
    return this.pickedPersonId();
  });

  protected readonly atIntro = computed<boolean>(() => this.stepIndex() === 0);
  protected readonly atLastQuestion = computed<boolean>(() => this.stepIndex() === this.questions.length);
  protected readonly currentQuestion = computed<string>(() => this.questions[this.stepIndex() - 1] ?? '');
  protected readonly currentAnswer = computed<string>(() => this.answers()[this.stepIndex() - 1] ?? '');

  protected readonly canAdvanceIntro = computed<boolean>(() =>
    this.hasTarget() || this.pickedPersonId() !== null || this.freetextName().trim().length > 0
  );

  protected readonly canGoBack = computed<boolean>(() => this.phase() === 'stepper' && this.stepIndex() > 0);

  protected readonly backLabel = computed<string>(() =>
    this.phase() === 'summary' ? 'Antworten anpassen' : 'Zurück'
  );

  protected readonly primaryLabel = computed<string | null>(() => {
    if (this.phase() === 'synthesizing') { return null; }
    if (this.phase() === 'summary') { return this.result()?.suggestion ? 'Übernehmen' : null; }
    if (this.atIntro()) { return 'Weiter'; }
    if (this.atLastQuestion()) { return 'Zusammenfassen'; }
    return this.currentAnswer().trim().length === 0 ? 'Überspringen' : 'Weiter';
  });

  protected readonly primaryDisabled = computed<boolean>(() => {
    if (this.phase() === 'summary') { return this.isSaving(); }
    if (this.atIntro()) { return !this.canAdvanceIntro(); }
    return false;
  });

  protected avatarUrl(person: PersonDto): string | null {
    return person.portrait_face_id !== null ? this.personService.portraitUrl(person.portrait_face_id) : null;
  }

  constructor() {
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

  protected answeredCount(): number {
    return Object.values(this.answers()).filter((answer: string) => answer.trim().length > 0).length;
  }

  protected pickPerson(personId: number): void {
    this.pickedPersonId.set(personId);
    this.freetextName.set('');
  }

  protected setFreetextName(value: string): void {
    this.freetextName.set(value);
    this.pickedPersonId.set(null);
  }

  protected setCurrentAnswer(value: string): void {
    const index = this.stepIndex() - 1;
    this.answers.update((current: Record<number, string>) => ({ ...current, [index]: value }));
  }

  protected onShellBack(): void {
    if (this.phase() === 'summary') {
      this.editAnswers();
      return;
    }
    if (this.stepIndex() > 0) {
      this.stepIndex.update((index: number) => index - 1);
    }
  }

  protected onShellPrimary(): void {
    if (this.phase() === 'summary') {
      this.onConfirm();
      return;
    }
    this.next();
  }

  private next(): void {
    if (this.atIntro()) {
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
    const domain = this.resolvedDomain();
    const type = this.resolvedType();
    if (domain === null || type === null) { return; }
    const answers: InterviewAnswer[] = this.questions.map((question: string, index: number) => ({
      question,
      answer: this.answers()[index] ?? '',
    }));
    const personId = this.linkedPersonId();
    const request: InterviewSynthesizeRequest = {
      title: this.name().trim(),
      domain: domain.name,
      type: type.name,
      answers,
      person_ids: personId !== null ? [personId] : [],
    };
    this.phase.set('synthesizing');
    this.requestInterview.emit(request);
  }

  // Zurück aus der Zusammenfassung in den Fragen-Dialog (z.B. nach Validierungs-Abweisung).
  private editAnswers(): void {
    this.phase.set('stepper');
    this.stepIndex.set(this.questions.length);
  }

  protected onConfirm(): void {
    const suggestion = this.result()?.suggestion;
    const domain = this.resolvedDomain();
    const type = this.resolvedType();
    if (suggestion === null || suggestion === undefined || domain === null || type === null) { return; }

    // Läuft das Interview über eine Person, die schon eine Notiz hat, ist das hier ein
    // Update der bestehenden Notiz — nicht das Anlegen einer zweiten mit derselben ID.
    const existingEntityId = this.target()?.entityId ?? null;
    if (existingEntityId !== null) {
      const patch: UpdateEntityRequest = {
        title: this.name().trim(),
        body: suggestion.body,
      };
      this.update.emit({ entityId: existingEntityId, patch });
      return;
    }

    const personId = this.linkedPersonId();
    const request: CreateEntityRequest = {
      id: `${type.folder}/${this.slugify(this.name())}`,
      type: type.name,
      title: this.name().trim(),
      domain: domain.name,
      body: suggestion.body,
      // Vorbelegte oder per Chip gewählte Person verknüpft die entstehende Notiz sofort
      // (Design-Vorgabe „automatische Verknüpfung") — ohne Person bleibt sie eigenständig.
      media_links: { persons: personId !== null ? [personId] : [], assets: [] },
    };
    this.save.emit(request);
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
