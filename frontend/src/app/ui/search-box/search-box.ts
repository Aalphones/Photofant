import { DOCUMENT } from '@angular/common';
import type { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type { PersonDto, SemanticSearchResponse, TagListItem } from '@photofant/models';
import { extractApiErrorMessage, SearchService, TagService } from '@photofant/services';
import { classificationSelectors, filtersActions, personsActions, personsSelectors, searchActions, searchSelectors } from '@photofant/store';
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
  private readonly searchService = inject(SearchService);
  private readonly router        = inject(Router);
  private readonly destroyRef    = inject(DestroyRef);
  private readonly document      = inject(DOCUMENT);

  private readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  private readonly queryInput$ = new Subject<string>();
  private readonly allPersons  = this.store.selectSignal(personsSelectors.selectAll);
  private readonly allCategories = this.store.selectSignal(classificationSelectors.selectAll);
  private readonly recentSearches = signal<RecentSearch[]>(this.loadRecentSearches());

  protected readonly localQuery  = signal('');
  protected readonly isOpen      = signal(false);
  protected readonly activeIndex = signal(-1);

  // Semantik-Modus (P36 Phase 4): expliziter Umschalter neben der exakten Tag-/Caption-Suche.
  // Quelle der Wahrheit ist der Store-Suchmodus (bleibt so automatisch synchron, auch wenn
  // ein Filter-Chip anderswo — Sub-Toolbar — die Suche zurücksetzt). `pendingSemanticToggle`
  // überbrückt nur die Lücke „Umschalter geklickt, aber noch kein Text getippt" — der Store
  // kennt erst ab dem ersten `setSemanticQuery`-Dispatch einen Semantik-Modus.
  private readonly storeSearchMode = this.store.selectSignal(searchSelectors.selectMode);
  private readonly pendingSemanticToggle = signal(false);
  protected readonly semanticMode = computed((): boolean =>
    this.storeSearchMode() === 'semantic' || this.pendingSemanticToggle()
  );

  // Reverse Image Search (P36): Drop/Upload eines Bildes → ähnliche Bibliotheks-Bilder.
  protected readonly isDropTarget       = signal(false);
  protected readonly isReverseSearching = signal(false);
  protected readonly reverseError       = signal<string | null>(null);
  private reverseErrorTimer: ReturnType<typeof setTimeout> | null = null;

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
    if (this.semanticMode()) {
      // Im Semantik-Modus zählt der Freitext direkt als Anfrage — keine exakten Tag-/Personen-/
      // Klassifikations-Vorschläge, die den Modus beim Klicken wieder verlassen würden.
      return [];
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
    return [...persons, ...tags, ...classifications];
  });

  constructor() {
    this.store.dispatch(personsActions.loadPersons());

    this.queryInput$.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((query: string) => {
      if (this.semanticMode()) {
        this.store.dispatch(searchActions.setSemanticQuery({ q: query }));
      } else {
        this.store.dispatch(searchActions.setQuery({ q: query }));
      }
      // Ab hier führt der Store-Modus — die vorgemerkte Absicht hat ihren Zweck erfüllt.
      this.pendingSemanticToggle.set(false);
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
    this.pendingSemanticToggle.set(false);
    this.store.dispatch(searchActions.clear());
  }

  // Umschalter „semantische Suche" (P36 Phase 4) — wirkt sofort auf einen bereits eingegebenen
  // Freitext; ohne Text merkt sich `pendingSemanticToggle` nur die Absicht für den nächsten
  // Tastendruck (siehe Kommentar am `semanticMode`-Signal oben).
  protected toggleSemanticMode(): void {
    const turningOn = !this.semanticMode();
    const query = this.localQuery().trim();
    if (!query) {
      this.pendingSemanticToggle.set(turningOn);
      return;
    }
    this.pendingSemanticToggle.set(false);
    if (turningOn) {
      this.store.dispatch(searchActions.setSemanticQuery({ q: query }));
      this.saveRecentSearch(query, 'semantic');
    } else {
      this.store.dispatch(searchActions.setQuery({ q: query }));
    }
    this.navigateToGalleryIfNeeded();
  }

  protected selectSuggestion(item: AutocompleteItem): void {
    // WICHTIG: hier NICHT queryInput$.next('') aufrufen. Der Subject speist die
    // debounced setQuery-Subscription (300ms) — ein '' würde nach der Auswahl
    // setQuery({ q: '' }) feuern und damit mode auf 'text' zurücksetzen und q
    // leeren. Bei einer Semantik-Auswahl killt das den gerade gesetzten Filter
    // („kurz gesetzt, dann Reload auf ungefiltert"). Aufräumen läuft daher
    // synchron und pro Zweig über den Store, nicht über den Eingabe-Stream.
    // pendingSemanticToggle hat in allen Zweigen ausgedient — entweder übernimmt gleich der
    // Store-Modus (semantic-Zweig) oder der Zweig will explizit den exakten Modus.
    this.pendingSemanticToggle.set(false);
    if (item.type === 'person') {
      this.store.dispatch(searchActions.clear());
      this.store.dispatch(filtersActions.setPersonId({ personId: item.id! }));
    } else if (item.type === 'semantic') {
      // Nur noch über die Verlaufsliste erreichbar (Umschalter ist der Weg für neue Anfragen).
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

  // --- Reverse Image Search (P36) ---

  protected onUploadClick(): void {
    this.fileInput()?.nativeElement.click();
  }

  protected onFilePicked(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.runReverseSearch(input.files?.[0]);
    // Zurücksetzen, damit dasselbe Bild direkt nochmal wählbar ist (change feuert sonst nicht).
    input.value = '';
  }

  protected onDragEnter(event: DragEvent): void {
    if (!event.dataTransfer?.types.includes('Files')) { return; }
    event.preventDefault();
    this.isDropTarget.set(true);
  }

  protected onDragOver(event: DragEvent): void {
    if (!event.dataTransfer?.types.includes('Files')) { return; }
    event.preventDefault();
  }

  protected onDragLeave(): void {
    this.isDropTarget.set(false);
  }

  // Kein stopPropagation: der Drop darf zur globalen Shell durchperlen, die ihr
  // Drag-Overlay zurücksetzt und den Import überspringt, wenn das Ziel die Suchbox
  // ist (Guard in shell.ts) — sonst würde ein Suchbox-Drop zusätzlich den Import öffnen.
  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDropTarget.set(false);
    this.runReverseSearch(event.dataTransfer?.files?.[0]);
  }

  private runReverseSearch(file: File | null | undefined): void {
    if (file == null) { return; }
    if (!file.type.startsWith('image/')) {
      this.setReverseError('Bitte ein Bild ablegen oder auswählen.');
      return;
    }
    this.reverseError.set(null);
    this.isReverseSearching.set(true);
    void this.performReverseSearch(file);
  }

  private async performReverseSearch(file: File): Promise<void> {
    let thumbnailDataUrl = '';
    try {
      thumbnailDataUrl = await this.buildThumbnail(file);
    } catch {
      // Vorschau ist optional — die Suche läuft auch ohne Thumbnail weiter.
      thumbnailDataUrl = '';
    }

    this.searchService.searchByImage(file)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: SemanticSearchResponse) => {
          this.isReverseSearching.set(false);
          const similarIds = response.hits.map((hit): number => hit.asset_id);
          if (similarIds.length === 0) {
            this.setReverseError('Keine ähnlichen Bilder gefunden.');
            return;
          }
          this.store.dispatch(filtersActions.setReverseSearch({
            reverseSearch: { thumbnailDataUrl, similarIds },
          }));
          this.localQuery.set('');
          this.isOpen.set(false);
          this.navigateToGalleryIfNeeded();
        },
        error: (error: HttpErrorResponse) => {
          this.isReverseSearching.set(false);
          this.setReverseError(extractApiErrorMessage(error, 'Reverse-Suche fehlgeschlagen.'));
        },
      });
  }

  // Kleines Vorschau-Thumbnail (max. 96px) als Data-URL für den Filter-Chip — statt das
  // volle Upload-Bild (bis 15 MB) in den Store zu legen.
  private async buildThumbnail(file: File, maxSize = 96): Promise<string> {
    const bitmap = await createImageBitmap(file);
    try {
      const scale = Math.min(1, maxSize / Math.max(bitmap.width, bitmap.height));
      const width = Math.max(1, Math.round(bitmap.width * scale));
      const height = Math.max(1, Math.round(bitmap.height * scale));
      const canvas = this.document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');
      if (context == null) { return ''; }
      context.drawImage(bitmap, 0, 0, width, height);
      return canvas.toDataURL('image/jpeg', 0.7);
    } finally {
      bitmap.close();
    }
  }

  private setReverseError(message: string): void {
    if (this.reverseErrorTimer != null) { clearTimeout(this.reverseErrorTimer); }
    this.reverseError.set(message);
    this.reverseErrorTimer = setTimeout(() => this.reverseError.set(null), 5000);
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
