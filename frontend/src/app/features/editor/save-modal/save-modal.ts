import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';

export type SaveMode = 'overwrite' | 'new_copy';

@Component({
  selector: 'pf-save-modal',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './save-modal.html',
  styleUrl: './save-modal.scss',
})
export class SaveModal {
  readonly stepCount = input.required<number>();
  readonly cancel = output<void>();
  readonly save = output<SaveMode>();

  protected readonly saveMode = signal<SaveMode>('overwrite');

  protected setSaveMode(mode: SaveMode): void {
    this.saveMode.set(mode);
  }

  protected onSave(): void {
    this.save.emit(this.saveMode());
  }

  protected onCancel(): void {
    this.cancel.emit();
  }
}
