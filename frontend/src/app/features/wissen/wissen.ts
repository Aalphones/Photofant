import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { AiAutonomyMode, CreateEntityRequest, EntityDto, ImportSuggestionRequest, TaskDto, UpdateEntityRequest } from '@photofant/models';
import { knowledgeActions, knowledgeSelectors } from '@photofant/store';
import { Icon } from '../../ui/icon/icon';
import { EntityWizardDialog } from './entity-wizard-dialog/entity-wizard-dialog';
import { WorkQueue } from './work-queue/work-queue';

@Component({
  selector: 'pf-wissen',
  imports: [Icon, EntityWizardDialog, WorkQueue],
  templateUrl: './wissen.html',
  styleUrl: './wissen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Wissen {
  private readonly store = inject(Store);

  protected readonly domains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly domainsLoading = this.store.selectSignal(knowledgeSelectors.selectDomainsLoading);
  protected readonly isSaving = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly saveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  protected readonly lastCreatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);
  protected readonly lastUpdatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastUpdatedEntity);

  protected readonly entities = this.store.selectSignal(knowledgeSelectors.selectAllEntities);
  protected readonly entitiesLoading = this.store.selectSignal(knowledgeSelectors.selectEntitiesLoading);
  private readonly entitiesById = this.store.selectSignal(knowledgeSelectors.selectEntityDictionary);

  protected readonly tasks = this.store.selectSignal(knowledgeSelectors.selectAllTasks);
  protected readonly tasksLoading = this.store.selectSignal(knowledgeSelectors.selectTasksLoading);
  protected readonly tasksError = this.store.selectSignal(knowledgeSelectors.selectTasksError);

  // P27 Phase 2 — KI-Vorschlag im Wizard
  private readonly aiAutonomy = this.store.selectSignal(knowledgeSelectors.selectAiAutonomy);
  protected readonly importAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.knowledge_import ?? 'off');
  protected readonly suggestionLoading = this.store.selectSignal(knowledgeSelectors.selectSuggestionLoading);
  protected readonly suggestionResult = this.store.selectSignal(knowledgeSelectors.selectSuggestionResult);
  protected readonly suggestionError = this.store.selectSignal(knowledgeSelectors.selectSuggestionError);

  protected readonly showWizard = signal(false);
  // Gesetzt, wenn der Wizard eine bestehende Entity bearbeitet (z.B. aus der Aufgabe
  // "Entity noch ohne Inhalt") statt eine neue anzulegen.
  protected readonly editingEntity = signal<EntityDto | null>(null);
  // Wizard aus einer Aufgabe geöffnet? -> nach Erfolg diese Aufgabe auflösen statt nur zu schließen.
  private readonly activeTask = signal<TaskDto | null>(null);

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

    // Wizard schließt sich selbst, sobald Anlegen ODER Bearbeiten erfolgreich war; kam
    // er aus einer Aufgabe, wird die Aufgabe im selben Zug aufgelöst.
    effect(() => {
      if (this.lastCreatedEntity() === null && this.lastUpdatedEntity() === null) { return; }
      this.showWizard.set(false);
      this.editingEntity.set(null);
      const task = this.activeTask();
      if (task !== null) {
        this.store.dispatch(knowledgeActions.resolveTask({ taskId: task.id }));
        this.activeTask.set(null);
      }
    });
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

  // Klick auf eine Zeile in der Übersichtsliste -> direkt bearbeiten, unabhängig von
  // der Work-Queue.
  protected openEntityForEdit(entity: EntityDto): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(null);
    this.editingEntity.set(entity);
    this.showWizard.set(true);
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
