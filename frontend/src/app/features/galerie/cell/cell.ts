import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Store } from '@ngrx/store';
import { DENSITY_THUMB_SIZE } from '@photofant/models';
import type { AssetDto, Density } from '@photofant/models';
import { AssetService, VersionService } from '@photofant/services';
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
  private readonly versionService = inject(VersionService);
  private readonly store = inject(Store);

  readonly asset         = input.required<AssetDto>();
  readonly baseHeight    = input.required<number>();
  readonly density       = input.required<Density>();
  readonly isSelected    = input<boolean>(false);
  readonly selectionMode = input<boolean>(false);
  readonly isArmed       = input<boolean>(false);

  // P21-Stapel: versionId ist gesetzt, wenn diese Kachel ein Version-Pseudo-Eintrag ist —
  // Lightbox zeigt dann initial diese Version statt des Originals.
  readonly openAsset    = output<{ id: number; versionId: number | null }>();
  readonly batchBind    = output<number>();
  readonly rangeSelect  = output<number>();

  protected readonly aspectRatio = computed((): number => {
    const { width, height } = this.asset();
    return width && height ? width / height : 4 / 3;
  });

  protected readonly flexBasis = computed((): number =>
    this.aspectRatio() * this.baseHeight()
  );

  protected readonly thumbnailSrc = computed((): string => {
    const asset: AssetDto = this.asset();
    const size = DENSITY_THUMB_SIZE[this.density()];
    if (asset.kind === 'version' && asset.version_id != null) {
      return this.versionService.thumbnailUrl(asset.version_id, size);
    }
    return this.assetService.thumbnailUrl(asset.id, size, asset.content_hash);
  });

  protected readonly badgeLabel = computed((): string =>
    sourceLabel(this.asset().source)
  );

  protected readonly isStacked = computed((): boolean =>
    this.asset().stack_size > 1
  );

  protected readonly stackTooltip = computed((): string =>
    `Stapel · ${this.asset().stack_size} Versionen`
  );

  // Version-Pseudo-Einträge (kind === 'version') teilen ihre `asset.id` mit dem
  // Original — Auswählen/Favorisieren würde also das Original treffen, nicht die
  // Version selbst. Backend hat (noch) keinen eigenen Favourite/Delete-Endpunkt für
  // Version-Zeilen (siehe FINDINGS → Phase 5 / ADR-012), darum bleiben Pick + Favorit
  // für diese Einträge deaktiviert statt eine falsche Ziel-ID zu benutzen.
  protected readonly isVersionEntry = computed((): boolean =>
    this.asset().kind === 'version'
  );

  // Version-Pseudo-Einträge teilen asset.id mit dem Original (siehe isVersionEntry) —
  // hier zeigt die ID-Badge darum die eigene version_id, sonst wäre jede Kachel eines
  // Stapels von außen nicht unterscheidbar.
  protected readonly displayId = computed((): number => {
    const asset = this.asset();
    return asset.kind === 'version' && asset.version_id != null ? asset.version_id : asset.id;
  });

  private emitOpenAsset(): void {
    const asset: AssetDto = this.asset();
    this.openAsset.emit({ id: asset.id, versionId: asset.kind === 'version' ? asset.version_id : null });
  }

  protected onCellClick(event: MouseEvent): void {
    if (this.isArmed()) {
      event.stopPropagation();
      if (event.ctrlKey || event.shiftKey || event.metaKey) {
        this.batchBind.emit(this.asset().id);
      } else {
        this.emitOpenAsset();
      }
      return;
    }

    if (this.isVersionEntry()) {
      this.emitOpenAsset();
      return;
    }

    if (this.selectionMode() || event.ctrlKey || event.metaKey || event.shiftKey) {
      event.stopPropagation();
      if (event.shiftKey) {
        this.rangeSelect.emit(this.asset().id);
      } else {
        this.store.dispatch(galleryActions.toggleSelected({ id: this.asset().id }));
      }
      return;
    }

    this.emitOpenAsset();
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
