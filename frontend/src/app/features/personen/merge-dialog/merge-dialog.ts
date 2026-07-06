import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { Icon } from '@photofant/ui';
import type { PersonDto } from '@photofant/models';

@Component({
  selector: 'pf-merge-dialog',
  imports: [Icon],
  templateUrl: './merge-dialog.html',
  styleUrl: './merge-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MergeDialog implements OnInit {
  readonly persons = input.required<PersonDto[]>();
  readonly preselectedFrom = input<PersonDto | null>(null);
  readonly close = output<void>();
  readonly merge = output<{ fromId: number; intoId: number }>();

  protected readonly fromPerson = signal<PersonDto | null>(null);
  protected readonly intoPerson = signal<PersonDto | null>(null);
  protected readonly step = signal<'select-from' | 'select-into' | 'confirm'>('select-from');
  protected readonly searchQuery = signal('');

  // Signal-Inputs sind erst nach dem Konstruktor gebunden — die Vorauswahl darf
  // deshalb nicht im Field-Initializer gelesen werden, sonst ist sie immer null.
  ngOnInit(): void {
    const preselected = this.preselectedFrom();
    if (preselected) {
      this.fromPerson.set(preselected);
      this.step.set('select-into');
    }
  }

  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.searchQuery().toLowerCase();
    const from = this.fromPerson();
    const isTargetSearch = this.step() === 'select-into';
    return this.persons().filter((person: PersonDto) => {
      if (person.is_unknown) return false;
      // Ziel einer Zusammenführung ist fast immer eine benannte Person — unbenannte
      // Cluster (name=null) würden nur als „—" die Zielliste zumüllen.
      if (isTargetSearch && !person.name) return false;
      if (from && person.id === from.id) return false;
      if (!query) return true;
      return (person.name ?? '').toLowerCase().includes(query);
    });
  });

  protected selectFrom(person: PersonDto): void {
    this.fromPerson.set(person);
    this.step.set('select-into');
    this.searchQuery.set('');
  }

  protected selectInto(person: PersonDto): void {
    this.intoPerson.set(person);
    this.step.set('confirm');
  }

  protected onConfirm(): void {
    const from = this.fromPerson();
    const into = this.intoPerson();
    if (from && into) {
      this.merge.emit({ fromId: from.id, intoId: into.id });
    }
  }

  protected onBack(): void {
    const current = this.step();
    if (current === 'confirm') {
      this.step.set('select-into');
      this.intoPerson.set(null);
    } else if (current === 'select-into') {
      this.step.set('select-from');
      this.fromPerson.set(null);
    }
    this.searchQuery.set('');
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('merge-dialog__backdrop')) {
      this.close.emit();
    }
  }

  protected portraitUrl(person: PersonDto): string | null {
    return person.portrait_face_id != null
      ? `/api/faces/${person.portrait_face_id}/thumbnail`
      : null;
  }
}
