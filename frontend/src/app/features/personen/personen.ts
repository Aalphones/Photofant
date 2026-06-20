import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
} from '@angular/core';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import type { PersonDto } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { filtersActions, personsActions, personsSelectors } from '@photofant/store';
import { PersonCard } from './person-card/person-card';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonCard],
  templateUrl: './personen.html',
  styleUrl: './personen.scss',
})
export class Personen implements OnInit {
  private readonly store = inject(Store);
  private readonly router = inject(Router);
  private readonly assetService = inject(AssetService);

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(personsSelectors.selectIsLoading);

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
}
