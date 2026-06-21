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
import type { ComfyUIConfig } from '@photofant/models';

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

  // Local draft — user edits fields, clicks Speichern
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

  constructor() {
    effect(() => {
      this.store.dispatch(comfyuiActions.loadConfig());
    });
    // Sync draft when config loads
    effect(() => {
      const cfg = this.config();
      this.draftEnabled.set(cfg.enabled);
      this.draftBaseUrl.set(cfg.baseUrl);
      this.draftClientId.set(cfg.clientId);
      this.draftOutputDir.set(cfg.outputDir);
      this.draftTimeout.set(cfg.timeout);
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
}
