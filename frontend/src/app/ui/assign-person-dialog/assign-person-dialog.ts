import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { Icon } from '../icon/icon';
import type { PersonDto } from '@photofant/models';

@Component({
  selector: 'pf-assign-person-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './assign-person-dialog.html',
  styleUrl: './assign-person-dialog.scss',
})
export class AssignPersonDialog {
  readonly persons = input.required<PersonDto[]>();
  readonly close = output<void>();
  readonly confirm = output<number>();

  protected readonly namedPersons = computed((): PersonDto[] =>
    this.persons().filter((person: PersonDto) => !person.is_unknown)
  );

  protected pick(personId: number): void {
    this.confirm.emit(personId);
  }

  protected portraitUrl(person: PersonDto): string | null {
    return person.portrait_face_id != null
      ? `/api/faces/${person.portrait_face_id}/thumbnail`
      : null;
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('assign-person-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
