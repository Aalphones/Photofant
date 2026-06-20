import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
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
  protected readonly isLoading = this.store.selectSignal(reviewSelectors.selectIsLoading);
  protected readonly comparePair = signal<DupePair | null>(null);

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
    this.store.dispatch(
      reviewActions.resolveDupePair({ itemId: event.pair.id, resolution: event.resolution }),
    );
    this.comparePair.set(null);
  }

  protected onScan(): void {
    this.store.dispatch(reviewActions.triggerDupeScan());
  }
}
