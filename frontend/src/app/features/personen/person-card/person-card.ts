import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { PersonDto, PersonFace } from '@photofant/models';
import { Icon } from '@photofant/ui';
import { AssetService, PersonService } from '@photofant/services';
import { groupColor } from '../group-color.util';

export type PersonViewMode = 'single' | 'grid4' | 'face';

@Component({
  selector: 'pf-person-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './person-card.html',
  styleUrl: './person-card.scss',
})
export class PersonCard {
  private readonly personService = inject(PersonService);
  private readonly assetService = inject(AssetService);
  private readonly elementRef = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly groupColor = groupColor;

  readonly person = input.required<PersonDto>();
  readonly viewMode = input<PersonViewMode>('face');

  readonly select = output<void>();
  readonly rename = output<{ id: number; name: string }>();
  readonly setGroup = output<{ id: number; groupName: string }>();
  readonly importFiles = output<{ personId: number; files: File[] }>();
  readonly splitClick = output<void>();
  readonly dupeCheck = output<void>();
  readonly revealInFileBrowser = output<void>();
  readonly deleteClick = output<void>();

  protected readonly isEditing = signal(false);
  protected readonly editName = signal('');
  protected readonly isEditingGroup = signal(false);
  protected readonly editGroupName = signal('');
  protected readonly isDragOver = signal(false);
  protected readonly menuOpen = signal(false);
  protected readonly extraPhotoUrls = signal<string[]>([]);

  private lastLoadedPersonId: number | null = null;

  private readonly nameInputRef = viewChild<ElementRef<HTMLInputElement>>('nameInput');
  private readonly groupInputRef = viewChild<ElementRef<HTMLInputElement>>('groupInput');

  constructor() {
    const closeOnOutsideClick = (event: MouseEvent): void => {
      if (this.menuOpen() && !this.elementRef.nativeElement.contains(event.target as Node)) {
        this.menuOpen.set(false);
      }
    };
    document.addEventListener('click', closeOnOutsideClick);
    this.destroyRef.onDestroy(() => document.removeEventListener('click', closeOnOutsideClick));

    effect(() => {
      const mode = this.viewMode();
      const personId = this.person().id;
      if (mode === 'face') { return; }
      if (this.lastLoadedPersonId === personId && this.extraPhotoUrls().length > 0) { return; }
      this.lastLoadedPersonId = personId;
      this.personService.getPersonFaces(personId).subscribe((faces: PersonFace[]) => {
        const urls = faces
          .filter((face: PersonFace) => face.asset_id != null)
          .slice(0, 4)
          .map((face: PersonFace) => this.assetService.thumbnailUrl(face.asset_id as number));
        this.extraPhotoUrls.set(urls);
      });
    });
  }

  protected get avatarUrl(): string | null {
    const faceId = this.person().portrait_face_id;
    return faceId != null ? this.personService.portraitUrl(faceId) : null;
  }

  protected get singleImageUrl(): string | null {
    return this.extraPhotoUrls()[0] ?? this.avatarUrl;
  }

  protected get gridImageUrls(): string[] {
    const urls = this.extraPhotoUrls();
    return urls.length > 0 ? urls : (this.avatarUrl != null ? [this.avatarUrl] : []);
  }

  protected get displayName(): string {
    const p = this.person();
    if (p.is_unknown) return 'Unbekannt';
    return p.name ?? '—';
  }

  protected onCardClick(event: MouseEvent): void {
    if (this.isEditing() || this.isEditingGroup()) { return; }
    if (this.menuOpen()) {
      this.menuOpen.set(false);
      event.stopPropagation();
      return;
    }
    this.select.emit();
  }

  protected toggleMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.update((open: boolean) => !open);
  }

  private startEdit(): void {
    this.editName.set(this.person().name ?? '');
    this.isEditing.set(true);
    setTimeout(() => { this.nameInputRef()?.nativeElement.focus(); }, 0);
  }

  protected confirmEdit(): void {
    const name = this.editName().trim();
    if (name) {
      this.rename.emit({ id: this.person().id, name });
    }
    this.isEditing.set(false);
  }

  protected cancelEdit(): void {
    this.isEditing.set(false);
  }

  protected onEditKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmEdit(); }
    if (event.key === 'Escape') { this.cancelEdit(); }
    event.stopPropagation();
  }

  protected onRenameClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.startEdit();
  }

  private startEditGroup(): void {
    this.editGroupName.set(this.person().group_name ?? '');
    this.isEditingGroup.set(true);
    setTimeout(() => { this.groupInputRef()?.nativeElement.focus(); }, 0);
  }

  protected confirmGroupEdit(): void {
    this.setGroup.emit({ id: this.person().id, groupName: this.editGroupName().trim() });
    this.isEditingGroup.set(false);
  }

  protected cancelGroupEdit(): void {
    this.isEditingGroup.set(false);
  }

  protected onGroupEditKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmGroupEdit(); }
    if (event.key === 'Escape') { this.cancelGroupEdit(); }
    event.stopPropagation();
  }

  protected onGroupClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.startEditGroup();
  }

  protected onSplitClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.splitClick.emit();
  }

  protected onDupeCheckClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.dupeCheck.emit();
  }

  protected onRevealClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.revealInFileBrowser.emit();
  }

  protected onDeleteClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    this.deleteClick.emit();
  }

  protected onImportClick(event: MouseEvent): void {
    event.stopPropagation();
    this.menuOpen.set(false);
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = true;
    input.accept = 'image/*';
    input.onchange = (): void => {
      if (input.files?.length) {
        this.importFiles.emit({ personId: this.person().id, files: Array.from(input.files) });
      }
    };
    input.click();
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(true);
  }

  protected onDragLeave(): void {
    this.isDragOver.set(false);
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
    const files = Array.from(event.dataTransfer?.files ?? []).filter((file: File) =>
      file.type.startsWith('image/')
    );
    if (files.length) {
      this.importFiles.emit({ personId: this.person().id, files });
    }
  }
}
