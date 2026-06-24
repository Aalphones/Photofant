import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { forkJoin } from 'rxjs';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import type { FaceGalleryItemDto, PersonDto } from '@photofant/models';
import { personsActions, personsSelectors } from '@photofant/store';
import { PersonService } from '@photofant/services';

@Component({
  selector: 'pf-review-unknown',
  imports: [Icon],
  templateUrl: './review-unknown.html',
  styleUrl: './review-unknown.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewUnknown {
  private readonly store = inject(Store);
  private readonly personService = inject(PersonService);

  private readonly allPersons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly unknownPerson = computed((): PersonDto | null =>
    this.allPersons().find((person: PersonDto) => person.is_unknown) ?? null
  );

  protected readonly namedPersons = computed((): PersonDto[] =>
    this.allPersons().filter((person: PersonDto) => !person.is_unknown)
  );

  protected readonly faces = signal<FaceGalleryItemDto[]>([]);
  protected readonly total = signal(0);
  protected readonly isLoading = signal(false);
  protected readonly page = signal(1);
  protected readonly pageSize = 48;

  protected readonly selected = signal<Set<number>>(new Set());
  private readonly anchorId = signal<number | null>(null);

  protected readonly selectedCount = computed(() => this.selected().size);

  protected readonly allSelected = computed((): boolean => {
    const faceList = this.faces();
    const sel = this.selected();
    return faceList.length > 0 && faceList.every((face: FaceGalleryItemDto) => sel.has(face.id));
  });

  protected readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.total() / this.pageSize))
  );

  protected readonly assignQuery = signal('');
  protected readonly showAssignPanel = signal(false);

  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.assignQuery().toLowerCase();
    return this.namedPersons().filter(
      (person: PersonDto) => !query || (person.name ?? '').toLowerCase().includes(query)
    );
  });

  constructor() {
    this.store.dispatch(personsActions.loadPersons());

    let initialLoadDone = false;
    effect(() => {
      const unknown = this.unknownPerson();
      if (unknown !== null && !initialLoadDone) {
        initialLoadDone = true;
        this.loadFacesForPage(1);
      }
    });
  }

  private loadFacesForPage(page: number): void {
    const unknown = this.unknownPerson();
    if (unknown === null) return;

    this.isLoading.set(true);
    this.personService.listFacesGallery({
      page,
      page_size: this.pageSize,
      person_id: unknown.id,
    }).subscribe({
      next: (result) => {
        this.faces.set(result.items);
        this.total.set(result.total);
        this.page.set(page);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }

  protected isSelected(faceId: number): boolean {
    return this.selected().has(faceId);
  }

  protected onCellClick(event: MouseEvent, faceId: number): void {
    if (event.shiftKey && this.anchorId() !== null) {
      this.doRangeSelect(faceId);
    } else {
      this.toggleSelect(faceId);
    }
  }

  private toggleSelect(faceId: number): void {
    this.anchorId.set(faceId);
    this.selected.update((sel: Set<number>) => {
      const next = new Set(sel);
      if (next.has(faceId)) {
        next.delete(faceId);
      } else {
        next.add(faceId);
      }
      return next;
    });
  }

  private doRangeSelect(targetId: number): void {
    const anchorId = this.anchorId();
    if (anchorId === null) {
      this.toggleSelect(targetId);
      return;
    }
    const faces = this.faces();
    const anchorIndex = faces.findIndex((face: FaceGalleryItemDto) => face.id === anchorId);
    const targetIndex = faces.findIndex((face: FaceGalleryItemDto) => face.id === targetId);
    if (anchorIndex === -1 || targetIndex === -1) {
      this.toggleSelect(targetId);
      return;
    }
    const start = Math.min(anchorIndex, targetIndex);
    const end = Math.max(anchorIndex, targetIndex);
    const rangeIds = faces.slice(start, end + 1).map((face: FaceGalleryItemDto) => face.id);
    this.selected.update((existing: Set<number>) => new Set([...existing, ...rangeIds]));
  }

  protected toggleAll(): void {
    this.anchorId.set(null);
    const faceList = this.faces();
    const sel = this.selected();
    if (faceList.every((face: FaceGalleryItemDto) => sel.has(face.id))) {
      this.selected.set(new Set());
    } else {
      this.selected.set(new Set(faceList.map((face: FaceGalleryItemDto) => face.id)));
    }
  }

  protected openAssignPanel(): void {
    this.showAssignPanel.set(true);
    this.assignQuery.set('');
  }

  protected closeAssignPanel(): void {
    this.showAssignPanel.set(false);
  }

  protected assignSelectedTo(personId: number): void {
    const ids = [...this.selected()];
    if (ids.length === 0) return;

    const requests = ids.map((faceId: number) => this.personService.assignFace(faceId, personId));
    forkJoin(requests).subscribe({
      next: () => {
        this.selected.set(new Set());
        this.anchorId.set(null);
        this.showAssignPanel.set(false);
        this.loadFacesForPage(this.page());
      },
    });
  }

  protected deleteSelected(): void {
    const ids = [...this.selected()];
    if (ids.length === 0) return;

    const requests = ids.map((faceId: number) => this.personService.deleteFace(faceId));
    forkJoin(requests).subscribe({
      next: () => {
        this.selected.set(new Set());
        this.anchorId.set(null);
        this.loadFacesForPage(this.page());
      },
    });
  }

  protected goPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.selected.set(new Set());
    this.anchorId.set(null);
    this.loadFacesForPage(page);
  }
}
