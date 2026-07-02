import { ChangeDetectionStrategy, Component, computed, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-create-person-dialog',
  imports: [Icon],
  templateUrl: './create-person-dialog.html',
  styleUrl: './create-person-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CreatePersonDialog {
  readonly close = output<void>();
  readonly confirm = output<string>();

  protected readonly nameValue = signal('');

  protected readonly canConfirm = computed((): boolean => this.nameValue().trim().length > 0);

  protected onConfirm(): void {
    const name = this.nameValue().trim();
    if (!name) {
      return;
    }
    this.confirm.emit(name);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && this.canConfirm()) {
      this.onConfirm();
    }
    if (event.key === 'Escape') {
      this.close.emit();
    }
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('create-person-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
