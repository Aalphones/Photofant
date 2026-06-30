import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type { PersonDto, TagListItem } from '@photofant/models';
import { TagService } from '@photofant/services';
import { filtersActions, personsActions, personsSelectors, searchActions } from '@photofant/store';
import { Icon } from '../icon/icon';

interface AutocompleteItem {
  type: 'tag' | 'person';
  text: string;
  id?: number;
  count?: number;
}

const RECENT_SEARCHES_KEY = 'pf_recent_searches';
const MAX_RECENT = 5;

@Component({
  selector: 'pf-search-box',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './search-box.html',
  styleUrl: './search-box.scss',
})
export class SearchBox {
  private readonly store      = inject(Store);
  private readonly tagService = inject(TagService);
  private readonly destroyRef = inject(DestroyRef);

  private readonly queryInput$    = new Subject<string>();
  private readonly allPersons     = this.store.selectSignal(personsSelectors.selectAll);
  private readonly recentSearches = signal<string[]>(this.loadRecentSearches());

  protected readonly localQuery  = signal('');
  protected readonly isOpen      = signal(false);
  protected readonly activeIndex = signal(-1);

  private readonly tagSuggestions = toSignal(
    this.queryInput$.pipe(
      debounceTime(150),
      distinctUntilChanged(),
      switchMap((query: string) => {
        if (!query || query.length < 1) return of([] as TagListItem[]);
        return this.tagService.listTags(query, 6).pipe(
          catchError(() => of([] as TagListItem[])),
        );
      }),
    ),
    { initialValue: [] as TagListItem[] },
  );

  private readonly personSuggestions = computed<PersonDto[]>(() => {
    const query = this.localQuery().trim().toLowerCase();
    if (!query) return [];
    return this.allPersons()
      .filter((person: PersonDto) =>
        !person.is_unknown && person.name != null && person.name.toLowerCase().includes(query)
      )
      .slice(0, 4);
  });

  protected readonly suggestions = computed<AutocompleteItem[]>(() => {
    const query = this.localQuery().trim();
    if (!query) {
      return this.recentSearches().map((text: string) => ({ type: 'tag' as const, text }));
    }
    const persons = this.personSuggestions().map((person: PersonDto) => ({
      type: 'person' as const,
      text: person.name!,
      id: person.id,
      count: person.count,
    }));
    const tags = this.tagSuggestions().map((tag: TagListItem) => ({
      type: 'tag' as const,
      text: tag.name,
      id: tag.id,
      count: tag.count,
    }));
    return [...persons, ...tags];
  });

  constructor() {
    this.store.dispatch(personsActions.loadPersons());

    this.queryInput$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((query: string) => {
      this.store.dispatch(searchActions.setQuery({ q: query }));
    });

    // Reset keyboard selection whenever the list changes
    effect(() => {
      this.suggestions();
      this.activeIndex.set(-1);
    });
  }

  protected onInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.localQuery.set(value);
    this.queryInput$.next(value);
  }

  protected onFocus(): void {
    this.isOpen.set(true);
  }

  protected onBlur(): void {
    // delay so suggestion clicks fire before the dropdown disappears
    setTimeout(() => this.isOpen.set(false), 180);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.clearSearch();
      return;
    }

    const items = this.suggestions();
    if (!this.isOpen() || items.length === 0) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex.update((index: number) =>
        index < items.length - 1 ? index + 1 : 0,
      );
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex.update((index: number) =>
        index > 0 ? index - 1 : items.length - 1,
      );
    } else if (event.key === 'Enter') {
      const active = this.activeIndex();
      if (active >= 0 && active < items.length) {
        event.preventDefault();
        this.selectSuggestion(items[active]);
      }
    }
  }

  protected clearSearch(): void {
    this.localQuery.set('');
    this.queryInput$.next('');
    this.store.dispatch(searchActions.clear());
  }

  protected selectSuggestion(item: AutocompleteItem): void {
    if (item.type === 'person') {
      this.store.dispatch(filtersActions.setPersonId({ personId: item.id! }));
      this.localQuery.set('');
      this.queryInput$.next('');
    } else {
      this.localQuery.set(item.text);
      this.queryInput$.next(item.text);
      this.store.dispatch(searchActions.setQuery({ q: item.text }));
      this.saveRecentSearch(item.text);
    }
    this.isOpen.set(false);
  }

  private loadRecentSearches(): string[] {
    try {
      const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  }

  private saveRecentSearch(text: string): void {
    const trimmed = text.trim();
    if (!trimmed) return;
    const next = [trimmed, ...this.recentSearches().filter((s: string) => s !== trimmed)].slice(0, MAX_RECENT);
    this.recentSearches.set(next);
    try {
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
    } catch {
      // quota exceeded — ignore
    }
  }
}
