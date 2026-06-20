import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { ReviewDupes } from './review-dupes/review-dupes';
import { ReviewFaces } from './review-faces/review-faces';

type ReviewTab = 'gesichter' | 'duplikate';

@Component({
  selector: 'pf-review',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReviewDupes, ReviewFaces],
  templateUrl: './review.html',
  styleUrl: './review.scss',
})
export class Review {
  readonly activeTab = signal<ReviewTab>('duplikate');

  goTab(tab: ReviewTab): void {
    this.activeTab.set(tab);
  }
}
