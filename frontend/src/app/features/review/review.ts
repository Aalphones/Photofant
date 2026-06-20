import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { ReviewDupes } from './review-dupes/review-dupes';

type ReviewTab = 'gesichter' | 'duplikate';

@Component({
  selector: 'pf-review',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReviewDupes],
  templateUrl: './review.html',
  styleUrl: './review.scss',
})
export class Review {
  readonly activeTab = signal<ReviewTab>('duplikate');

  goTab(tab: ReviewTab): void {
    this.activeTab.set(tab);
  }
}
