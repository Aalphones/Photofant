import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Store } from '@ngrx/store';
import { DENSITY_THUMB_SIZE } from '@photofant/models';
import type { AssetDto, Density } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { galleryActions } from '@photofant/store';
import { Icon } from '@photofant/ui';

function sourceLabel(source: string | null): string {
  if (source === 'flux') return 'FLUX';
  if (source === 'sdxl') return 'SDXL';
  return '';
}

@Component({
  selector: 'pf-galerie-cell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './cell.html',
  styleUrl: './cell.scss',
  host: {
    '[style.height.px]':          'baseHeight()',
    '[style.flex-grow]':          'aspectRatio()',
    '[style.flex-basis.px]':      'flexBasis()',
    '[class.cell--selected]':     'isSelected()',
    '[class.cell--selmode]':      'selectionMode()',
    '[class.cell--armed]':        'isArmed()',
    '(click)':                    'onCellClick($event)',
  },
})
export class GalerieCell {
  private readonly assetService = inject(AssetService);
  private readonly store = inject(Store);

  readonly asset         = input.required<AssetDto>();
  readonly baseHeight    = input.required<number>();
  readonly density       = input.required<Density>();
  readonly isSelected    = input<boolean>(false);
  readonly selectionMode = input<boolean>(false);
  readonly isArmed       = input<boolean>(false);

  readonly openAsset  = output<number>();
  readonly batchBind  = output<number>();

  protected readonly aspectRatio = computed((): number => {
    const { width, height } = this.asset();
    return width && height ? width / height : 4 / 3;
  });

  protected readonly flexBasis = computed((): number =>
    this.aspectRatio() * this.baseHeight()
  );

  protected readonly thumbnailSrc = computed((): string => {
    const asset: AssetDto = this.asset();
    return this.assetService.thumbnailUrl(asset.id, DENSITY_THUMB_SIZE[this.density()], asset.content_hash);
  });

  protected readonly badgeLabel = computed((): string =>
    sourceLabel(this.asset().source)
  );

  protected readonly hasVersions = computed((): boolean =>
    this.asset().version_count > 1
  );

  protected onCellClick(event: MouseEvent): void {
    if (this.isArmed()) {
      event.stopPropagation();
      if (event.ctrlKey || event.shiftKey || event.metaKey) {
        this.batchBind.emit(this.asset().id);
      } else {
        this.openAsset.emit(this.asset().id);
      }
    } else if (this.selectionMode() || event.ctrlKey || event.metaKey) {
      event.stopPropagation();
      this.store.dispatch(galleryActions.toggleSelected({ id: this.asset().id }));
    } else {
      this.openAsset.emit(this.asset().id);
    }
  }

  protected onPickClick(event: MouseEvent): void {
    event.stopPropagation();
    this.store.dispatch(galleryActions.toggleSelected({ id: this.asset().id }));
  }

  protected onFavClick(event: MouseEvent): void {
    event.stopPropagation();
    const asset: AssetDto = this.asset();
    this.store.dispatch(galleryActions.toggleFavourite({ id: asset.id, value: !asset.favourite }));
  }
}
