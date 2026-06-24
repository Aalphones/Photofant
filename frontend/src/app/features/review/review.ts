import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { ReviewDupes } from './review-dupes/review-dupes';
import { ReviewFaces } from './review-faces/review-faces';
import { ReviewUnknown } from './review-unknown/review-unknown';
import { ReviewReconcile } from './review-reconcile/review-reconcile';

type ReviewTab = 'gesichter' | 'duplikate' | 'unbekannt' | 'abgleich';

@Component({
  selector: 'pf-review',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReviewDupes, ReviewFaces, ReviewUnknown, ReviewReconcile],
  templateUrl: './review.html',
  styleUrl: './review.scss',
})
export class Review {
  readonly activeTab = signal<ReviewTab>('duplikate');

  goTab(tab: ReviewTab): void {
    this.activeTab.set(tab);
  }
}
