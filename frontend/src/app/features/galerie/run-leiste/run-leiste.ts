import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';
import type { ComfyUIWorkflow, ResolutionRun } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { Icon } from '@photofant/ui';

export interface RunFirePayload {
  workflowKey: string;
  inputs: Record<string, number | number[]>;
  faceInputs: Record<string, number | number[]>;
  prompt: string | null;
  resolution: ResolutionRun | null;
}

@Component({
  selector: 'pf-run-leiste',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './run-leiste.html',
  styleUrl: './run-leiste.scss',
})
export class RunLeiste {
  private readonly assetService = inject(AssetService);

  readonly workflows    = input.required<ComfyUIWorkflow[]>();
  readonly activeWorkflow = input<ComfyUIWorkflow | null>(null);
  readonly bindings     = input<Record<string, number | number[]>>({});
  readonly faceBindings = input<Record<string, number | number[]>>({});
  readonly hashMap      = input<Record<number, string>>({});
  readonly armedSlotKey = input<string | null>(null);
  readonly batchAxisKey = input<string | null>(null);
  readonly isFiring     = input<boolean>(false);

  readonly workflowChanged = output<string | null>();
  readonly slotArmed       = output<string | null>();
  readonly fire            = output<RunFirePayload>();
  readonly closed          = output<void>();

  protected readonly prompt      = signal('');
  protected readonly megapixels  = signal(1.0);

  constructor() {
    // Prompt/Auflösung zurücksetzen, wenn der Workflow wechselt.
    let lastKey: string | null = null;
    effect((): void => {
      const key = this.activeWorkflow()?.key ?? null;
      if (key !== lastKey) {
        lastKey = key;
        this.prompt.set('');
        this.megapixels.set(1.0);
      }
    });
  }

  protected readonly fireCount = computed((): number => {
    const batchKey = this.batchAxisKey();
    if (!batchKey) { return 1; }
    const assetBatch = this.bindings()[batchKey];
    if (Array.isArray(assetBatch)) { return assetBatch.length; }
    const faceBatch = this.faceBindings()[batchKey];
    return Array.isArray(faceBatch) ? faceBatch.length : 1;
  });

  // Alle Bild-Slots müssen gebunden sein (Masken-Slots ausgenommen).
  protected readonly canFire = computed((): boolean => {
    const workflow = this.activeWorkflow();
    if (!workflow) { return false; }
    const bindings = this.bindings();
    const faceBindings = this.faceBindings();
    return workflow.inputs
      .filter((inp) => inp.kind !== 'mask')
      .every((inp) => {
        const assetValue = bindings[inp.key];
        const assetBound = assetValue != null && (!Array.isArray(assetValue) || assetValue.length > 0);
        if (assetBound) { return true; }
        const faceValue = faceBindings[inp.key];
        return faceValue != null && (!Array.isArray(faceValue) || faceValue.length > 0);
      });
  });

  protected slotThumbnail(slotKey: string): string | null {
    const faceBinding = this.faceBindings()[slotKey];
    if (faceBinding != null) {
      const faceId = Array.isArray(faceBinding) ? faceBinding[0] ?? null : faceBinding;
      if (faceId != null) { return `/api/faces/${faceId}/thumbnail`; }
    }
    const binding = this.bindings()[slotKey];
    if (binding == null) { return null; }
    const assetId = Array.isArray(binding) ? binding[0] ?? null : binding;
    if (assetId == null) { return null; }
    return this.assetService.thumbnailUrl(assetId, 256, this.hashMap()[assetId]);
  }

  protected slotBatchCount(slotKey: string): number {
    const assetBinding = this.bindings()[slotKey];
    if (Array.isArray(assetBinding)) { return assetBinding.length; }
    const faceBinding = this.faceBindings()[slotKey];
    return Array.isArray(faceBinding) ? faceBinding.length : 0;
  }

  protected isSlotArmed(slotKey: string): boolean {
    return this.armedSlotKey() === slotKey;
  }

  protected isSlotBatchAxis(slotKey: string): boolean {
    return this.batchAxisKey() === slotKey;
  }

  protected isBound(slotKey: string): boolean {
    const assetValue = this.bindings()[slotKey];
    if (assetValue != null && (!Array.isArray(assetValue) || assetValue.length > 0)) { return true; }
    const faceValue = this.faceBindings()[slotKey];
    return faceValue != null && (!Array.isArray(faceValue) || faceValue.length > 0);
  }

  protected onSlotClick(slotKey: string, kind: string): void {
    if (kind === 'mask') { return; }
    const nextArmed = this.armedSlotKey() === slotKey ? null : slotKey;
    this.slotArmed.emit(nextArmed);
  }

  protected onFire(): void {
    const workflow = this.activeWorkflow();
    if (!workflow || !this.canFire() || this.isFiring()) { return; }
    const promptText = this.prompt().trim();
    const resolution = workflow.resolution;
    this.fire.emit({
      workflowKey: workflow.key,
      inputs: this.bindings(),
      faceInputs: this.faceBindings(),
      prompt: workflow.prompt != null && promptText.length > 0 ? promptText : null,
      resolution: resolution != null
        ? { megapixels: this.megapixels(), aspect_ratio: resolution.aspectDefault }
        : null,
    });
  }

  protected onPromptInput(event: Event): void {
    this.prompt.set((event.target as HTMLInputElement).value);
  }

  protected onMegapixelsInput(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(value) && value > 0) {
      this.megapixels.set(value);
    }
  }

  protected onWorkflowSelect(event: Event): void {
    const selectEl = event.target as HTMLSelectElement;
    const workflowKey = selectEl.value || null;
    this.workflowChanged.emit(workflowKey);
  }
}
