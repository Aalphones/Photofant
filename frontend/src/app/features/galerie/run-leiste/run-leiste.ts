import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import type { ComfyUIWorkflow, WorkflowToggle } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { Icon } from '@photofant/ui';

export interface RunFirePayload {
  workflowKey: string;
  inputs: Record<string, number | number[]>;
  faceInputs: Record<string, number | number[]>;
  versionInputs: Record<string, number | number[]>;
  toggles: Record<string, boolean>;
}

export interface ToggleChangedEvent {
  key: string;
  value: boolean;
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
  readonly bindings        = input<Record<string, number | number[]>>({});
  readonly faceBindings    = input<Record<string, number | number[]>>({});
  readonly versionBindings = input<Record<string, number | number[]>>({});
  readonly toggleBindings  = input<Record<string, boolean>>({});
  readonly hashMap         = input<Record<number, string>>({});
  readonly armedSlotKey = input<string | null>(null);
  readonly batchAxisKey = input<string | null>(null);
  readonly isFiring     = input<boolean>(false);

  readonly workflowChanged = output<string | null>();
  readonly slotArmed       = output<string | null>();
  readonly toggleChanged   = output<ToggleChangedEvent>();
  readonly fire            = output<RunFirePayload>();
  readonly closed          = output<void>();

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
    const versionBindings = this.versionBindings();
    return workflow.inputs
      .filter((inp) => inp.kind !== 'mask')
      .every((inp) => {
        const assetValue = bindings[inp.key];
        if (assetValue != null && (!Array.isArray(assetValue) || assetValue.length > 0)) { return true; }
        const faceValue = faceBindings[inp.key];
        if (faceValue != null && (!Array.isArray(faceValue) || faceValue.length > 0)) { return true; }
        const versionValue = versionBindings[inp.key];
        return versionValue != null && (!Array.isArray(versionValue) || versionValue.length > 0);
      });
  });

  protected slotThumbnail(slotKey: string): string | null {
    const faceBinding = this.faceBindings()[slotKey];
    if (faceBinding != null) {
      const faceId = Array.isArray(faceBinding) ? faceBinding[0] ?? null : faceBinding;
      if (faceId != null) { return `/api/faces/${faceId}/thumbnail`; }
    }
    const versionBinding = this.versionBindings()[slotKey];
    if (versionBinding != null) {
      const versionId = Array.isArray(versionBinding) ? versionBinding[0] ?? null : versionBinding;
      if (versionId != null) { return `/api/versions/${versionId}/thumbnail`; }
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
    if (Array.isArray(faceBinding)) { return faceBinding.length; }
    const versionBinding = this.versionBindings()[slotKey];
    return Array.isArray(versionBinding) ? versionBinding.length : 0;
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
    if (faceValue != null && (!Array.isArray(faceValue) || faceValue.length > 0)) { return true; }
    const versionValue = this.versionBindings()[slotKey];
    return versionValue != null && (!Array.isArray(versionValue) || versionValue.length > 0);
  }

  protected onSlotClick(slotKey: string, kind: string): void {
    if (kind === 'mask') { return; }
    const nextArmed = this.armedSlotKey() === slotKey ? null : slotKey;
    this.slotArmed.emit(nextArmed);
  }

  protected onFire(): void {
    const workflow = this.activeWorkflow();
    if (!workflow || !this.canFire() || this.isFiring()) { return; }
    this.fire.emit({
      workflowKey: workflow.key,
      inputs: this.bindings(),
      faceInputs: this.faceBindings(),
      versionInputs: this.versionBindings(),
      toggles: this.toggleBindings(),
    });
  }

  protected toggleValue(toggle: WorkflowToggle): boolean {
    const bound = this.toggleBindings()[toggle.key];
    return bound ?? toggle.default;
  }

  protected onToggleClick(toggle: WorkflowToggle): void {
    this.toggleChanged.emit({ key: toggle.key, value: !this.toggleValue(toggle) });
  }

  protected onWorkflowSelect(event: Event): void {
    const selectEl = event.target as HTMLSelectElement;
    const workflowKey = selectEl.value || null;
    this.workflowChanged.emit(workflowKey);
  }
}
