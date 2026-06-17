import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type { SearchMode, TagListItem } from '@photofant/models';
import { TagService } from '@photofant/services';
import { searchActions, searchSelectors } from '@photofant/store';
import { Icon } from '../icon/icon';

interface AutocompleteItem {
  text: string;
  id?: number;
  count?: number;
}

const RECENT_SEARCHES_KEY = 'pf_recent_searches';
const MAX_RECENT = 5;
const MODES: ReadonlyArray<{ value: SearchMode; label: string }> = [
  { value: 'tags',     label: 'Tags' },
  { value: 'caption',  label: 'Caption' },
  { value: 'semantic', label: 'Semantisch' },
];

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

  private readonly queryInput$ = new Subject<string>();

  protected readonly currentMode = this.store.selectSignal(searchSelectors.selectMode);
  protected readonly localQuery  = signal('');
  protected readonly isOpen      = signal(false);
  protected readonly modes       = MODES;

  private readonly recentSearches = signal<string[]>(this.loadRecentSearches());

  private readonly tagSuggestions = toSignal(
    this.queryInput$.pipe(
      debounceTime(150),
      distinctUntilChanged(),
      switchMap((q: string) => {
        if (!q || q.length < 1) return of([] as TagListItem[]);
        return this.tagService.listTags(q, 8).pipe(
          catchError(() => of([] as TagListItem[])),
        );
      }),
    ),
    { initialValue: [] as TagListItem[] },
  );

  protected readonly suggestions = computed<AutocompleteItem[]>(() => {
    const mode = this.currentMode();
    if (mode === 'tags') {
      return this.tagSuggestions().map((tag: TagListItem) => ({
        text:  tag.name,
        id:    tag.id,
        count: tag.count,
      }));
    }
    return this.recentSearches().map((text: string) => ({ text }));
  });

  protected readonly placeholder = computed<string>(() => {
    const mode = this.currentMode();
    if (mode === 'caption')  return 'Bildtext suchen…';
    if (mode === 'semantic') return 'Semantisch suchen…';
    return 'Tags suchen…';
  });

  protected readonly modeLabel = computed<string>(() => {
    const found = MODES.find((m) => m.value === this.currentMode());
    return found?.label ?? 'Tags';
  });

  constructor() {
    this.queryInput$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((q: string) => {
      this.store.dispatch(searchActions.setQuery({ q }));
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

  protected clearSearch(): void {
    this.localQuery.set('');
    this.queryInput$.next('');
    this.store.dispatch(searchActions.clear());
  }

  protected setMode(mode: SearchMode): void {
    this.localQuery.set('');
    this.store.dispatch(searchActions.setMode({ mode }));
  }

  protected cycleMode(): void {
    const current = this.currentMode();
    const index   = MODES.findIndex((m) => m.value === current);
    const next    = MODES[(index + 1) % MODES.length];
    if (next !== undefined) {
      this.localQuery.set('');
      this.store.dispatch(searchActions.setMode({ mode: next.value }));
    }
  }

  protected selectSuggestion(item: AutocompleteItem): void {
    this.localQuery.set(item.text);
    this.queryInput$.next(item.text);
    this.store.dispatch(searchActions.setQuery({ q: item.text }));
    if (this.currentMode() !== 'tags') {
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
