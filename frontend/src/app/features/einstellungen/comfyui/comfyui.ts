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
import type { ComfyUIConfig, ComfyUIWorkflow } from '@photofant/models';

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
  readonly selectedWorkflowId = this.store.selectSignal(comfyuiSelectors.selectSelectedWorkflowId);
  readonly workflowError = this.store.selectSignal(comfyuiSelectors.selectWorkflowError);

  readonly draftEnabled = signal<boolean>(false);
  readonly draftBaseUrl = signal<string>('');
  readonly draftClientId = signal<string>('');
  readonly draftOutputDir = signal<string>('');
  readonly draftTimeout = signal<number>(10);
  readonly draftDefaultUpscale = signal<string>('');
  readonly draftDefaultEdit = signal<string>('');
  readonly draftDefaultInpaint = signal<string>('');

  readonly isDirty = computed((): boolean => {
    const cfg = this.config();
    return (
      this.draftEnabled() !== cfg.enabled ||
      this.draftBaseUrl() !== cfg.baseUrl ||
      this.draftClientId() !== cfg.clientId ||
      this.draftOutputDir() !== cfg.outputDir ||
      this.draftTimeout() !== cfg.timeout ||
      this.draftDefaultUpscale() !== cfg.defaultUpscale ||
      this.draftDefaultEdit() !== cfg.defaultEdit ||
      this.draftDefaultInpaint() !== cfg.defaultInpaint
    );
  });

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
      this.draftDefaultUpscale.set(cfg.defaultUpscale);
      this.draftDefaultEdit.set(cfg.defaultEdit);
      this.draftDefaultInpaint.set(cfg.defaultInpaint);
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

  onDefaultUpscaleChange(target: HTMLSelectElement): void {
    this.draftDefaultUpscale.set(target.value);
  }

  onDefaultEditChange(target: HTMLSelectElement): void {
    this.draftDefaultEdit.set(target.value);
  }

  onDefaultInpaintChange(target: HTMLSelectElement): void {
    this.draftDefaultInpaint.set(target.value);
  }

  save(): void {
    const config: ComfyUIConfig = {
      enabled: this.draftEnabled(),
      baseUrl: this.draftBaseUrl().trim(),
      clientId: this.draftClientId().trim() || 'photofant',
      outputDir: this.draftOutputDir().trim(),
      timeout: this.draftTimeout(),
      defaultUpscale: this.draftDefaultUpscale(),
      defaultEdit: this.draftDefaultEdit(),
      defaultInpaint: this.draftDefaultInpaint(),
    };
    this.store.dispatch(comfyuiActions.saveConfig({ config }));
  }

  testConnection(): void {
    this.store.dispatch(comfyuiActions.testConnection());
  }

  selectWorkflow(workflowKey: string): void {
    const current = this.selectedWorkflowId();
    this.store.dispatch(comfyuiActions.selectWorkflow({
      workflowId: current === workflowKey ? null : workflowKey,
    }));
  }

  statusLabel(workflow: ComfyUIWorkflow): string {
    return workflow.isValid ? 'verfügbar' : 'invalide';
  }

  statusClass(workflow: ComfyUIWorkflow): string {
    return workflow.isValid ? 'comfyui__status--ok' : 'comfyui__status--fehler';
  }
}
