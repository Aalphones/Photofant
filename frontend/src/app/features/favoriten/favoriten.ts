import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import {
  collectionsActions,
  collectionsSelectors,
  filtersActions,
  filtersSelectors,
  galleryActions,
  gallerySelectors,
  personsActions,
} from '@photofant/store';
import { AssetService } from '@photofant/services';
import { GalerieGrid } from '../galerie/grid/grid';
import { Lightbox } from '../galerie/lightbox/lightbox';
import { FilterRail } from '../galerie/filter-rail/filter-rail';
import { SubToolbar } from '../galerie/sub-toolbar/sub-toolbar';
import { BulkBar, ExportDialog, Icon } from '@photofant/ui';
import type { ExportDialogFilters } from '@photofant/ui';

@Component({
  selector: 'pf-favoriten',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SubToolbar, GalerieGrid, Lightbox, FilterRail, Icon, BulkBar, ExportDialog],
  templateUrl: './favoriten.html',
  styleUrl: './favoriten.scss',
})
export class Favoriten {
  private readonly store        = inject(Store);
  private readonly router       = inject(Router);
  private readonly route        = inject(ActivatedRoute);
  private readonly assetService = inject(AssetService);
  private readonly destroyRef   = inject(DestroyRef);

  protected readonly density       = this.store.selectSignal(filtersSelectors.density);
  protected readonly isLoading     = this.store.selectSignal(gallerySelectors.selectIsLoading);
  protected readonly hasMore       = this.store.selectSignal(gallerySelectors.selectHasMore);
  protected readonly lightboxId    = this.store.selectSignal(gallerySelectors.selectLightboxId);
  protected readonly selectionMode = this.store.selectSignal(gallerySelectors.selectSelectionMode);
  protected readonly selectedIds   = this.store.selectSignal(gallerySelectors.selectSelectedIds);
  protected readonly allAssets     = this.store.selectSignal(gallerySelectors.selectAll);
  private readonly anchorId        = this.store.selectSignal(gallerySelectors.selectAnchorId);

  private readonly filterSources    = this.store.selectSignal(filtersSelectors.sources);
  private readonly filterQualityMin = this.store.selectSignal(filtersSelectors.qualityMin);
  private readonly filterTagIds     = this.store.selectSignal(filtersSelectors.tagIds);
  private readonly filterPersonId   = this.store.selectSignal(filtersSelectors.personId);
  private readonly filterSort       = this.store.selectSignal(filtersSelectors.sort);
  private readonly filterOrder      = this.store.selectSignal(filtersSelectors.order);

  protected readonly albums = this.store.selectSignal(collectionsSelectors.selectAlbums);

  protected readonly railOpen       = signal(false);
  protected readonly showExportDialog = signal(false);

  protected readonly selectedCount = computed((): number => this.selectedIds().length);

  protected readonly isEmpty = computed((): boolean =>
    !this.isLoading() && this.allAssets().length === 0
  );

  protected readonly exportFilters = computed((): ExportDialogFilters => ({
    sources:    this.filterSources(),
    qualityMin: this.filterQualityMin(),
    tagIds:     this.filterTagIds(),
    personId:   this.filterPersonId(),
    favourite:  true,
  }));

  constructor() {
    // Lock favourite filter for this view and load initial data
    this.store.dispatch(filtersActions.setFavourite({ favourite: true }));
    this.store.dispatch(collectionsActions.load());
    this.store.dispatch(personsActions.loadPersons());
    this.store.dispatch(galleryActions.requestPage());

    // Apply any extra filter params from URL (person, quality, etc.)
    const qp = this.route.snapshot.queryParamMap;
    const urlPersonId = Number(qp.get('person') ?? '') || 0;
    if (urlPersonId > 0) {
      this.store.dispatch(filtersActions.setPersonId({ personId: urlPersonId }));
    }

    // Sync extra filters back to URL
    effect((): void => {
      const params: Record<string, string> = {};
      const sources    = this.filterSources();
      const qualityMin = this.filterQualityMin();
      const tagIds     = this.filterTagIds();
      const personId   = this.filterPersonId();
      const sort       = this.filterSort();
      const order      = this.filterOrder();

      if (sources.length)  { params['sources']  = sources.join(','); }
      if (qualityMin > 0)  { params['q_min']    = String(qualityMin); }
      if (tagIds.length)   { params['tags']     = tagIds.join(','); }
      if (personId != null){ params['person']   = String(personId); }
      if (sort !== 'date') { params['sort']     = sort; }
      if (order !== 'desc'){ params['order']    = order; }

      void this.router.navigate([], {
        queryParams: params,
        replaceUrl: true,
        relativeTo: this.route,
      });
    });
  }

  protected onLoadMore(): void {
    if (!this.isLoading() && this.hasMore()) {
      this.store.dispatch(galleryActions.requestNextPage());
    }
  }

  protected onOpenAsset(event: { id: number; versionId: number | null }): void {
    this.store.dispatch(galleryActions.openLightbox({ id: event.id, versionId: event.versionId }));
  }

  protected toggleSelectionMode(): void {
    if (this.selectionMode()) {
      this.store.dispatch(galleryActions.disableSelectionMode());
    } else {
      this.store.dispatch(galleryActions.enableSelectionMode());
    }
  }

  protected onSelectAll(ids: number[]): void {
    this.store.dispatch(galleryActions.selectAll({ ids }));
  }

  protected onRangeSelect(targetId: number): void {
    const anchorId = this.anchorId();
    if (anchorId === null) {
      this.store.dispatch(galleryActions.toggleSelected({ id: targetId }));
      return;
    }
    const assets = this.allAssets();
    const anchorIndex = assets.findIndex((asset) => asset.id === anchorId);
    const targetIndex = assets.findIndex((asset) => asset.id === targetId);
    if (anchorIndex === -1 || targetIndex === -1) {
      this.store.dispatch(galleryActions.toggleSelected({ id: targetId }));
      return;
    }
    const start = Math.min(anchorIndex, targetIndex);
    const end   = Math.max(anchorIndex, targetIndex);
    const rangeIds = assets.slice(start, end + 1).map((asset) => asset.id);
    this.store.dispatch(galleryActions.selectRange({ ids: rangeIds }));
  }

  protected onBulkClose(): void {
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkTrash(): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(galleryActions.clearSelection());
    this.assetService.bulkTrash(ids)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.store.dispatch(galleryActions.reset()); });
  }
}
