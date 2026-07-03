import { ChangeDetectionStrategy, Component, effect, inject, OnInit, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { reviewActions, reviewSelectors } from '@photofant/store';
import type { DupePair, DupeResolution } from '@photofant/models';
import { DupePairRow } from './dupe-pair-row/dupe-pair-row';
import { DupeCompare } from './dupe-compare/dupe-compare';

@Component({
  selector: 'pf-review-dupes',
  imports: [Icon, DupePairRow, DupeCompare],
  templateUrl: './review-dupes.html',
  styleUrl: './review-dupes.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewDupes implements OnInit {
  private readonly store = inject(Store);

  protected readonly pairs = this.store.selectSignal(reviewSelectors.selectAll);
  protected readonly pairCount = this.store.selectSignal(reviewSelectors.selectTotal);
  protected readonly total = this.store.selectSignal(reviewSelectors.selectServerTotal);
  protected readonly hasMore = this.store.selectSignal(reviewSelectors.selectHasMore);
  protected readonly isLoading = this.store.selectSignal(reviewSelectors.selectIsLoading);
  protected readonly isLoadingMore = this.store.selectSignal(reviewSelectors.selectIsLoadingMore);
  protected readonly comparePair = signal<DupePair | null>(null);

  private readonly resolvingId = signal<number | null>(null);

  constructor() {
    effect(() => {
      const id = this.resolvingId();
      const pairs = this.pairs();
      if (id !== null && !pairs.some((pair: DupePair) => pair.id === id)) {
        this.resolvingId.set(null);
        this.comparePair.set(pairs[0] ?? null);
      }
    });
  }

  ngOnInit(): void {
    this.store.dispatch(reviewActions.loadDupePairs());
  }

  protected onCompare(pair: DupePair): void {
    this.comparePair.set(pair);
  }

  protected onCloseCompare(): void {
    this.comparePair.set(null);
  }

  protected onResolve(event: { pair: DupePair; resolution: DupeResolution }): void {
    this.resolvingId.set(event.pair.id);
    this.store.dispatch(
      reviewActions.resolveDupePair({ itemId: event.pair.id, resolution: event.resolution }),
    );
    this.comparePair.set(null);
  }

  protected onScan(): void {
    this.store.dispatch(reviewActions.triggerDupeScan());
  }

  protected onLoadMore(): void {
    this.store.dispatch(reviewActions.loadMoreDupePairs());
  }
}
