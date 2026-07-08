import { ChangeDetectionStrategy, Component, computed, effect, inject, linkedSignal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { ModelDto, ProcessingConfig } from '@photofant/models';
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
  private readonly allModels = this.store.selectSignal(modelsSelectors.selectModels);
  private readonly vram = this.store.selectSignal(modelsSelectors.selectVram);

  readonly captionerOptions = computed((): ModelDto[] =>
    this.allModels().filter((model: ModelDto) => model.caption_mode != null)
  );

  // linkedSignals: zeigen Store-Werte an, akzeptieren temporäre Eingaben während des Ziehens
  // P37 Phase 4: Duplikaterkennung läuft auf DINOv2 — der Slider bindet an dupeDinoThreshold,
  // dupeClipEnabled bleibt der generische An/Aus-Schalter (Key-Name unverändert, kein Feature-Bezug mehr).
  protected readonly dupeDinoThresholdDisplay   = linkedSignal(() => this.processingConfig().dupeDinoThreshold);
  protected readonly trainingNearDupeThresholdDisplay = linkedSignal(() => this.processingConfig().trainingNearDupeDinoThreshold);
  protected readonly faceDetConfDisplay         = linkedSignal(() => this.processingConfig().faceDetConfThreshold);
  protected readonly faceDetIouDisplay          = linkedSignal(() => this.processingConfig().faceDetIouThreshold);
  protected readonly faceAutoThresholdDisplay   = linkedSignal(() => this.processingConfig().faceAutoThreshold);
  protected readonly faceReviewThresholdDisplay = linkedSignal(() => this.processingConfig().faceReviewThreshold);
  protected readonly taggingWorkersDisplay      = linkedSignal(() => this.processingConfig().taggingWorkers);
  protected readonly captioningWorkersDisplay   = linkedSignal(() => this.processingConfig().captioningWorkers);

  protected readonly dupeDinoThresholdPct = computed((): number =>
    Math.round((1 - this.dupeDinoThresholdDisplay()) * 100)
  );

  protected readonly dupeDinoThresholdLabel = computed((): string => `${this.dupeDinoThresholdPct()} %`);

  protected readonly trainingNearDupeThresholdPct = computed((): number =>
    Math.round((1 - this.trainingNearDupeThresholdDisplay()) * 100)
  );

  protected readonly trainingNearDupeThresholdLabel = computed((): string => `${this.trainingNearDupeThresholdPct()} %`);

  protected readonly faceDetConfLabel = computed((): string => {
    const value = this.faceDetConfDisplay();
    if (value <= 0.35) { return `${value.toFixed(2)} — sehr sensibel (mehr Fehlalarme)`; }
    if (value <= 0.60) { return `${value.toFixed(2)} — ausgewogen`; }
    return `${value.toFixed(2)} — nur eindeutige Gesichter`;
  });

  protected readonly faceDetIouLabel = computed((): string => {
    const value = this.faceDetIouDisplay();
    if (value <= 0.35) { return `${value.toFixed(2)} — streng (wenig Überlappung)`; }
    if (value <= 0.55) { return `${value.toFixed(2)} — Standard`; }
    return `${value.toFixed(2)} — viel Überlappung erlaubt`;
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

  protected readonly reviewBelowAutoWarning = computed((): boolean =>
    this.processingConfig().faceReviewThreshold >= this.processingConfig().faceAutoThreshold
  );

  protected readonly suggestedTaggingWorkers = computed((): number | null =>
    this.vram()?.suggested_tagging_workers ?? null
  );

  protected readonly suggestedCaptioningWorkers = computed((): number | null =>
    this.vram()?.suggested_captioning_workers ?? null
  );

  constructor() {
    effect(() => {
      this.store.dispatch(modelsActions.loadConfig());
      this.store.dispatch(modelsActions.loadModels());
      this.store.dispatch(modelsActions.loadVram());
    });
  }

  patchProcessingConfig(patch: Partial<ProcessingConfig>): void {
    this.store.dispatch(modelsActions.updateProcessingConfig({ patch }));
  }

  onActiveCaptionerChange(manifestId: string): void {
    this.patchProcessingConfig({ activeCaptioner: manifestId });
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

  onDupeClipEnabledToggle(): void {
    this.patchProcessingConfig({ dupeClipEnabled: !this.processingConfig().dupeClipEnabled });
  }

  onRerankEnabledToggle(): void {
    this.patchProcessingConfig({ rerankEnabled: !this.processingConfig().rerankEnabled });
  }

  onRerankPoolSizeChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(500, Math.max(10, isNaN(raw) ? 100 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ rerankCandidatePoolSize: clamped });
  }

  onDupeDinoThresholdInput(target: HTMLInputElement): void {
    const pct = parseInt(target.value, 10);
    this.dupeDinoThresholdDisplay.set((100 - pct) / 100);
  }

  onDupeDinoThresholdChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    // DINOv2s Distanz-Regime ist noch nicht am realen Set kalibriert (P37 Phase 4) —
    // Bereich bewusst weiter als beim alten CLIP-Slider (60-99 statt 90-99 %).
    const pct = Math.min(99, Math.max(60, isNaN(raw) ? 92 : raw));
    this.patchProcessingConfig({ dupeDinoThreshold: (100 - pct) / 100 });
  }

  onTrainingNearDupeThresholdInput(target: HTMLInputElement): void {
    const pct = parseInt(target.value, 10);
    this.trainingNearDupeThresholdDisplay.set((100 - pct) / 100);
  }

  onTrainingNearDupeThresholdChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    // Gleiches unkalibriertes DINOv2-Distanz-Regime wie der Haupt-Slider (P37 Phase 4),
    // bewusst lockerer Default (88 % statt 92 %). Bereich 60-99 % analog.
    const pct = Math.min(99, Math.max(60, isNaN(raw) ? 88 : raw));
    this.patchProcessingConfig({ trainingNearDupeDinoThreshold: (100 - pct) / 100 });
  }

  onFaceDetConfInput(target: HTMLInputElement): void {
    this.faceDetConfDisplay.set(parseFloat(target.value));
  }

  onFaceDetConfChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(0.9, Math.max(0.1, isNaN(raw) ? 0.5 : raw));
    this.patchProcessingConfig({ faceDetConfThreshold: clamped });
  }

  onFaceDetIouInput(target: HTMLInputElement): void {
    this.faceDetIouDisplay.set(parseFloat(target.value));
  }

  onFaceDetIouChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(0.9, Math.max(0.1, isNaN(raw) ? 0.45 : raw));
    this.patchProcessingConfig({ faceDetIouThreshold: clamped });
  }

  onFaceCropPaddingChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(150, Math.max(0, isNaN(raw) ? 40 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ faceCropPadding: clamped });
  }

  onFaceAutoThresholdInput(target: HTMLInputElement): void {
    this.faceAutoThresholdDisplay.set(parseFloat(target.value));
  }

  onFaceAutoThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(0.95, Math.max(0.4, isNaN(raw) ? 0.6 : raw));
    this.patchProcessingConfig({ faceAutoThreshold: clamped });
  }

  onFaceReviewThresholdInput(target: HTMLInputElement): void {
    this.faceReviewThresholdDisplay.set(parseFloat(target.value));
  }

  onFaceReviewThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(0.85, Math.max(0.2, isNaN(raw) ? 0.45 : raw));
    this.patchProcessingConfig({ faceReviewThreshold: clamped });
  }

  onFaceMinClusterSizeChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(20, Math.max(2, isNaN(raw) ? 3 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ faceMinClusterSize: clamped });
  }

  onTaggingWorkersInput(target: HTMLInputElement): void {
    this.taggingWorkersDisplay.set(parseInt(target.value, 10));
  }

  onTaggingWorkersChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(4, Math.max(1, isNaN(raw) ? 1 : raw));
    this.patchProcessingConfig({ taggingWorkers: clamped });
  }

  onCaptioningWorkersInput(target: HTMLInputElement): void {
    this.captioningWorkersDisplay.set(parseInt(target.value, 10));
  }

  onCaptioningWorkersChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(4, Math.max(1, isNaN(raw) ? 1 : raw));
    this.patchProcessingConfig({ captioningWorkers: clamped });
  }
}
