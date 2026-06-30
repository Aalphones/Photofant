import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { VersionGalleryItemDto } from '@photofant/models';

@Component({
  selector: 'pf-version-cell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './version-cell.html',
  styleUrl: './version-cell.scss',
  host: {
    '[class.version-cell--armed]': 'isArmed()',
    '(click)': 'onCellClick()',
  },
})
export class VersionCell {
  readonly version  = input.required<VersionGalleryItemDto>();
  readonly isArmed  = input<boolean>(false);

  readonly openVersion = output<number>();
  readonly bindVersion = output<number>();

  protected readonly aspectRatio = computed((): number => {
    const { width, height } = this.version();
    return width && height ? width / height : 4 / 3;
  });

  protected readonly typeLabel = computed((): string => {
    const type = this.version().type;
    if (!type) { return 'Edit'; }
    if (type === 'crop') { return 'Zuschnitt'; }
    if (type === 'resize') { return 'Skaliert'; }
    if (type === 'convert') { return 'Konvertiert'; }
    return type;
  });

  protected readonly formattedDate = computed((): string => {
    const dateStr = this.version().created_at;
    if (!dateStr) { return ''; }
    return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(dateStr));
  });

  protected onCellClick(): void {
    if (this.isArmed()) {
      this.bindVersion.emit(this.version().id);
    } else {
      this.openVersion.emit(this.version().id);
    }
  }
}
