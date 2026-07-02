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
    const pair = this.pair();
    const scores = [pair.phash_similarity_pct, pair.clip_similarity_pct].filter(
      (pct: number | null): pct is number => pct !== null,
    );
    return scores.length > 0 ? Math.max(...scores) : 0;
  });

  protected readonly scoreSubtitle = computed<string>(() => {
    const pair = this.pair();
    const parts: string[] = [];
    if (pair.phash_similarity_pct !== null) parts.push(`Pixel: ${pair.phash_similarity_pct}%`);
    if (pair.clip_similarity_pct !== null) parts.push(`Inhalt: ${pair.clip_similarity_pct}%`);
    return parts.join(' · ');
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
