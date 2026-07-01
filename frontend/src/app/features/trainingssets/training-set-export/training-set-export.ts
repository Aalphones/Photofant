import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { CollectionDetail } from '@photofant/models';
import type { SidecarMode } from '@photofant/services';
import { Icon } from '@photofant/ui';

export interface TrainingSetExportPayload {
  sidecar: SidecarMode | null;
  splitRatio: number | null;
  targetDir: string | null;
}

interface SidecarOption {
  key: SidecarMode | 'none';
  label: string;
  desc: string;
}

const SIDECAR_OPTIONS: SidecarOption[] = [
  { key: 'none', label: 'Keine', desc: 'Nur Bilder kopieren, keine Sidecar-Datei' },
  { key: 'tags', label: 'Tags', desc: 'Kommagetrennte Tag-Liste pro Bild' },
  { key: 'caption', label: 'Caption', desc: 'Effektive Caption (Override oder Original)' },
  { key: 'both', label: 'Beides', desc: 'Caption gefolgt von den Tags' },
];

@Component({
  selector: 'pf-training-set-export',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './training-set-export.html',
  styleUrl: './training-set-export.scss',
})
export class TrainingSetExport {
  readonly collection = input.required<CollectionDetail>();
  readonly apply = output<TrainingSetExportPayload>();
  readonly cancel = output<void>();

  protected readonly SIDECAR_OPTIONS = SIDECAR_OPTIONS;
  protected readonly sidecar = signal<SidecarOption['key']>('both');
  protected readonly splitEnabled = signal(false);
  protected readonly splitPercent = signal(90);
  protected targetDir = '';

  protected readonly defaultSplitPercent = computed((): number => {
    const ratio = this.collection().settings?.split_ratio;
    return ratio != null ? Math.round(ratio * 100) : 90;
  });

  protected readonly activeSidecarDesc = computed((): string =>
    SIDECAR_OPTIONS.find((option: SidecarOption) => option.key === this.sidecar())?.desc ?? '');

  protected selectSidecar(key: SidecarOption['key']): void {
    this.sidecar.set(key);
  }

  protected toggleSplit(): void {
    this.splitEnabled.update((enabled: boolean) => {
      const next = !enabled;
      if (next) { this.splitPercent.set(this.defaultSplitPercent()); }
      return next;
    });
  }

  protected onScrimClick(): void {
    this.cancel.emit();
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleApply(): void {
    const sidecarKey = this.sidecar();
    this.apply.emit({
      sidecar: sidecarKey === 'none' ? null : sidecarKey,
      splitRatio: this.splitEnabled() ? this.splitPercent() / 100 : null,
      targetDir: this.targetDir.trim() || null,
    });
  }
}
