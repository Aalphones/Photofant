import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Store } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';
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
    '[style.height.px]':     'baseHeight()',
    '[style.flex-grow]':     'aspectRatio()',
    '[style.flex-basis.px]': 'flexBasis()',
    '(click)':               'onCellClick()',
  },
})
export class GalerieCell {
  private readonly assetService = inject(AssetService);
  private readonly store = inject(Store);

  readonly asset      = input.required<AssetDto>();
  readonly baseHeight = input.required<number>();

  readonly openAsset = output<number>();

  protected readonly aspectRatio = computed((): number => {
    const { width, height } = this.asset();
    return width && height ? width / height : 4 / 3;
  });

  protected readonly flexBasis = computed((): number =>
    this.aspectRatio() * this.baseHeight()
  );

  protected readonly thumbnailSrc = computed((): string =>
    this.assetService.thumbnailUrl(this.asset().id, 256)
  );

  protected readonly badgeLabel = computed((): string =>
    sourceLabel(this.asset().source)
  );

  protected readonly hasVersions = computed((): boolean =>
    this.asset().version_count > 1
  );

  protected onCellClick(): void {
    this.openAsset.emit(this.asset().id);
  }

  protected onFavClick(event: MouseEvent): void {
    event.stopPropagation();
    const asset: AssetDto = this.asset();
    this.store.dispatch(galleryActions.toggleFavourite({ id: asset.id, value: !asset.favourite }));
  }
}
