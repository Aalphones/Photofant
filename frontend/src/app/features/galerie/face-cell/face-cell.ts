import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { FaceGalleryItemDto } from '@photofant/models';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-face-cell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './face-cell.html',
  styleUrl: './face-cell.scss',
  host: {
    '(click)': 'onCellClick($event)',
    '[class.face-cell--selected]': 'isSelected()',
    '[class.face-cell--selmode]': 'selectionMode()',
  },
})
export class FaceCell {
  readonly face          = input.required<FaceGalleryItemDto>();
  readonly cellSize      = input<number>(160);
  readonly isSelected    = input<boolean>(false);
  readonly selectionMode = input<boolean>(false);
  readonly isArmed       = input<boolean>(false);

  readonly openFace    = output<{ faceId: number; assetId: number | null; versionId: number | null }>();
  readonly toggleSelect = output<number>();
  readonly rangeSelect  = output<number>();

  protected readonly label = computed((): string => {
    const face = this.face();
    if (face.person_name) { return face.person_name; }
    if (face.age != null) { return `~${face.age} J.`; }
    return 'Gesicht';
  });

  protected readonly scorePercent = computed((): string => {
    const score = this.face().score;
    return score != null ? `${Math.round(score * 100)}%` : '';
  });

  protected readonly isStacked = computed((): boolean =>
    this.face().stack_size > 1
  );

  protected readonly stackTooltip = computed((): string =>
    `Stapel · ${this.face().stack_size} Versionen`
  );

  private emitOpenFace(): void {
    const face = this.face();
    this.openFace.emit({ faceId: face.id, assetId: face.asset_id, versionId: face.version_id });
  }

  protected onCellClick(event: MouseEvent): void {
    if (!this.isArmed() && (this.selectionMode() || event.ctrlKey || event.metaKey || event.shiftKey)) {
      event.stopPropagation();
      if (event.shiftKey) {
        this.rangeSelect.emit(this.face().id);
      } else {
        this.toggleSelect.emit(this.face().id);
      }
      return;
    }
    this.emitOpenFace();
  }

  protected onPickClick(event: MouseEvent): void {
    event.stopPropagation();
    this.toggleSelect.emit(this.face().id);
  }
}
