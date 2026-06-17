import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { Icon } from '../icon/icon';

@Component({
  selector: 'pf-bulk-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './bulk-bar.html',
  styleUrl: './bulk-bar.scss',
})
export class BulkBar {
  readonly count = input.required<number>();

  readonly close = output<void>();
  readonly tagAction = output<{ add: string[]; remove: number[] }>();

  protected readonly showTagInput = signal(false);
  protected readonly tagInput = signal('');

  protected readonly countLabel = computed((): string => {
    const n = this.count();
    return n === 1 ? '1 Bild ausgewählt' : `${n} Bilder ausgewählt`;
  });

  protected openTagInput(): void {
    this.showTagInput.set(true);
  }

  protected applyTags(): void {
    const raw = this.tagInput().trim();
    if (raw) {
      const tags = raw.split(',').map((tag: string) => tag.trim()).filter(Boolean);
      this.tagAction.emit({ add: tags, remove: [] });
    }
    this.tagInput.set('');
    this.showTagInput.set(false);
  }

  protected onTagKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.applyTags();
    } else if (event.key === 'Escape') {
      this.showTagInput.set(false);
      this.tagInput.set('');
    }
  }

  protected onClose(): void {
    this.close.emit();
  }
}
