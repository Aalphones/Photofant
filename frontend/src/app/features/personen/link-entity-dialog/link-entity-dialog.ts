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

@Component({
  selector: 'pf-link-entity-dialog',
  imports: [Icon],
  templateUrl: './link-entity-dialog.html',
  styleUrl: './link-entity-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LinkEntityDialog {
  readonly person = input.required<PersonDto>();

  readonly close = output<void>();
  readonly select = output<EntityDto>();

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

  protected onQueryInput(value: string): void {
    this.query.set(value);
    this.query$.next(value);
  }

  protected onSelect(entity: EntityDto): void {
    this.select.emit(entity);
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
