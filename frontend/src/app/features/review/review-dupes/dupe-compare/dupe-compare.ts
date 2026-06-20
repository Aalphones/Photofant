import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Icon } from '@photofant/ui';
import type { DupePair, DupeResolution } from '@photofant/models';

@Component({
  selector: 'pf-dupe-compare',
  imports: [Icon],
  templateUrl: './dupe-compare.html',
  styleUrl: './dupe-compare.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DupeCompare {
  readonly pair = input.required<DupePair>();
  readonly close = output<void>();
  readonly resolve = output<{ pair: DupePair; resolution: DupeResolution }>();

  protected readonly similarity = computed<number>(() => {
    const distance = this.pair().phash_distance;
    return Math.max(0, Math.round((1 - distance / 64) * 100));
  });

  protected fileUrl(assetId: number): string {
    return `/api/assets/${assetId}/thumbnail?size=1024`;
  }

  protected onScrimClick(): void {
    this.close.emit();
  }

  protected onModalClick(event: MouseEvent): void {
    event.stopPropagation();
  }

  protected onResolve(resolution: DupeResolution): void {
    this.resolve.emit({ pair: this.pair(), resolution });
  }

  protected onClose(): void {
    this.close.emit();
  }
}
