import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import type { PersonDto } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { Icon } from '@photofant/ui';
import { filtersActions, personsActions, personsSelectors } from '@photofant/store';
import { PersonCard } from './person-card/person-card';
import { MergeDialog } from './merge-dialog/merge-dialog';
import { SplitDialog } from './split-dialog/split-dialog';
import { DupeCheckDialog } from './dupe-check-dialog/dupe-check-dialog';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonCard, MergeDialog, SplitDialog, DupeCheckDialog, Icon],
  templateUrl: './personen.html',
  styleUrl: './personen.scss',
})
export class Personen implements OnInit {
  private readonly store = inject(Store);
  private readonly router = inject(Router);
  private readonly personService = inject(PersonService);

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly showMergeDialog = signal(false);
  protected readonly splitPerson = signal<PersonDto | null>(null);
  protected readonly dupeCheckPerson = signal<PersonDto | null>(null);

  ngOnInit(): void {
    this.store.dispatch(personsActions.loadPersons());
  }

  protected onSelect(person: PersonDto): void {
    this.store.dispatch(filtersActions.setPersonId({ personId: person.id }));
    void this.router.navigate(['/galerie']);
  }

  protected onRename(event: { id: number; name: string }): void {
    this.store.dispatch(personsActions.renamePerson(event));
  }

  protected onImportFiles(event: { personId: number; files: File[] }): void {
    this.personService.importToPersonFolder(event.personId, event.files).subscribe();
  }

  protected onDupeCheck(person: PersonDto): void {
    this.dupeCheckPerson.set(person);
  }

  protected onRevealInFileBrowser(person: PersonDto): void {
    this.personService.revealPersonFolder(person.id).subscribe();
  }

  protected onMerge(event: { fromId: number; intoId: number }): void {
    this.store.dispatch(personsActions.mergePersons(event));
    this.showMergeDialog.set(false);
  }

  protected onSplitClick(person: PersonDto): void {
    this.splitPerson.set(person);
  }

  protected onSplit(event: { personId: number; faceIds: number[] }): void {
    this.store.dispatch(personsActions.splitPerson(event));
    this.splitPerson.set(null);
  }
}
