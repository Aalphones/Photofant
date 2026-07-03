import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { injectVirtualizer } from '@tanstack/angular-virtual';
import type { AssetDto, Density, FaceGalleryItemDto } from '@photofant/models';
import { BASE_HEIGHTS } from '@photofant/models';
import { GalerieCell } from '../cell/cell';
import { FaceCell } from '../face-cell/face-cell';
import { buildLayoutItems, computeRows, GRID_GAP, ROW_HEIGHT } from './row-layout';
import type { LayoutItem, VirtualRow } from './row-layout';

const SKELETON_RATIOS = [1.4, 0.75, 1.0, 1.6, 0.85, 1.2, 0.7, 1.5, 1.1, 0.9];
const OVERSCAN = 5;

@Component({
  selector: 'pf-galerie-grid',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GalerieCell, FaceCell],
  templateUrl: './grid.html',
  styleUrl: './grid.scss',
})
export class GalerieGrid {
  private readonly destroyRef = inject(DestroyRef);
  private readonly hostEl = inject(ElementRef<HTMLElement>);

  readonly assets         = input.required<AssetDto[]>();
  readonly density        = input.required<Density>();
  readonly isLoading      = input.required<boolean>();
  readonly hasMore        = input<boolean>(false);
  readonly selectionMode  = input<boolean>(false);
  readonly selectedIds    = input<number[]>([]);
  readonly isArmed        = input<boolean>(false);

  readonly facesMap   = input<Map<number, FaceGalleryItemDto[]>>(new Map());

  readonly openAsset    = output<{ id: number; versionId: number | null }>();
  readonly openFace     = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
  readonly loadMore     = output<void>();
  readonly batchBind    = output<number>();
  readonly rangeSelect  = output<number>();

  private readonly scrollEl = viewChild.required<ElementRef<HTMLElement>>('scrollContainer');

  protected readonly baseHeight = computed((): number => BASE_HEIGHTS[this.density()]);

  protected readonly skeletonCells = SKELETON_RATIOS.map((ratio, index) => ({ ratio, index }));

  protected readonly isEmpty = computed((): boolean =>
    !this.isLoading() && this.assets().length === 0
  );

  private readonly containerWidth = signal<number>(0);

  protected readonly rows = computed((): VirtualRow[] => {
    if (this.containerWidth() === 0) return [];
    return computeRows(buildLayoutItems(this.assets(), this.facesMap()), this.containerWidth(), this.baseHeight(), GRID_GAP);
  });

  protected readonly virtualizer = injectVirtualizer(() => ({
    count: this.rows().length,
    scrollElement: this.scrollEl(),
    estimateSize: () => ROW_HEIGHT(this.baseHeight()),
    overscan: OVERSCAN,
    // Wir lesen getTotalSize()/getVirtualItems()/range() als Signals direkt im Template/effect —
    // Angulars eigene Signal-Reaktivität reicht aus. Der eingebaute ApplicationRef.tick() kollidiert
    // damit rekursiv (NG0101), wenn eine Row-Änderung während eines laufenden Tick eine weitere CD auslöst
    // (z.B. via loadMore-Effect). Siehe FINDINGS.md.
    useApplicationRefTick: false,
  }));

  constructor() {
    afterNextRender(() => {
      let rafId: number | null = null;
      const resizeObserver = new ResizeObserver(([entry]) => {
        if (rafId !== null) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
          if (entry) this.containerWidth.set(entry.contentRect.width);
          rafId = null;
        });
      });
      resizeObserver.observe(this.hostEl.nativeElement);
      this.destroyRef.onDestroy(() => {
        resizeObserver.disconnect();
        if (rafId !== null) cancelAnimationFrame(rafId);
      });
    });

    effect(() => {
      const range = this.virtualizer.range();
      const totalRows = this.rows().length;
      if (
        range !== null &&
        range.endIndex >= totalRows - OVERSCAN - 3 &&
        this.hasMore() &&
        !this.isLoading()
      ) {
        this.loadMore.emit();
      }
    });
  }

  protected isAssetSelected(assetId: number): boolean {
    return this.selectedIds().includes(assetId);
  }

  // Invariant aus buildLayoutItems: assetData ist bei kind === 'asset' immer gesetzt.
  protected assetOf(item: LayoutItem): AssetDto {
    return item.assetData!;
  }

  // Invariant aus buildLayoutItems: faceData ist bei kind === 'face' immer gesetzt.
  protected faceOf(item: LayoutItem): FaceGalleryItemDto {
    return item.faceData!;
  }

  protected onOpenFace(event: { faceId: number; assetId: number | null; versionId: number | null }): void {
    this.openFace.emit(event);
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
}
