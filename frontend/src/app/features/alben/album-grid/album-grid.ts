import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Store } from '@ngrx/store';
import { BASE_HEIGHTS } from '@photofant/models';
import type { AssetDto } from '@photofant/models';
import { filtersSelectors } from '@photofant/store';
import { GalerieCell } from '../../galerie/cell/cell';

@Component({
  selector: 'pf-album-grid',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GalerieCell],
  templateUrl: './album-grid.html',
  styleUrl: './album-grid.scss',
})
export class AlbumGrid {
  private readonly store = inject(Store);

  readonly assets = input.required<AssetDto[]>();

  readonly openAsset = output<number>();

  protected readonly density = this.store.selectSignal(filtersSelectors.density);

  protected readonly baseHeight = computed((): number => BASE_HEIGHTS[this.density()]);

  protected onOpen(id: number): void {
    this.openAsset.emit(id);
  }
}
