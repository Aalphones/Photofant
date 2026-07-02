import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import type { Density, PersonDto } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { Icon } from '@photofant/ui';
import { filtersActions, personsActions, personsSelectors } from '@photofant/store';
import { PersonCard } from './person-card/person-card';
import { MergeDialog } from './merge-dialog/merge-dialog';
import { SplitDialog } from './split-dialog/split-dialog';
import { DupeCheckDialog } from './dupe-check-dialog/dupe-check-dialog';
import { CreatePersonDialog } from './create-person-dialog/create-person-dialog';
import { DeletePersonDialog } from './delete-person-dialog/delete-person-dialog';
import { AlphabetRail } from './alphabet-rail/alphabet-rail';
import { groupColor } from './group-color.util';

type PersonSortKey = 'group' | 'created' | 'name' | 'unnamed' | 'count';
type PersonViewMode = 'single' | 'grid4' | 'face';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PersonCard, MergeDialog, SplitDialog, DupeCheckDialog, CreatePersonDialog, DeletePersonDialog, AlphabetRail, Icon],
  templateUrl: './personen.html',
  styleUrl: './personen.scss',
})
export class Personen implements OnInit {
  private readonly store = inject(Store);
  private readonly router = inject(Router);
  private readonly personService = inject(PersonService);

  protected readonly groupColor = groupColor;

  private readonly SORT_CYCLE: PersonSortKey[] = ['group', 'created', 'name', 'unnamed', 'count'];
  private readonly SORT_LABELS: Record<PersonSortKey, string> = {
    group: 'Gruppe', created: 'Erstellungsdatum', name: 'Name',
    unnamed: 'Unbenannt zuerst', count: 'Anzahl Fotos',
  };

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly isClustering = this.store.selectSignal(personsSelectors.selectIsClustering);
  protected readonly showMergeDialog = signal(false);
  protected readonly showCreateDialog = signal(false);
  protected readonly splitPerson = signal<PersonDto | null>(null);
  protected readonly dupeCheckPerson = signal<PersonDto | null>(null);
  protected readonly deletePersonTarget = signal<PersonDto | null>(null);

  protected readonly searchQuery = signal('');
  protected readonly sortKey = signal<PersonSortKey>('group');
  protected readonly groupFilter = signal<Set<string>>(new Set());
  protected readonly viewMode = signal<PersonViewMode>('face');
  protected readonly cardSize = signal<Density>('md');

  protected readonly SIZES: { key: Density; iconSize: number }[] = [
    { key: 'sm', iconSize: 13 },
    { key: 'md', iconSize: 15 },
    { key: 'lg', iconSize: 17 },
  ];

  private readonly CARD_WIDTHS: Record<Density, number> = { sm: 150, md: 200, lg: 270 };

  protected readonly cardWidth = computed((): number => this.CARD_WIDTHS[this.cardSize()]);

  protected readonly availableGroups = computed((): string[] => {
    const names = new Set<string>();
    for (const person of this.persons()) {
      if (person.group_name) { names.add(person.group_name); }
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  });

  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.searchQuery().trim().toLowerCase();
    const groups = this.groupFilter();
    return this.persons().filter((person: PersonDto) => {
      if (query) {
        const label = (person.is_unknown ? 'unbekannt' : (person.name ?? '')).toLowerCase();
        if (!label.includes(query)) { return false; }
      }
      if (groups.size > 0) {
        if (!person.group_name || !groups.has(person.group_name)) { return false; }
      }
      return true;
    });
  });

  protected readonly sortedPersons = computed((): PersonDto[] => {
    const list = [...this.filteredPersons()];
    if (this.sortKey() === 'name') {
      return list.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
    }
    if (this.sortKey() === 'created') {
      return list.sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bTime - aTime; // neueste zuerst, NULL (=0) landet am Ende
      });
    }
    if (this.sortKey() === 'unnamed') {
      return list.sort((a, b) => {
        const aUnnamed = a.is_unknown || !a.name;
        const bUnnamed = b.is_unknown || !b.name;
        if (aUnnamed !== bUnnamed) { return aUnnamed ? -1 : 1; }
        return (a.name ?? '').localeCompare(b.name ?? '');
      });
    }
    if (this.sortKey() === 'count') {
      return list.sort((a, b) => b.count - a.count);
    }
    return list; // 'group' — Gruppierung übernimmt die Sortierung in personGroups()
  });

  protected readonly personGroups = computed((): { label: string; persons: PersonDto[] }[] => {
    if (this.sortKey() !== 'group') { return []; }
    const buckets = new Map<string, PersonDto[]>();
    for (const person of this.sortedPersons()) {
      const key = person.group_name ?? 'Ohne Gruppe';
      const bucket = buckets.get(key) ?? [];
      bucket.push(person);
      buckets.set(key, bucket);
    }
    const entries = [...buckets.entries()].sort(([a], [b]) => {
      if (a === 'Ohne Gruppe') { return 1; }
      if (b === 'Ohne Gruppe') { return -1; }
      return a.localeCompare(b);
    });
    return entries.map(([label, persons]) => ({ label, persons }));
  });

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

  protected onSetGroup(event: { id: number; groupName: string }): void {
    this.store.dispatch(personsActions.setPersonGroup({ id: event.id, groupName: event.groupName || null }));
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

  protected onDeleteClick(person: PersonDto): void {
    this.deletePersonTarget.set(person);
  }

  protected onConfirmDelete(personId: number): void {
    this.store.dispatch(personsActions.deletePerson({ id: personId }));
    this.deletePersonTarget.set(null);
  }

  protected onCreatePerson(name: string): void {
    this.store.dispatch(personsActions.createPerson({ name }));
    this.showCreateDialog.set(false);
  }

  protected cycleSortKey(): void {
    const currentIndex = this.SORT_CYCLE.indexOf(this.sortKey());
    const next = this.SORT_CYCLE[(currentIndex + 1) % this.SORT_CYCLE.length] ?? 'group';
    this.sortKey.set(next);
  }

  protected sortLabel(): string {
    return this.SORT_LABELS[this.sortKey()];
  }

  protected toggleGroupFilter(groupName: string): void {
    const next = new Set(this.groupFilter());
    if (next.has(groupName)) { next.delete(groupName); } else { next.add(groupName); }
    this.groupFilter.set(next);
  }

  protected setViewMode(mode: PersonViewMode): void {
    this.viewMode.set(mode);
  }

  protected setCardSize(size: Density): void {
    this.cardSize.set(size);
  }

  protected triggerClustering(): void {
    this.store.dispatch(personsActions.triggerClustering());
  }

  protected onAlphabetJump(personId: number): void {
    document.getElementById(`person-${personId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
