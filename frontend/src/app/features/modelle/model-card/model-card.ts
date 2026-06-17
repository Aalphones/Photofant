import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Icon } from '@photofant/ui';
import { ROLE_META, STATUS_META, formatModelSize } from '@photofant/models';
import type { ModelView } from '@photofant/models';

@Component({
  selector: 'pf-model-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './model-card.html',
  styleUrl: './model-card.scss',
  host: { class: 'model-card-host' },
})
export class ModelCard {
  readonly model = input.required<ModelView>();
  readonly isPendingDownload = input<boolean>(false);
  readonly open = output<ModelView>();

  protected readonly roleMeta = computed(() => ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role });
  protected readonly statusMeta = computed(() => STATUS_META[this.model().status] ?? { label: this.model().status, dot: true });

  protected formatSize(bytes: number | null): string {
    return formatModelSize(bytes);
  }

  protected handleClick(): void {
    this.open.emit(this.model());
  }
}
