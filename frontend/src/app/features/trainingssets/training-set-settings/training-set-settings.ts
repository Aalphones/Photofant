import { ChangeDetectionStrategy, Component, effect, inject, input, output, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { CollectionDetail, TrainingSetSettings } from '@photofant/models';
import { collectionsActions } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-training-set-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './training-set-settings.html',
  styleUrl: './training-set-settings.scss',
})
export class TrainingSetSettingsPanel {
  private readonly store = inject(Store);

  readonly collection = input.required<CollectionDetail>();
  readonly close = output<void>();

  protected readonly triggerWordDraft = signal('');
  protected readonly prefixDraft = signal('');
  protected readonly suffixDraft = signal('');
  protected readonly splitRatioDraft = signal(0.9);

  constructor() {
    // Entwurf mit Server-Stand synchron halten, wenn ein anderes Set geöffnet wird.
    effect((): void => {
      const settings: TrainingSetSettings | null = this.collection().settings;
      this.triggerWordDraft.set(settings?.trigger_word ?? '');
      this.prefixDraft.set(settings?.prefix ?? '');
      this.suffixDraft.set(settings?.suffix ?? '');
      this.splitRatioDraft.set(settings?.split_ratio ?? 0.9);
    });
  }

  protected save(): void {
    this.store.dispatch(collectionsActions.update({
      id: this.collection().id,
      request: {
        settings: {
          trigger_word: this.triggerWordDraft().trim() || null,
          prefix: this.prefixDraft().trim() || null,
          suffix: this.suffixDraft().trim() || null,
          split_ratio: this.splitRatioDraft(),
        },
      },
    }));
  }

  protected onClose(): void {
    this.close.emit();
  }
}
