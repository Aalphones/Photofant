import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  viewChild,
} from '@angular/core';
import type { FaceGalleryItemDto } from '@photofant/models';
import { FaceCell } from '../face-cell/face-cell';

@Component({
  selector: 'pf-face-grid',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FaceCell],
  templateUrl: './face-grid.html',
  styleUrl: './face-grid.scss',
})
export class FaceGrid {
  private readonly destroyRef = inject(DestroyRef);

  readonly faceItems = input.required<FaceGalleryItemDto[]>();
  readonly isLoading = input.required<boolean>();

  readonly openFace = output<{ faceId: number; assetId: number | null }>();
  readonly loadMore = output<void>();

  private readonly sentinel = viewChild.required<ElementRef<HTMLDivElement>>('loadSentinel');

  protected readonly CELL_SIZE = 160;

  protected readonly skeletonCount = 20;

  constructor() {
    afterNextRender(() => {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry?.isIntersecting) {
            this.loadMore.emit();
          }
        },
        { rootMargin: '400px' }
      );
      observer.observe(this.sentinel().nativeElement);
      this.destroyRef.onDestroy(() => observer.disconnect());
    });
  }

  protected onOpenFace(event: { faceId: number; assetId: number | null }): void {
    this.openFace.emit(event);
  }
}
