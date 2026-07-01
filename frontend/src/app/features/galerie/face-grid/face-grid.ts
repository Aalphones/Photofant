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

  readonly openFace = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
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

  protected onOpenFace(event: { faceId: number; assetId: number | null; versionId: number | null }): void {
    this.openFace.emit(event);
  }

  // Version-Pseudo-Einträge teilen ihre `id` mit dem zugehörigen Face (siehe Backend
  // FaceGalleryItemDto: `id=face.id` für beide Zweige) — track allein über `face.id`
  // würde Angular bei mehreren Stapel-Mitgliedern denselben Key für verschiedene
  // Einträge geben und die N+1-Kacheln-AK aus Phase 3 brechen (analog zum
  // Entity-Key-Fund aus Phase 2, siehe FINDINGS).
  protected trackFace(face: FaceGalleryItemDto): string {
    return face.version_id != null ? `v${face.version_id}` : `f${face.id}`;
  }
}
