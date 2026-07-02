import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { Icon } from '@photofant/ui';
import type { PersonDto } from '@photofant/models';

@Component({
  selector: 'pf-delete-person-dialog',
  imports: [Icon],
  templateUrl: './delete-person-dialog.html',
  styleUrl: './delete-person-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DeletePersonDialog {
  readonly person = input.required<PersonDto>();
  readonly close = output<void>();
  readonly confirmDelete = output<number>();

  protected onConfirm(): void {
    this.confirmDelete.emit(this.person().id);
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('delete-person-dialog__backdrop')) {
      this.close.emit();
    }
  }

  protected portraitUrl(person: PersonDto): string | null {
    return person.portrait_face_id != null
      ? `/api/faces/${person.portrait_face_id}/thumbnail`
      : null;
  }
}
