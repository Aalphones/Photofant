import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import type { ProcessingConfig } from '@photofant/models';
import { modelsActions, modelsSelectors } from '@photofant/store';

@Component({
  selector: 'pf-einstellungen-verarbeitung',
  imports: [],
  templateUrl: './verarbeitung.html',
  styleUrl: './verarbeitung.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Verarbeitung {
  private readonly store = inject(Store);

  readonly processingConfig = this.store.selectSignal(modelsSelectors.selectProcessingConfig);

  constructor() {
    effect(() => {
      this.store.dispatch(modelsActions.loadConfig());
    });
  }

  patchProcessingConfig(patch: Partial<ProcessingConfig>): void {
    this.store.dispatch(modelsActions.updateProcessingConfig({ patch }));
  }

  onMinProbabilityChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1, Math.max(0, isNaN(raw) ? 0.5 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ minProbability: clamped });
  }

  onMaxTagsChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(200, Math.max(1, isNaN(raw) ? 30 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ maxTags: clamped });
  }

  onBlurThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1000, Math.max(0, isNaN(raw) ? 200 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ blurThreshold: clamped });
  }
}
