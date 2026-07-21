import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type {
  AiAutonomyMode,
  CreateEntityRequest,
  DomainDto,
  EntityDto,
  ImportSuggestionRequest,
  InterviewSynthesizeRequest,
  PersonDto,
  TaskDto,
  UpdateEntityRequest,
} from '@photofant/models';
import { PersonService } from '@photofant/services';
import { knowledgeActions, knowledgeSelectors, personsActions, personsSelectors } from '@photofant/store';
import { Icon, LinkEntityDialog } from '@photofant/ui';
import { EntityWizardDialog } from './entity-wizard-dialog/entity-wizard-dialog';
import { InterviewDialog } from './interview-dialog/interview-dialog';
import { PersonKnowledgeCard } from './person-knowledge-card/person-knowledge-card';
import { WorkQueue } from './work-queue/work-queue';

const TOAST_DURATION_MS = 2800;

@Component({
  selector: 'pf-wissen',
  imports: [Icon, EntityWizardDialog, InterviewDialog, WorkQueue, PersonKnowledgeCard, LinkEntityDialog],
  templateUrl: './wissen.html',
  styleUrl: './wissen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Wissen {
  private readonly store = inject(Store);
  private readonly personService = inject(PersonService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly domains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly domainsLoading = this.store.selectSignal(knowledgeSelectors.selectDomainsLoading);
  protected readonly isSaving = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly saveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  protected readonly lastCreatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);
  protected readonly lastUpdatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastUpdatedEntity);

  protected readonly entities = this.store.selectSignal(knowledgeSelectors.selectAllEntities);
  private readonly entitiesById = this.store.selectSignal(knowledgeSelectors.selectEntityDictionary);

  protected readonly tasks = this.store.selectSignal(knowledgeSelectors.selectAllTasks);
  protected readonly tasksLoading = this.store.selectSignal(knowledgeSelectors.selectTasksLoading);
  protected readonly tasksError = this.store.selectSignal(knowledgeSelectors.selectTasksError);

  // P38 Phase 5 — Personen-Grid der Übersicht.
  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly personsLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly knownPersons = computed((): PersonDto[] =>
    this.persons().filter((person: PersonDto) => !person.is_unknown)
  );

  // EntityRefDto (person.linked_entity) trägt keine Domäne — über die vollständige
  // Entity-Liste auflösen, die für die Übersicht ohnehin schon geladen ist.
  protected readonly entityDomainById = computed((): Record<string, string> => {
    const map: Record<string, string> = {};
    for (const entity of this.entities()) {
      map[entity.id] = entity.domain;
    }
    return map;
  });

  // P38 Phase 5 — Sektion "Nicht verknüpfte Notizen": private Entities ohne Personen-Link.
  protected readonly unlinkedEntities = computed((): EntityDto[] => {
    const privateDomainNames = new Set(
      this.domains()
        .filter((domain: DomainDto) => domain.private)
        .map((domain: DomainDto) => domain.name)
    );
    return this.entities().filter(
      (entity: EntityDto) => privateDomainNames.has(entity.domain) && entity.media_links.persons.length === 0
    );
  });

  // P27 Phase 2 — KI-Vorschlag im Wizard
  private readonly aiAutonomy = this.store.selectSignal(knowledgeSelectors.selectAiAutonomy);
  protected readonly importAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.knowledge_import ?? 'off');
  protected readonly suggestionLoading = this.store.selectSignal(knowledgeSelectors.selectSuggestionLoading);
  protected readonly suggestionResult = this.store.selectSignal(knowledgeSelectors.selectSuggestionResult);
  protected readonly suggestionError = this.store.selectSignal(knowledgeSelectors.selectSuggestionError);

  // P27 Phase 4 — Interview-Mode für private Personen. Nur angeboten, wenn die Funktion
  // nicht abgeschaltet ist UND eine private Domäne existiert (Konzept-ADR-009).
  protected readonly interviewAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.interview ?? 'off');
  protected readonly hasPrivateDomain = computed((): boolean =>
    this.domains().some((domain: DomainDto) => domain.private)
  );
  protected readonly showInterviewButton = computed((): boolean =>
    this.interviewAutonomy() !== 'off' && this.hasPrivateDomain()
  );
  protected readonly interviewLoading = this.store.selectSignal(knowledgeSelectors.selectInterviewLoading);
  protected readonly interviewResult = this.store.selectSignal(knowledgeSelectors.selectInterviewResult);
  protected readonly interviewError = this.store.selectSignal(knowledgeSelectors.selectInterviewError);
  protected readonly showInterview = signal(false);

  // P38 Phase 5 — "Web-Suche"-Knopf, gleicher Schalter wie der Backend-Guard. Der Wizard
  // selbst kommt erst in Phase 7 — das Signal wird hier bewusst schon gesetzt, aber noch
  // von keinem Dialog konsumiert (keine tote Zeile, sondern ein vorbereiteter Anschluss).
  protected readonly discoveryAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.discovery ?? 'off');
  protected readonly showWebSearchButton = computed((): boolean => this.discoveryAutonomy() === 'auto');
  protected readonly showWebSearchWizard = signal(false);

  protected readonly showWizard = signal(false);
  // Gesetzt, wenn der Wizard eine bestehende Entity bearbeitet (z.B. aus der Aufgabe
  // "Entity noch ohne Inhalt") statt eine neue anzulegen.
  protected readonly editingEntity = signal<EntityDto | null>(null);
  // Wizard aus einer Aufgabe geöffnet? -> nach Erfolg diese Aufgabe auflösen statt nur zu schließen.
  private readonly activeTask = signal<TaskDto | null>(null);

  // P38 Phase 5 — Personen-Detail (Modal kommt erst in Phase 6, Signal ist der Anschluss
  // dafür; die Karte im Grid schreibt bereits heute hinein).
  protected readonly detailPersonId = signal<number | null>(null);

  // P38 Phase 5 — "Verknüpfen" auf einer unverknüpften Notiz: Personen-Suche öffnen.
  protected readonly linkingEntity = signal<EntityDto | null>(null);

  // P38 Phase 5 — Toast statt der beiden statischen Bestätigungs-Blöcke.
  protected readonly toastMessage = signal<string | null>(null);
  private toastTimeoutId: ReturnType<typeof setTimeout> | null = null;

  protected readonly wizardPrefill = computed((): Partial<CreateEntityRequest> => {
    const task = this.activeTask();
    if (task === null) { return {}; }
    const title = task.context['title'];
    if (typeof title === 'string' && title.length > 0) {
      return { title };
    }
    const ref = task.context['ref'];
    if (typeof ref === 'string' && ref.length > 0) {
      return { title: ref };
    }
    return {};
  });

  constructor() {
    this.store.dispatch(knowledgeActions.loadDomains());
    this.store.dispatch(knowledgeActions.loadTasks());
    this.store.dispatch(knowledgeActions.loadEntities());
    this.store.dispatch(knowledgeActions.loadAiAutonomy());
    this.store.dispatch(personsActions.loadPersons());

    // Wizard schließt sich selbst, sobald Anlegen ODER Bearbeiten erfolgreich war; kam
    // er aus einer Aufgabe, wird die Aufgabe im selben Zug aufgelöst.
    effect(() => {
      const created = this.lastCreatedEntity();
      const updated = this.lastUpdatedEntity();
      if (created === null && updated === null) { return; }
      this.showWizard.set(false);
      this.showInterview.set(false);
      this.editingEntity.set(null);
      const task = this.activeTask();
      if (task !== null) {
        this.store.dispatch(knowledgeActions.resolveTask({ taskId: task.id }));
        this.activeTask.set(null);
      }
      if (created !== null) {
        this.showToast(`„${created.title}" (${created.type}) angelegt.`);
      } else if (updated !== null) {
        this.showToast(`„${updated.title}" aktualisiert.`);
      }
    });

    this.destroyRef.onDestroy(() => {
      if (this.toastTimeoutId !== null) {
        clearTimeout(this.toastTimeoutId);
      }
    });
  }

  private showToast(message: string): void {
    this.toastMessage.set(message);
    if (this.toastTimeoutId !== null) {
      clearTimeout(this.toastTimeoutId);
    }
    this.toastTimeoutId = setTimeout(() => this.toastMessage.set(null), TOAST_DURATION_MS);
  }

  protected openInterview(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetInterview());
    this.showInterview.set(true);
  }

  protected closeInterview(): void {
    this.store.dispatch(knowledgeActions.resetInterview());
    this.showInterview.set(false);
  }

  protected onRequestInterview(request: InterviewSynthesizeRequest): void {
    this.store.dispatch(knowledgeActions.requestInterview({ request }));
  }

  // P38 Phase 5 — Platzhalter bis Phase 7 den echten Wizard liefert.
  protected openWebSearchWizard(): void {
    this.showWebSearchWizard.set(true);
  }

  protected openWizard(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(null);
    this.editingEntity.set(null);
    this.showWizard.set(true);
  }

  protected closeWizard(): void {
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.showWizard.set(false);
    this.activeTask.set(null);
    this.editingEntity.set(null);
  }

  protected onRequestSuggestion(request: ImportSuggestionRequest): void {
    this.store.dispatch(knowledgeActions.requestImportSuggestion({ request }));
  }

  protected onSave(request: CreateEntityRequest): void {
    this.store.dispatch(knowledgeActions.createEntity({ request }));
  }

  protected onUpdate(event: { entityId: string; patch: UpdateEntityRequest }): void {
    this.store.dispatch(knowledgeActions.updateEntity(event));
  }

  // Klick auf eine Personen-Karte -> Detail öffnen (Modal folgt in Phase 6).
  protected openPersonDetail(personId: number): void {
    this.detailPersonId.set(personId);
  }

  protected openLinkPicker(entity: EntityDto): void {
    this.linkingEntity.set(entity);
  }

  protected closeLinkPicker(): void {
    this.linkingEntity.set(null);
  }

  protected onLinkNoteToPerson(person: PersonDto): void {
    const entity = this.linkingEntity();
    if (entity === null) { return; }
    this.personService.linkEntity(person.id, entity.id).subscribe(() => {
      this.linkingEntity.set(null);
      this.store.dispatch(knowledgeActions.loadEntities());
      this.store.dispatch(personsActions.loadPersons());
      this.store.dispatch(knowledgeActions.loadTasks());
      this.showToast(`„${entity.title}" mit ${person.name ?? 'Unbenannt'} verknüpft.`);
    });
  }

  // Kein `updated_at` im EntityDto-Kontrakt (P38 Phase 2/3 fixiert) — die Meta-Zeile zeigt
  // deshalb nur den Prozentwert, kein "geändert am {Datum}" wie im Design-Mock (dort mit
  // erfundenen Mock-Daten belegt). Siehe Report-Back.
  protected unlinkedPercent(entity: EntityDto): number {
    return Math.round(entity.completeness * 100);
  }

  protected resolveTaskViaWizard(task: TaskDto): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(task);
    // "Entity noch ohne Inhalt" verweist auf eine bestehende Entity (`entity_id` im
    // Task-Kontext) -> Wizard im Edit-Modus öffnen statt eine neue anzulegen.
    if (task.kind === 'incomplete_entity') {
      const entityId = task.context['entity_id'];
      this.editingEntity.set(typeof entityId === 'string' ? this.entitiesById()[entityId] ?? null : null);
    } else {
      this.editingEntity.set(null);
    }
    this.showWizard.set(true);
  }

  protected dismissTask(taskId: number): void {
    this.store.dispatch(knowledgeActions.dismissTask({ taskId }));
  }
}
