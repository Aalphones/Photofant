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
import { AssetService } from '@photofant/services';
import { Icon } from '@photofant/ui';
import { filtersActions, personsActions, personsSelectors } from '@photofant/store';
import { PersonCard } from './person-card/person-card';
import { MergeDialog } from './merge-dialog/merge-dialog';
import { SplitDialog } from './split-dialog/split-dialog';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonCard, MergeDialog, SplitDialog, Icon],
  templateUrl: './personen.html',
  styleUrl: './personen.scss',
})
export class Personen implements OnInit {
  private readonly store = inject(Store);
  private readonly router = inject(Router);
  private readonly assetService = inject(AssetService);

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly showMergeDialog = signal(false);
  protected readonly splitPerson = signal<PersonDto | null>(null);

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
    this.assetService.uploadFiles(event.files).subscribe();
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
