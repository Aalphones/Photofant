import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type { EntityDto, PersonDto } from '@photofant/models';
import { KnowledgeService } from '@photofant/services';
import { Icon } from '@photofant/ui';

// P38 Phase 5 — zweiter Modus "person": statt Wissen für eine feste Person zu suchen
// (bisheriges Verhalten), wird hier eine Person für eine feste, unverknüpfte Notiz
// gesucht (Wissen-Übersicht, Sektion "Nicht verknüpfte Notizen"). Gleicher Dialog,
// weil beides "so eine Sache mit einer anderen verknüpfen" ist — kein zweites Modal
// für dieselbe Interaktion.
export type LinkEntityDialogMode = 'entity' | 'person';

@Component({
  selector: 'pf-link-entity-dialog',
  imports: [Icon],
  templateUrl: './link-entity-dialog.html',
  styleUrl: './link-entity-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LinkEntityDialog {
  readonly mode = input<LinkEntityDialogMode>('entity');
  // Modus "entity": die Person, für die Wissen gesucht wird.
  readonly person = input<PersonDto | null>(null);
  // Modus "person": Titel der unverknüpften Notiz, für die eine Person gesucht wird.
  readonly entityTitle = input<string | null>(null);
  // Modus "person": Kandidatenpool — bereits geladen (`personsSelectors.selectAll`),
  // kein eigener Request nötig.
  readonly persons = input<PersonDto[]>([]);

  readonly close = output<void>();
  readonly select = output<EntityDto>();
  readonly selectPerson = output<PersonDto>();

  private readonly knowledgeService = inject(KnowledgeService);

  protected readonly query = signal('');
  private readonly query$ = new Subject<string>();

  // Debounce + Live-Suche über die Wissensbasis — gleiches Muster wie das
  // Beziehungs-Autocomplete im Entity-Wizard.
  protected readonly results = toSignal(
    this.query$.pipe(
      debounceTime(200),
      distinctUntilChanged(),
      switchMap((query: string) => {
        if (query.trim().length < 2) {
          return of([] as EntityDto[]);
        }
        return this.knowledgeService.searchEntities(query).pipe(
          catchError(() => of([] as EntityDto[])),
        );
      }),
    ),
    { initialValue: [] as EntityDto[] },
  );

  protected readonly hasQuery = computed((): boolean => this.query().trim().length >= 2);

  // Modus "person": rein clientseitiger Filter über den bereits geladenen Pool — keine
  // Mindestlänge nötig, leere Eingabe zeigt die volle Liste (Browsing wie im Design).
  protected readonly personResults = computed((): PersonDto[] => {
    const needle = this.query().trim().toLowerCase();
    const candidates = this.persons().filter(
      (candidate: PersonDto) => !candidate.is_unknown && candidate.name != null,
    );
    if (needle.length === 0) { return candidates; }
    return candidates.filter((candidate: PersonDto) => candidate.name?.toLowerCase().includes(needle));
  });

  protected onQueryInput(value: string): void {
    this.query.set(value);
    this.query$.next(value);
  }

  protected onSelect(entity: EntityDto): void {
    this.select.emit(entity);
  }

  protected onSelectPerson(person: PersonDto): void {
    this.selectPerson.emit(person);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.close.emit();
    }
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('link-entity-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
