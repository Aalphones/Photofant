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
    '(click)': 'onCellClick()',
  },
})
export class FaceCell {
  readonly face     = input.required<FaceGalleryItemDto>();
  readonly cellSize = input<number>(160);

  readonly openFace = output<{ faceId: number; assetId: number | null }>();

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

  protected onCellClick(): void {
    const face = this.face();
    this.openFace.emit({ faceId: face.id, assetId: face.asset_id });
  }
}
