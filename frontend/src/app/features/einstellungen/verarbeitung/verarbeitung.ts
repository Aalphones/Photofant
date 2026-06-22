import { ChangeDetectionStrategy, Component, computed, effect, inject, linkedSignal } from '@angular/core';
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

  // linkedSignals: zeigen Store-Werte an, akzeptieren temporäre Eingaben während des Ziehens
  protected readonly dupeThresholdDisplay       = linkedSignal(() => this.processingConfig().dupeThreshold);
  protected readonly faceAutoThresholdDisplay   = linkedSignal(() => this.processingConfig().faceAutoThreshold);
  protected readonly faceReviewThresholdDisplay = linkedSignal(() => this.processingConfig().faceReviewThreshold);
  protected readonly faceMinClusterSizeDisplay  = linkedSignal(() => this.processingConfig().faceMinClusterSize);

  protected readonly dupeThresholdLabel = computed((): string => {
    const value = this.dupeThresholdDisplay();
    if (value <= 4) { return `${value} — nur fast identische Bilder`; }
    if (value <= 9) { return `${value} — geringe Toleranz`; }
    if (value <= 14) { return `${value} — mittlere Empfindlichkeit`; }
    if (value <= 20) { return `${value} — hohe Toleranz`; }
    return `${value} — sehr hohe Toleranz (mehr Fehlalarme möglich)`;
  });

  protected readonly faceAutoThresholdLabel = computed((): string => {
    const pct = Math.round(this.faceAutoThresholdDisplay() * 100);
    return `${pct} % — darüber: automatische Zuordnung`;
  });

  protected readonly faceReviewThresholdLabel = computed((): string => {
    const pct = Math.round(this.faceReviewThresholdDisplay() * 100);
    const autoPct = Math.round(this.faceAutoThresholdDisplay() * 100);
    return `${pct} % — zwischen ${pct} % und ${autoPct} %: Review-Queue`;
  });

  protected readonly faceMinClusterSizeLabel = computed((): string => {
    const value = this.faceMinClusterSizeDisplay();
    return value === 1 ? '1 Gesicht min. (kein Cluster-Filter)' : `${value} Gesichter min. pro Cluster`;
  });

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

  onDupeThresholdInput(target: HTMLInputElement): void {
    this.dupeThresholdDisplay.set(parseInt(target.value, 10));
  }

  onDupeThresholdChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(32, Math.max(0, isNaN(raw) ? 10 : raw));
    this.patchProcessingConfig({ dupeThreshold: clamped });
  }

  onFaceAutoThresholdInput(target: HTMLInputElement): void {
    this.faceAutoThresholdDisplay.set(parseFloat(target.value));
  }

  onFaceAutoThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1, Math.max(0, isNaN(raw) ? 0.6 : raw));
    this.patchProcessingConfig({ faceAutoThreshold: clamped });
  }

  onFaceReviewThresholdInput(target: HTMLInputElement): void {
    this.faceReviewThresholdDisplay.set(parseFloat(target.value));
  }

  onFaceReviewThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1, Math.max(0, isNaN(raw) ? 0.45 : raw));
    this.patchProcessingConfig({ faceReviewThreshold: clamped });
  }

  onFaceMinClusterSizeInput(target: HTMLInputElement): void {
    this.faceMinClusterSizeDisplay.set(parseInt(target.value, 10));
  }

  onFaceMinClusterSizeChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(20, Math.max(1, isNaN(raw) ? 2 : raw));
    this.patchProcessingConfig({ faceMinClusterSize: clamped });
  }
}
