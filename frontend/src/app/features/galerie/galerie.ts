import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { collectionsActions, collectionsSelectors, filtersActions, filtersSelectors, galleryActions, gallerySelectors, presetsActions, presetsSelectors, reviewActions, tagsActions } from '@photofant/store';
import { ClassifyService } from '@photofant/services';
import { GalerieGrid } from './grid/grid';
import { SubToolbar } from './sub-toolbar/sub-toolbar';
import { Lightbox } from './lightbox/lightbox';
import { FilterRail } from './filter-rail/filter-rail';
import { BulkBar, Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';

@Component({
  selector: 'pf-galerie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SubToolbar, GalerieGrid, Lightbox, FilterRail, Icon, BulkBar, RerunDialog, RouterLink],
  templateUrl: './galerie.html',
  styleUrl: './galerie.scss',
})
export class Galerie {
  private readonly store           = inject(Store);
  private readonly router          = inject(Router);
  private readonly route           = inject(ActivatedRoute);
  private readonly classifyService = inject(ClassifyService);

  protected readonly groups        = this.store.selectSignal(gallerySelectors.selectGroups);
  protected readonly density       = this.store.selectSignal(filtersSelectors.density);
  protected readonly isLoading     = this.store.selectSignal(gallerySelectors.selectIsLoading);
  protected readonly hasMore       = this.store.selectSignal(gallerySelectors.selectHasMore);
  protected readonly lightboxId    = this.store.selectSignal(gallerySelectors.selectLightboxId);
  protected readonly selectionMode = this.store.selectSignal(gallerySelectors.selectSelectionMode);
  protected readonly selectedIds   = this.store.selectSignal(gallerySelectors.selectSelectedIds);

  private readonly filterSources      = this.store.selectSignal(filtersSelectors.sources);
  private readonly filterQualityMin   = this.store.selectSignal(filtersSelectors.qualityMin);
  private readonly filterTagIds       = this.store.selectSignal(filtersSelectors.tagIds);
  private readonly filterCollectionId = this.store.selectSignal(filtersSelectors.collectionId);
  private readonly filterSort         = this.store.selectSignal(filtersSelectors.sort);
  private readonly filterOrder        = this.store.selectSignal(filtersSelectors.order);

  protected readonly albums = this.store.selectSignal(collectionsSelectors.selectAll);

  protected readonly railOpen = signal(false);
  protected readonly showBulkRerunDialog = signal(false);
  protected readonly bulkRerunPresets = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly dupeScanToast = signal<string | null>(null);
  private dupeScanToastTimer: ReturnType<typeof setTimeout> | null = null;

  protected readonly isEmpty = computed((): boolean =>
    !this.isLoading() && this.groups().length === 0
  );

  protected readonly selectedCount = computed((): number => this.selectedIds().length);

  constructor() {
    // URL → store: apply filter params from URL on load
    const qp = this.route.snapshot.queryParamMap;
    const urlSources = (qp.get('sources') ?? '').split(',').filter(Boolean);
    const urlQMin    = parseFloat(qp.get('q_min') ?? '0') || 0;
    const urlTagIds  = (qp.get('tags') ?? '').split(',').map(Number).filter((n: number) => n > 0);
    const urlCollection = Number(qp.get('collection') ?? '') || 0;

    if (urlSources.length) this.store.dispatch(filtersActions.setSources({ sources: urlSources }));
    if (urlQMin > 0)       this.store.dispatch(filtersActions.setQualityMin({ qualityMin: urlQMin }));
    if (urlTagIds.length)  this.store.dispatch(filtersActions.setTagIds({ tagIds: urlTagIds }));
    if (urlCollection > 0) this.store.dispatch(filtersActions.setCollectionId({ collectionId: urlCollection }));

    this.store.dispatch(collectionsActions.load());
    this.store.dispatch(galleryActions.requestPage());

    // store → URL: keep query params in sync
    effect((): void => {
      const params: Record<string, string> = {};
      const sources      = this.filterSources();
      const qualityMin   = this.filterQualityMin();
      const tagIds       = this.filterTagIds();
      const collectionId = this.filterCollectionId();
      const sort         = this.filterSort();
      const order        = this.filterOrder();

      if (sources.length)     params['sources']    = sources.join(',');
      if (qualityMin > 0)     params['q_min']      = String(qualityMin);
      if (tagIds.length)      params['tags']       = tagIds.join(',');
      if (collectionId != null) params['collection'] = String(collectionId);
      if (sort !== 'date')    params['sort']       = sort;
      if (order !== 'desc')   params['order']      = order;

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

  protected onOpenAsset(id: number): void {
    this.store.dispatch(galleryActions.openLightbox({ id }));
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

  protected onBulkClose(): void {
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkTag(payload: { add: string[]; remove: number[] }): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(tagsActions.bulkTag({
      asset_ids: ids,
      add: payload.add,
      remove: payload.remove,
    }));
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onAddToAlbum(collectionId: number): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(collectionsActions.addItems({ collectionId, assetIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkRerunOpen(): void {
    this.store.dispatch(presetsActions.loadPresets());
    this.showBulkRerunDialog.set(true);
  }

  protected onBulkRerunConfirm(payload: RerunPayload): void {
    this.showBulkRerunDialog.set(false);
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.classifyService.rerun({
      asset_ids: ids,
      steps: payload.steps,
      ...(payload.captionPresetId != null ? { caption_preset_id: payload.captionPresetId } : {}),
    }).subscribe();
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkRerunCancel(): void {
    this.showBulkRerunDialog.set(false);
  }

  protected onBulkDupeScan(): void {
    const ids = this.selectedIds();
    if (ids.length < 2) { return; }
    this.store.dispatch(reviewActions.triggerDupeScanSelection({ assetIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
    if (this.dupeScanToastTimer != null) { clearTimeout(this.dupeScanToastTimer); }
    this.dupeScanToast.set(`Duplikat-Scan für ${ids.length} Bilder gestartet`);
    this.dupeScanToastTimer = setTimeout(() => { this.dupeScanToast.set(null); }, 4000);
  }
}
