import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { comfyuiActions, comfyuiSelectors } from '@photofant/store';
import type { ComfyUIConfig, ComfyUIWorkflow, WorkflowInput } from '@photofant/models';
import { WORKFLOW_CATEGORIES } from '@photofant/models';

@Component({
  selector: 'pf-einstellungen-comfyui',
  imports: [Icon],
  templateUrl: './comfyui.html',
  styleUrl: './comfyui.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ComfyUISection {
  private readonly store = inject(Store);

  readonly config = this.store.selectSignal(comfyuiSelectors.selectConfig);
  readonly isSaving = this.store.selectSignal(comfyuiSelectors.selectIsSaving);
  readonly isTesting = this.store.selectSignal(comfyuiSelectors.selectIsTesting);
  readonly testResult = this.store.selectSignal(comfyuiSelectors.selectTestResult);
  readonly error = this.store.selectSignal(comfyuiSelectors.selectError);

  readonly workflows = this.store.selectSignal(comfyuiSelectors.selectWorkflows);
  readonly isLoadingWorkflows = this.store.selectSignal(comfyuiSelectors.selectIsLoadingWorkflows);
  readonly isCreatingWorkflow = this.store.selectSignal(comfyuiSelectors.selectIsCreatingWorkflow);
  readonly selectedWorkflowId = this.store.selectSignal(comfyuiSelectors.selectSelectedWorkflowId);
  readonly selectedWorkflow = this.store.selectSignal(comfyuiSelectors.selectSelectedWorkflow);
  readonly workflowError = this.store.selectSignal(comfyuiSelectors.selectWorkflowError);

  readonly categories = WORKFLOW_CATEGORIES;

  readonly draftEnabled = signal<boolean>(false);
  readonly draftBaseUrl = signal<string>('');
  readonly draftClientId = signal<string>('');
  readonly draftOutputDir = signal<string>('');
  readonly draftTimeout = signal<number>(10);

  readonly isDirty = computed((): boolean => {
    const cfg = this.config();
    return (
      this.draftEnabled() !== cfg.enabled ||
      this.draftBaseUrl() !== cfg.baseUrl ||
      this.draftClientId() !== cfg.clientId ||
      this.draftOutputDir() !== cfg.outputDir ||
      this.draftTimeout() !== cfg.timeout
    );
  });

  readonly editingWorkflow = signal<ComfyUIWorkflow | null>(null);
  readonly editName = signal<string>('');
  readonly editCategory = signal<string>('generic');

  constructor() {
    effect(() => {
      this.store.dispatch(comfyuiActions.loadConfig());
    });
    effect(() => {
      const cfg = this.config();
      this.draftEnabled.set(cfg.enabled);
      this.draftBaseUrl.set(cfg.baseUrl);
      this.draftClientId.set(cfg.clientId);
      this.draftOutputDir.set(cfg.outputDir);
      this.draftTimeout.set(cfg.timeout);
    });
    effect(() => {
      this.store.dispatch(comfyuiActions.loadWorkflows());
    });
  }

  toggleEnabled(): void {
    this.draftEnabled.update((value: boolean) => !value);
    this.store.dispatch(comfyuiActions.clearTestResult());
  }

  onBaseUrlChange(target: HTMLInputElement): void {
    this.draftBaseUrl.set(target.value);
    this.store.dispatch(comfyuiActions.clearTestResult());
  }

  onClientIdChange(target: HTMLInputElement): void {
    this.draftClientId.set(target.value);
  }

  onOutputDirChange(target: HTMLInputElement): void {
    this.draftOutputDir.set(target.value);
  }

  onTimeoutChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(300, Math.max(1, isNaN(raw) ? 10 : raw));
    target.value = String(clamped);
    this.draftTimeout.set(clamped);
    this.store.dispatch(comfyuiActions.clearTestResult());
  }

  save(): void {
    const config: ComfyUIConfig = {
      enabled: this.draftEnabled(),
      baseUrl: this.draftBaseUrl().trim(),
      clientId: this.draftClientId().trim() || 'photofant',
      outputDir: this.draftOutputDir().trim(),
      timeout: this.draftTimeout(),
    };
    this.store.dispatch(comfyuiActions.saveConfig({ config }));
  }

  testConnection(): void {
    this.store.dispatch(comfyuiActions.testConnection());
  }

  onTemplateUpload(input: HTMLInputElement): void {
    const file = input.files?.[0];
    if (!file) return;
    const name = file.name.replace(/\.api\.json$|\.json$/, '').replace(/[_-]/g, ' ');
    this.store.dispatch(comfyuiActions.createWorkflow({ file, name, category: 'generic' }));
    input.value = '';
  }

  selectWorkflow(workflowId: number): void {
    const current = this.selectedWorkflowId();
    if (current === workflowId) {
      this.store.dispatch(comfyuiActions.selectWorkflow({ workflowId: null }));
      this.editingWorkflow.set(null);
    } else {
      this.store.dispatch(comfyuiActions.selectWorkflow({ workflowId }));
      this.editingWorkflow.set(null);
    }
  }

  startEditWorkflow(workflow: ComfyUIWorkflow): void {
    this.editingWorkflow.set(workflow);
    this.editName.set(workflow.name);
    this.editCategory.set(workflow.category);
  }

  cancelEditWorkflow(): void {
    this.editingWorkflow.set(null);
  }

  saveEditWorkflow(): void {
    const editing = this.editingWorkflow();
    if (!editing) return;

    const patch: { name?: string; category?: string } = {};
    if (this.editName() !== editing.name) {
      patch.name = this.editName();
    }
    if (this.editCategory() !== editing.category) {
      patch.category = this.editCategory();
    }
    if (Object.keys(patch).length > 0) {
      this.store.dispatch(comfyuiActions.updateWorkflow({ workflowId: editing.id, patch }));
    }
    this.editingWorkflow.set(null);
  }

  onEditNameChange(target: HTMLInputElement): void {
    this.editName.set(target.value);
  }

  onEditCategoryChange(target: HTMLSelectElement): void {
    this.editCategory.set(target.value);
  }

  deleteWorkflow(workflowId: number): void {
    this.store.dispatch(comfyuiActions.deleteWorkflow({ workflowId }));
  }

  activateWorkflow(workflowId: number): void {
    this.store.dispatch(comfyuiActions.activateWorkflow({ workflowId }));
  }

  deactivateWorkflow(workflowId: number): void {
    this.store.dispatch(comfyuiActions.deactivateWorkflow({ workflowId }));
  }

  duplicateWorkflow(workflowId: number): void {
    this.store.dispatch(comfyuiActions.duplicateWorkflow({ workflowId }));
  }

  redetectInputs(workflowId: number): void {
    this.store.dispatch(comfyuiActions.redetectInputs({ workflowId }));
  }

  statusLabel(workflow: ComfyUIWorkflow): string {
    if (!workflow.isValid) return 'invalide';
    if (workflow.isActive) return 'aktiv';
    return 'inaktiv';
  }

  statusClass(workflow: ComfyUIWorkflow): string {
    if (!workflow.isValid) return 'comfyui__status--fehler';
    if (workflow.isActive) return 'comfyui__status--ok';
    return 'comfyui__status--inaktiv';
  }

  removeInput(workflow: ComfyUIWorkflow, index: number): void {
    const inputs = [...workflow.inputs];
    inputs.splice(index, 1);
    this.store.dispatch(comfyuiActions.updateWorkflow({
      workflowId: workflow.id,
      patch: { inputs },
    }));
  }

  removeParam(workflow: ComfyUIWorkflow, index: number): void {
    const params = [...workflow.params];
    params.splice(index, 1);
    this.store.dispatch(comfyuiActions.updateWorkflow({
      workflowId: workflow.id,
      patch: { params },
    }));
  }

  toggleInputRequired(workflow: ComfyUIWorkflow, index: number): void {
    const inputs = workflow.inputs.map((input: WorkflowInput, idx: number) =>
      idx === index ? { ...input, required: !input.required } : input
    );
    this.store.dispatch(comfyuiActions.updateWorkflow({
      workflowId: workflow.id,
      patch: { inputs },
    }));
  }

  toggleInputLockable(workflow: ComfyUIWorkflow, index: number): void {
    const inputs = workflow.inputs.map((input: WorkflowInput, idx: number) =>
      idx === index ? { ...input, lockable: !input.lockable } : input
    );
    this.store.dispatch(comfyuiActions.updateWorkflow({
      workflowId: workflow.id,
      patch: { inputs },
    }));
  }
}
