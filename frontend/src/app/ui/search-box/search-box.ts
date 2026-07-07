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
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type { PersonDto, TagListItem } from '@photofant/models';
import { TagService } from '@photofant/services';
import { classificationSelectors, filtersActions, personsActions, personsSelectors, searchActions } from '@photofant/store';
import { Icon } from '../icon/icon';

interface AutocompleteItem {
  type: 'tag' | 'person' | 'semantic' | 'class';
  text: string;
  id?: number;
  count?: number;
  badge?: string;
}

interface RecentSearch {
  text: string;
  type: 'tag' | 'semantic' | 'class';
  id?: number;
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
  private readonly store         = inject(Store);
  private readonly tagService    = inject(TagService);
  private readonly router        = inject(Router);
  private readonly destroyRef    = inject(DestroyRef);

  private readonly queryInput$ = new Subject<string>();
  private readonly allPersons  = this.store.selectSignal(personsSelectors.selectAll);
  private readonly allCategories = this.store.selectSignal(classificationSelectors.selectAll);
  private readonly recentSearches = signal<RecentSearch[]>(this.loadRecentSearches());

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

  private readonly classificationSuggestions = computed<AutocompleteItem[]>(() => {
    const query = this.localQuery().trim().toLowerCase();
    if (!query) return [];
    const matches: AutocompleteItem[] = [];
    for (const category of this.allCategories()) {
      for (const label of category.labels) {
        if (label.name.toLowerCase().includes(query)) {
          matches.push({ type: 'class', text: label.name, id: label.id });
        }
      }
    }
    return matches.slice(0, 4);
  });

  protected readonly suggestions = computed<AutocompleteItem[]>(() => {
    const query = this.localQuery().trim();
    if (!query) {
      return this.recentSearches().map((recent: RecentSearch): AutocompleteItem => ({
        type: recent.type,
        text: recent.text,
        ...(recent.id != null ? { id: recent.id } : {}),
        ...(recent.type === 'semantic' ? { badge: 'Semantisch' } : {}),
      }));
    }
    const persons = this.personSuggestions().map((person: PersonDto): AutocompleteItem => ({
      type: 'person',
      text: person.name!,
      id: person.id,
      count: person.count,
    }));
    const tags = this.tagSuggestions().map((tag: TagListItem): AutocompleteItem => ({
      type: 'tag',
      text: tag.name,
      id: tag.id,
      count: tag.count,
    }));
    const classifications = this.classificationSuggestions();
    const semantic: AutocompleteItem = { type: 'semantic', text: query, badge: 'Semantisch' };
    return [...persons, ...tags, ...classifications, semantic];
  });

  constructor() {
    this.store.dispatch(personsActions.loadPersons());

    this.queryInput$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((query: string) => {
      this.store.dispatch(searchActions.setQuery({ q: query }));
      if (query) { this.navigateToGalleryIfNeeded(); }
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
      const item = items[active];
      if (active >= 0 && item !== undefined) {
        event.preventDefault();
        this.selectSuggestion(item);
      }
    }
  }

  protected clearSearch(): void {
    this.localQuery.set('');
    this.queryInput$.next('');
    this.store.dispatch(searchActions.clear());
  }

  protected selectSuggestion(item: AutocompleteItem): void {
    // WICHTIG: hier NICHT queryInput$.next('') aufrufen. Der Subject speist die
    // debounced setQuery-Subscription (300ms) — ein '' würde nach der Auswahl
    // setQuery({ q: '' }) feuern und damit mode auf 'text' zurücksetzen und q
    // leeren. Bei einer Semantik-Auswahl killt das den gerade gesetzten Filter
    // („kurz gesetzt, dann Reload auf ungefiltert"). Aufräumen läuft daher
    // synchron und pro Zweig über den Store, nicht über den Eingabe-Stream.
    if (item.type === 'person') {
      this.store.dispatch(searchActions.clear());
      this.store.dispatch(filtersActions.setPersonId({ personId: item.id! }));
    } else if (item.type === 'semantic') {
      this.store.dispatch(searchActions.setSemanticQuery({ q: item.text }));
      this.saveRecentSearch(item.text, 'semantic');
    } else if (item.type === 'class' && item.id != null) {
      this.store.dispatch(searchActions.clear());
      this.store.dispatch(filtersActions.setClassificationLabelIds({ classificationLabelIds: [item.id] }));
      this.saveRecentSearch(item.text, 'class', item.id);
    } else if (item.id != null) {
      // Tag exakt filtern (statt als freien q-Text zu schicken) — sonst liefern
      // mehrdeutige Tag-Namen falsche Treffer (ADR-015).
      this.store.dispatch(searchActions.clear());
      this.store.dispatch(filtersActions.setTagIds({ tagIds: [item.id] }));
      this.saveRecentSearch(item.text, 'tag', item.id);
    } else {
      // Alte, vor diesem Fix gemerkte Tag-Suche ohne ID (Altbestand in
      // localStorage) — als Freitext statt als kaputten Tag-Filter ausführen.
      this.store.dispatch(searchActions.setQuery({ q: item.text }));
    }
    this.localQuery.set('');
    this.isOpen.set(false);
    this.navigateToGalleryIfNeeded();
  }

  private navigateToGalleryIfNeeded(): void {
    if (!this.router.url.startsWith('/galerie')) {
      void this.router.navigate(['/galerie']);
    }
  }

  private loadRecentSearches(): RecentSearch[] {
    try {
      const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
      if (!raw) return [];
      const parsed: unknown = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      // migrate old format (plain strings, or objects without id) to RecentSearch objects
      return parsed.map((entry: unknown): RecentSearch => {
        if (typeof entry === 'string') return { text: entry, type: 'tag' };
        if (typeof entry === 'object' && entry !== null && 'text' in entry) {
          const typed = entry as { text: unknown; type?: unknown; id?: unknown };
          const text = typeof typed.text === 'string' ? typed.text : '';
          const type = typed.type === 'semantic' || typed.type === 'class' ? typed.type : 'tag';
          const id = typeof typed.id === 'number' ? typed.id : undefined;
          return { text, type, ...(id != null ? { id } : {}) };
        }
        return { text: String(entry), type: 'tag' };
      }).filter((entry: RecentSearch) => entry.text.trim() !== '');
    } catch {
      return [];
    }
  }

  private saveRecentSearch(text: string, type: 'tag' | 'semantic' | 'class', id?: number): void {
    const trimmed = text.trim();
    if (!trimmed) return;
    const filtered = this.recentSearches().filter(
      (entry: RecentSearch) => !(entry.text === trimmed && entry.type === type),
    );
    const next = [{ text: trimmed, type, ...(id != null ? { id } : {}) }, ...filtered].slice(0, MAX_RECENT);
    this.recentSearches.set(next);
    try {
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next));
    } catch {
      // quota exceeded — ignore
    }
  }
}
