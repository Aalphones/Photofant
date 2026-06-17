import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Icon } from '@photofant/ui';
import { ERROR_CODE_MESSAGES, ROLE_META } from '@photofant/models';
import type { ModelBindError, ModelView } from '@photofant/models';

@Component({
  selector: 'pf-bind-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './bind-dialog.html',
  styleUrl: './bind-dialog.scss',
})
export class BindDialog {
  readonly model = input.required<ModelView>();
  readonly bindError = input<ModelBindError | null>(null);
  readonly isPending = input<boolean>(false);
  readonly confirm = output<{ model: ModelView; path: string }>();
  readonly cancel = output<void>();

  protected readonly path = signal<string>('');
  protected readonly roleMeta = computed(() =>
    ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role }
  );
  protected readonly canConfirm = computed(() =>
    this.path().trim().length > 0 && !this.isPending()
  );
  protected readonly errorMessage = computed(() => {
    const error = this.bindError();
    if (error === null || error.manifestId !== this.model().id) { return null; }
    return ERROR_CODE_MESSAGES[error.code] ?? error.message;
  });

  protected handleConfirm(): void {
    if (!this.canConfirm()) { return; }
    this.confirm.emit({ model: this.model(), path: this.path().trim() });
  }

  protected handleCancel(): void { this.cancel.emit(); }
  protected handleScrimClick(): void { this.cancel.emit(); }
}
