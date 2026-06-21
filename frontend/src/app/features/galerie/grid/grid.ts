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
import type { AssetDto, AssetGroup, Density } from '@photofant/models';
import { BASE_HEIGHTS } from '@photofant/models';
import { GalerieCell } from '../cell/cell';

const SKELETON_RATIOS = [1.4, 0.75, 1.0, 1.6, 0.85, 1.2, 0.7, 1.5, 1.1, 0.9];

@Component({
  selector: 'pf-galerie-grid',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GalerieCell],
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

  readonly openAsset  = output<number>();
  readonly selectAll  = output<number[]>();
  readonly loadMore   = output<void>();
  readonly batchBind  = output<number>();

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

  protected groupIds(group: AssetGroup): number[] {
    return group.assets.map((asset: AssetDto) => asset.id);
  }

  protected onOpenAsset(id: number): void {
    this.openAsset.emit(id);
  }

  protected onBatchBind(id: number): void {
    this.batchBind.emit(id);
  }

  protected onSelectAll(ids: number[]): void {
    this.selectAll.emit(ids);
  }
}
