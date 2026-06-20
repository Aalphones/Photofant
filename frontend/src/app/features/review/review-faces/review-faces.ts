import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import type { FaceReviewItem, PersonDto } from '@photofant/models';
import { reviewActions, reviewSelectors, personsActions, personsSelectors } from '@photofant/store';

@Component({
  selector: 'pf-review-faces',
  imports: [Icon],
  templateUrl: './review-faces.html',
  styleUrl: './review-faces.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewFaces implements OnInit {
  private readonly store = inject(Store);

  protected readonly items = this.store.selectSignal(reviewSelectors.selectFaceQueue);
  protected readonly isLoading = this.store.selectSignal(reviewSelectors.selectFaceQueueLoading);
  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly currentIndex = signal(0);
  protected readonly assignOpen = signal(false);
  protected readonly assignQuery = signal('');

  protected readonly currentItem = computed((): FaceReviewItem | null => {
    const allItems = this.items();
    const index = this.currentIndex();
    return index < allItems.length ? allItems[index] ?? null : null;
  });

  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.assignQuery().toLowerCase();
    return this.persons().filter((person: PersonDto) =>
      !person.is_unknown && (!query || (person.name ?? '').toLowerCase().includes(query))
    );
  });

  protected readonly progress = computed(() => {
    const total = this.items().length;
    const index = this.currentIndex();
    return { current: Math.min(index + 1, total), total };
  });

  ngOnInit(): void {
    this.store.dispatch(reviewActions.loadFaceQueue());
    this.store.dispatch(personsActions.loadPersons());
  }

  protected onConfirm(): void {
    const item = this.currentItem();
    if (item === null) return;
    this.store.dispatch(reviewActions.resolveFaceReview({ faceId: item.face_id, action: 'confirm' }));
    this.advanceToNext();
  }

  protected onReject(): void {
    const item = this.currentItem();
    if (item === null) return;
    this.store.dispatch(reviewActions.resolveFaceReview({ faceId: item.face_id, action: 'reject' }));
    this.advanceToNext();
  }

  protected onReassign(personId: number): void {
    const item = this.currentItem();
    if (item === null) return;
    this.store.dispatch(reviewActions.resolveFaceReview({ faceId: item.face_id, action: 'reassign', personId }));
    this.assignOpen.set(false);
    this.assignQuery.set('');
    this.advanceToNext();
  }

  protected onSelectItem(index: number): void {
    this.currentIndex.set(index);
    this.assignOpen.set(false);
  }

  protected onPrev(): void {
    this.currentIndex.update((index: number) => Math.max(0, index - 1));
  }

  protected onNext(): void {
    this.currentIndex.update((index: number) => Math.min(this.items().length - 1, index + 1));
  }

  protected toggleAssign(): void {
    this.assignOpen.update((open: boolean) => !open);
    this.assignQuery.set('');
  }

  protected scorePercent(score: number): number {
    return Math.round(score * 100);
  }

  protected scoreClass(score: number): string {
    if (score >= 0.85) return 'high';
    if (score >= 0.7) return 'mid';
    return '';
  }

  private advanceToNext(): void {
    const total = this.items().length;
    const current = this.currentIndex();
    if (current + 1 < total) {
      this.currentIndex.set(current + 1);
    }
  }
}
