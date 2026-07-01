import { ChangeDetectionStrategy, Component, DestroyRef, HostListener, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import type { CollectionDupePair, DupeReviewResolution } from '@photofant/models';
import { CollectionService } from '@photofant/services';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-training-set-dupes',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './training-set-dupes.html',
  styleUrl: './training-set-dupes.scss',
})
export class TrainingSetDupes {
  private readonly collectionService = inject(CollectionService);
  private readonly destroyRef = inject(DestroyRef);

  readonly collectionId = input.required<number>();
  readonly close = output<void>();
  readonly resolved = output<void>();

  protected readonly threshold = signal(10);
  protected readonly isLoading = signal(false);
  protected readonly pairs = signal<CollectionDupePair[]>([]);
  protected readonly comparePair = signal<CollectionDupePair | null>(null);

  constructor() {
    this.fetch();
  }

  protected onThresholdChange(value: number): void {
    this.threshold.set(value);
  }

  protected fetch(): void {
    this.isLoading.set(true);
    this.collectionService.getDuplicates(this.collectionId(), this.threshold())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((pairs: CollectionDupePair[]) => {
        this.pairs.set(pairs);
        this.isLoading.set(false);
      });
  }

  protected thumbnailUrl(assetId: number, contentHash: string): string {
    return `/api/assets/${assetId}/thumbnail?size=256&v=${contentHash.slice(0, 8)}`;
  }

  protected fullUrl(assetId: number): string {
    return `/api/assets/${assetId}/thumbnail?size=1024`;
  }

  protected onCompare(pair: CollectionDupePair): void {
    this.comparePair.set(pair);
  }

  protected onCloseCompare(): void {
    this.comparePair.set(null);
  }

  protected resolve(pair: CollectionDupePair, resolution: DupeReviewResolution): void {
    this.collectionService.resolveDuplicate(this.collectionId(), pair.asset_a_id, pair.asset_b_id, resolution)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.pairs.update((list: CollectionDupePair[]) =>
          list.filter((current: CollectionDupePair) =>
            !(current.asset_a_id === pair.asset_a_id && current.asset_b_id === pair.asset_b_id)));
        if (this.comparePair()?.asset_a_id === pair.asset_a_id && this.comparePair()?.asset_b_id === pair.asset_b_id) {
          this.comparePair.set(null);
        }
        if (resolution !== 'keep_both') { this.resolved.emit(); }
      });
  }

  @HostListener('document:keydown', ['$event'])
  protected onKeyDown(event: KeyboardEvent): void {
    const pair = this.comparePair();
    if (pair == null) { return; }
    if (event.key === 'ArrowLeft') { this.resolve(pair, 'keep_left'); }
    else if (event.key === 'ArrowRight') { this.resolve(pair, 'keep_right'); }
    else if (event.key.toLowerCase() === 'b') { this.resolve(pair, 'keep_both'); }
    else if (event.key === 'Escape') { this.onCloseCompare(); }
  }

  protected onClose(): void {
    this.close.emit();
  }
}
