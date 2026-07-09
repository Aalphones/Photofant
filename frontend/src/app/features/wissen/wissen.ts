import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { CreateEntityRequest, TaskDto } from '@photofant/models';
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

  protected readonly tasks = this.store.selectSignal(knowledgeSelectors.selectAllTasks);
  protected readonly tasksLoading = this.store.selectSignal(knowledgeSelectors.selectTasksLoading);
  protected readonly tasksError = this.store.selectSignal(knowledgeSelectors.selectTasksError);

  protected readonly showWizard = signal(false);
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

    // Wizard schließt sich selbst, sobald das Anlegen erfolgreich war; kam er aus
    // einer Aufgabe, wird die Aufgabe im selben Zug aufgelöst.
    effect(() => {
      if (this.lastCreatedEntity() === null) { return; }
      this.showWizard.set(false);
      const task = this.activeTask();
      if (task !== null) {
        this.store.dispatch(knowledgeActions.resolveTask({ taskId: task.id }));
        this.activeTask.set(null);
      }
    });
  }

  protected openWizard(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.activeTask.set(null);
    this.showWizard.set(true);
  }

  protected closeWizard(): void {
    this.showWizard.set(false);
    this.activeTask.set(null);
  }

  protected onSave(request: CreateEntityRequest): void {
    this.store.dispatch(knowledgeActions.createEntity({ request }));
  }

  protected resolveTaskViaWizard(task: TaskDto): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.activeTask.set(task);
    this.showWizard.set(true);
  }

  protected dismissTask(taskId: number): void {
    this.store.dispatch(knowledgeActions.dismissTask({ taskId }));
  }
}
