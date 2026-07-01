import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  output,
  viewChild,
} from '@angular/core';
import type { AssetDto, AssetGroup, Density, FaceGalleryItemDto } from '@photofant/models';
import { BASE_HEIGHTS } from '@photofant/models';
import { GalerieCell } from '../cell/cell';
import { FaceCell } from '../face-cell/face-cell';

const SKELETON_RATIOS = [1.4, 0.75, 1.0, 1.6, 0.85, 1.2, 0.7, 1.5, 1.1, 0.9];

@Component({
  selector: 'pf-galerie-grid',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GalerieCell, FaceCell],
  templateUrl: './grid.html',
  styleUrl: './grid.scss',
})
export class GalerieGrid {
  private readonly destroyRef = inject(DestroyRef);

  readonly groups        = input.required<AssetGroup[]>();
  readonly density       = input.required<Density>();
  readonly isLoading     = input.required<boolean>();
  readonly selectionMode = input<boolean>(false);
  readonly selectedIds   = input<number[]>([]);
  readonly isArmed       = input<boolean>(false);

  readonly facesMap   = input<Map<number, FaceGalleryItemDto[]>>(new Map());

  readonly openAsset    = output<{ id: number; versionId: number | null }>();
  readonly openFace     = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
  readonly selectAll    = output<number[]>();
  readonly loadMore     = output<void>();
  readonly batchBind    = output<number>();
  readonly rangeSelect  = output<number>();

  private readonly sentinel = viewChild.required<ElementRef<HTMLDivElement>>('loadSentinel');

  protected readonly baseHeight = computed((): number => BASE_HEIGHTS[this.density()]);

  protected readonly skeletonCells = SKELETON_RATIOS.map((ratio, index) => ({ ratio, index }));

  protected readonly isEmpty = computed((): boolean =>
    !this.isLoading() && this.groups().every((group) => group.assets.length === 0)
  );

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

  protected isAssetSelected(assetId: number): boolean {
    return this.selectedIds().includes(assetId);
  }

  protected facesForAsset(assetId: number): FaceGalleryItemDto[] {
    return this.facesMap().get(assetId) ?? [];
  }

  protected onOpenFace(event: { faceId: number; assetId: number | null; versionId: number | null }): void {
    this.openFace.emit(event);
  }

  protected groupIds(group: AssetGroup): number[] {
    return group.assets.map((asset: AssetDto) => asset.id);
  }

  protected onOpenAsset(event: { id: number; versionId: number | null }): void {
    this.openAsset.emit(event);
  }

  protected onBatchBind(id: number): void {
    this.batchBind.emit(id);
  }

  protected onRangeSelect(id: number): void {
    this.rangeSelect.emit(id);
  }

  protected onSelectAll(ids: number[]): void {
    this.selectAll.emit(ids);
  }
}
