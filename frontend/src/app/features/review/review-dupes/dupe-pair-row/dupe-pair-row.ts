import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Icon } from '@photofant/ui';
import type { DupePair } from '@photofant/models';

@Component({
  selector: 'pf-dupe-pair-row',
  imports: [Icon],
  templateUrl: './dupe-pair-row.html',
  styleUrl: './dupe-pair-row.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DupePairRow {
  readonly pair = input.required<DupePair>();
  readonly compare = output<DupePair>();
  readonly resolve = output<{ pair: DupePair; resolution: 'a_is_original' | 'b_is_original' | 'delete_a' | 'delete_b' | 'dismiss' }>();

  protected readonly similarity = computed<number>(() => {
    const distance = this.pair().phash_distance;
    return Math.max(0, Math.round((1 - distance / 64) * 100));
  });

  protected readonly similarityClass = computed<string>(() => {
    const pct = this.similarity();
    if (pct >= 90) return 'high';
    if (pct >= 75) return 'mid';
    return 'low';
  });

  protected thumbnailUrl(assetId: number): string {
    return `/api/assets/${assetId}/thumbnail?size=256`;
  }

  protected onCompare(): void {
    this.compare.emit(this.pair());
  }

  protected onResolve(resolution: 'a_is_original' | 'b_is_original' | 'delete_a' | 'delete_b' | 'dismiss'): void {
    this.resolve.emit({ pair: this.pair(), resolution });
  }
}
