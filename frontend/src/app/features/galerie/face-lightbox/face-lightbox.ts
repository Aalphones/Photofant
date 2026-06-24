import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DOCUMENT } from '@angular/common';
import { Store } from '@ngrx/store';
import type { FaceGalleryItemDto, FaceMatch, PersonDto } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { personsActions, personsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-face-lightbox',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './face-lightbox.html',
  styleUrl: './face-lightbox.scss',
})
export class FaceLightbox {
  private readonly store         = inject(Store);
  private readonly personService = inject(PersonService);
  private readonly destroyRef    = inject(DestroyRef);
  private readonly document      = inject(DOCUMENT);

  readonly faceItem = input.required<FaceGalleryItemDto>();
  readonly hasPrev  = input<boolean>(false);
  readonly hasNext  = input<boolean>(false);

  readonly close       = output<void>();
  readonly prev        = output<void>();
  readonly next        = output<void>();
  readonly openAsset   = output<number>();
  readonly faceDeleted = output<number>();

  protected readonly faceMatches        = signal<FaceMatch[]>([]);
  protected readonly faceMatchesLoading = signal(false);
  protected readonly creatingNewPerson  = signal(false);
  protected readonly newPersonName      = signal('');
  protected readonly personSearchQuery  = signal('');
  protected readonly assignedName       = signal<string | null>(null);

  private readonly allPersons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly displayName = computed((): string | null =>
    this.assignedName() ?? this.faceItem().person_name
  );

  protected readonly personSearchResults = computed((): PersonDto[] => {
    const query = this.personSearchQuery().trim().toLowerCase();
    if (query.length === 0) { return []; }
    return this.allPersons()
      .filter((person: PersonDto) =>
        !person.is_unknown && person.name != null && person.name.toLowerCase().includes(query)
      )
      .slice(0, 15);
  });

  private activeFaceId: number | null = null;

  constructor() {
    effect((): void => {
      const face = this.faceItem();
      this.faceMatches.set([]);
      this.personSearchQuery.set('');
      this.creatingNewPerson.set(false);
      this.newPersonName.set('');
      this.assignedName.set(null);
      this.loadMatches(face.id);
    });

    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
      if (event.key === 'Escape') { this.close.emit(); }
      else if (event.key === 'ArrowLeft')  { if (this.hasPrev()) { this.prev.emit(); } }
      else if (event.key === 'ArrowRight') { if (this.hasNext()) { this.next.emit(); } }
    };
    this.document.addEventListener('keydown', onKeyDown);
    this.destroyRef.onDestroy(() => this.document.removeEventListener('keydown', onKeyDown));
  }

  private loadMatches(faceId: number): void {
    this.activeFaceId = faceId;
    this.faceMatchesLoading.set(true);
    this.store.dispatch(personsActions.loadPersons());
    this.personService.getFaceMatches(faceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (matches: FaceMatch[]) => {
          if (this.activeFaceId === faceId) {
            this.faceMatches.set(matches);
            this.faceMatchesLoading.set(false);
          }
        },
        error: () => {
          if (this.activeFaceId === faceId) {
            this.faceMatchesLoading.set(false);
          }
        },
      });
  }

  protected assignFaceToPerson(personId: number, personName: string | null): void {
    const face = this.faceItem();
    this.personService.assignFace(face.id, personId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.assignedName.set(personName);
          this.faceMatches.set([]);
          this.personSearchQuery.set('');
        },
        error: (err: unknown) => { console.error('[FaceLightbox] assign failed', err); },
      });
  }

  protected deleteFace(): void {
    const faceId = this.faceItem().id;
    this.personService.deleteFace(faceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.faceDeleted.emit(faceId);
          this.close.emit();
        },
        error: (err: unknown) => { console.error('[FaceLightbox] delete failed', err); },
      });
  }

  protected startCreatePerson(): void {
    this.creatingNewPerson.set(true);
    this.newPersonName.set('');
  }

  protected cancelCreatePerson(): void {
    this.creatingNewPerson.set(false);
    this.newPersonName.set('');
  }

  protected confirmCreatePerson(): void {
    const name = this.newPersonName().trim();
    if (!name) {
      this.cancelCreatePerson();
      return;
    }
    this.personService.createPerson(name)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (person: PersonDto) => {
          this.creatingNewPerson.set(false);
          this.newPersonName.set('');
          this.assignFaceToPerson(person.id, person.name);
        },
        error: () => { this.creatingNewPerson.set(false); },
      });
  }

  protected onNewPersonKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter')  { this.confirmCreatePerson(); }
    if (event.key === 'Escape') { this.cancelCreatePerson(); }
  }

  protected matchScorePercent(score: number): number {
    return Math.round(score * 100);
  }
}
