import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { filtersSelectors, galleryActions, gallerySelectors } from '@photofant/store';
import { GalerieGrid } from './grid/grid';
import { SubToolbar } from './sub-toolbar/sub-toolbar';
import { Lightbox } from './lightbox/lightbox';

@Component({
  selector: 'pf-galerie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SubToolbar, GalerieGrid, Lightbox],
  templateUrl: './galerie.html',
  styleUrl: './galerie.scss',
})
export class Galerie {
  private readonly store = inject(Store);

  protected readonly groups      = this.store.selectSignal(gallerySelectors.selectGroups);
  protected readonly density     = this.store.selectSignal(filtersSelectors.density);
  protected readonly isLoading   = this.store.selectSignal(gallerySelectors.selectIsLoading);
  protected readonly hasMore     = this.store.selectSignal(gallerySelectors.selectHasMore);
  protected readonly lightboxId  = this.store.selectSignal(gallerySelectors.selectLightboxId);

  constructor() {
    this.store.dispatch(galleryActions.requestPage());
  }

  protected onLoadMore(): void {
    if (!this.isLoading() && this.hasMore()) {
      this.store.dispatch(galleryActions.requestNextPage());
    }
  }

  protected onOpenAsset(id: number): void {
    this.store.dispatch(galleryActions.openLightbox({ id }));
  }
}
