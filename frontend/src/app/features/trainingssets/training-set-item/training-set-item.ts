import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import type { TrainingSetItem, TrainingSetItemTag } from '@photofant/models';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-training-set-item',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './training-set-item.html',
  styleUrl: './training-set-item.scss',
})
export class TrainingSetItemCell {
  readonly item = input.required<TrainingSetItem>();
  readonly thumbnailUrl = input.required<string>();

  readonly captionSaved = output<string | null>();
  readonly tagAdded = output<string>();
  readonly tagRemoved = output<number>();
  readonly removed = output<void>();

  protected readonly editingCaption = signal(false);
  protected readonly captionDraft = signal('');
  protected readonly newTagInput = signal('');

  protected readonly dims = computed((): string => {
    const { width, height } = this.item();
    return width != null && height != null ? `${width}×${height}` : '';
  });

  protected startEditCaption(): void {
    this.captionDraft.set(this.item().effective_caption ?? '');
    this.editingCaption.set(true);
  }

  protected saveCaption(): void {
    const draft = this.captionDraft().trim();
    this.editingCaption.set(false);
    if (draft === (this.item().effective_caption ?? '')) { return; }
    this.captionSaved.emit(draft.length > 0 ? draft : null);
  }

  protected cancelEditCaption(): void {
    this.editingCaption.set(false);
  }

  protected addTag(): void {
    const name = this.newTagInput().trim();
    if (!name) { return; }
    this.tagAdded.emit(name);
    this.newTagInput.set('');
  }

  protected onTagKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.addTag(); }
  }

  protected tagLabel(tag: TrainingSetItemTag): string {
    return tag.name.replaceAll('_', ' ');
  }
}
