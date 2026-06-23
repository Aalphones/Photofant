import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';
import { ROLE_META, formatModelSize } from '@photofant/models';
import type { ModelView, VariantSpec, VramResponse } from '@photofant/models';

@Component({
  selector: 'pf-download-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './download-dialog.html',
  styleUrl: './download-dialog.scss',
})
export class DownloadDialog {
  readonly model = input.required<ModelView>();
  readonly modelsDir = input<string | null>(null);
  readonly vram = input<VramResponse | null>(null);
  readonly confirm = output<{ model: ModelView; licenseAck: boolean; variant: string | null }>();
  readonly cancel = output<void>();

  protected readonly licenseAgreed = signal<boolean>(false);
  protected readonly selectedVariant = signal<string | null>(null);
  protected readonly roleMeta = computed(() =>
    ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role }
  );
  protected readonly variants = computed((): VariantSpec[] => {
    const caps = this.model().capabilities as Record<string, unknown> | null;
    if (caps === null || caps === undefined) { return []; }
    return (caps['variants'] as VariantSpec[] | undefined) ?? [];
  });
  protected readonly recommendedVariant = computed((): string | null => {
    const vramData = this.vram();
    if (vramData === null) { return null; }
    const rec = vramData.recommendations.find(
      (recommendation: { model_id: string }) => recommendation.model_id === this.model().id
    );
    return rec?.recommended_variant ?? null;
  });
  protected readonly activeVariant = computed((): string | null =>
    this.selectedVariant() ?? this.recommendedVariant()
  );
  protected readonly isDisabled = computed(() =>
    this.model().licenseNc && !this.licenseAgreed()
  );
  protected readonly targetPath = computed(() => {
    const dir = this.modelsDir() ?? '~/photofant/models';
    return `${dir}/${this.model().id}`;
  });

  protected toggleLicense(): void {
    this.licenseAgreed.update((agreed: boolean) => !agreed);
  }

  protected selectVariant(name: string): void {
    this.selectedVariant.set(name);
  }

  protected handleConfirm(): void {
    if (this.isDisabled()) { return; }
    this.confirm.emit({
      model: this.model(),
      licenseAck: this.licenseAgreed() || !this.model().licenseNc,
      variant: this.activeVariant(),
    });
  }

  protected handleCancel(): void { this.cancel.emit(); }
  protected handleScrimClick(): void { this.cancel.emit(); }

  protected formatSize(bytes: number | null): string {
    return formatModelSize(bytes);
  }
}
