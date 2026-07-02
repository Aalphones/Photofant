import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
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

  protected scoreClass(pct: number): 'high' | 'mid' | 'low' {
    if (pct >= 90) return 'high';
    if (pct >= 75) return 'mid';
    return 'low';
  }

  protected thumbnailUrl(asset: { id: number; content_hash: string }): string {
    return `/api/assets/${asset.id}/thumbnail?size=256&v=${asset.content_hash.slice(0, 8)}`;
  }

  protected onCompare(): void {
    this.compare.emit(this.pair());
  }

  protected onResolve(resolution: 'a_is_original' | 'b_is_original' | 'delete_a' | 'delete_b' | 'dismiss'): void {
    this.resolve.emit({ pair: this.pair(), resolution });
  }
}
