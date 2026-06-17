import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { filtersActions, filtersSelectors, galleryActions, gallerySelectors, tagsActions } from '@photofant/store';
import { GalerieGrid } from './grid/grid';
import { SubToolbar } from './sub-toolbar/sub-toolbar';
import { Lightbox } from './lightbox/lightbox';
import { FilterRail } from './filter-rail/filter-rail';
import { BulkBar, Icon } from '@photofant/ui';

@Component({
  selector: 'pf-galerie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SubToolbar, GalerieGrid, Lightbox, FilterRail, Icon, BulkBar],
  templateUrl: './galerie.html',
  styleUrl: './galerie.scss',
})
export class Galerie {
  private readonly store  = inject(Store);
  private readonly router = inject(Router);
  private readonly route  = inject(ActivatedRoute);

  protected readonly groups        = this.store.selectSignal(gallerySelectors.selectGroups);
  protected readonly density       = this.store.selectSignal(filtersSelectors.density);
  protected readonly isLoading     = this.store.selectSignal(gallerySelectors.selectIsLoading);
  protected readonly hasMore       = this.store.selectSignal(gallerySelectors.selectHasMore);
  protected readonly lightboxId    = this.store.selectSignal(gallerySelectors.selectLightboxId);
  protected readonly selectionMode = this.store.selectSignal(gallerySelectors.selectSelectionMode);
  protected readonly selectedIds   = this.store.selectSignal(gallerySelectors.selectSelectedIds);

  private readonly filterSources    = this.store.selectSignal(filtersSelectors.sources);
  private readonly filterQualityMin = this.store.selectSignal(filtersSelectors.qualityMin);
  private readonly filterTagIds     = this.store.selectSignal(filtersSelectors.tagIds);
  private readonly filterSort       = this.store.selectSignal(filtersSelectors.sort);
  private readonly filterOrder      = this.store.selectSignal(filtersSelectors.order);

  protected readonly railOpen = signal(false);

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

    if (urlSources.length) this.store.dispatch(filtersActions.setSources({ sources: urlSources }));
    if (urlQMin > 0)       this.store.dispatch(filtersActions.setQualityMin({ qualityMin: urlQMin }));
    if (urlTagIds.length)  this.store.dispatch(filtersActions.setTagIds({ tagIds: urlTagIds }));

    this.store.dispatch(galleryActions.requestPage());

    // store → URL: keep query params in sync
    effect((): void => {
      const params: Record<string, string> = {};
      const sources    = this.filterSources();
      const qualityMin = this.filterQualityMin();
      const tagIds     = this.filterTagIds();
      const sort       = this.filterSort();
      const order      = this.filterOrder();

      if (sources.length)    params['sources'] = sources.join(',');
      if (qualityMin > 0)    params['q_min']   = String(qualityMin);
      if (tagIds.length)     params['tags']     = tagIds.join(',');
      if (sort !== 'date')   params['sort']     = sort;
      if (order !== 'desc')  params['order']    = order;

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
}
