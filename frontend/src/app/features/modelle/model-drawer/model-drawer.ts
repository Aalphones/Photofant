import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Icon } from '@photofant/ui';
import { ROLE_META, STATUS_META, formatModelSize } from '@photofant/models';
import type { ModelView } from '@photofant/models';

@Component({
  selector: 'pf-model-drawer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './model-drawer.html',
  styleUrl: './model-drawer.scss',
})
export class ModelDrawer {
  readonly model = input.required<ModelView>();
  readonly close = output<void>();
  readonly download = output<ModelView>();
  readonly bind = output<ModelView>();
  readonly deleteModel = output<ModelView>();

  protected readonly roleMeta = computed(() =>
    ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role }
  );
  protected readonly statusMeta = computed(() =>
    STATUS_META[this.model().status] ?? { label: this.model().status, dot: true }
  );
  protected readonly isInstalled = computed(() =>
    this.model().status === 'active' || this.model().status === 'inplace'
  );
  protected readonly isUnavailable = computed(() =>
    this.model().status === 'missing' || this.model().status === 'available'
  );

  protected formatSize(bytes: number | null): string {
    return formatModelSize(bytes);
  }

  protected handleClose(): void { this.close.emit(); }
  protected handleDownload(): void { this.download.emit(this.model()); }
  protected handleBind(): void { this.bind.emit(this.model()); }
  protected handleDelete(): void { this.deleteModel.emit(this.model()); }
}
