import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import type { PersonDto } from '@photofant/models';
import { Icon } from '@photofant/ui';
import { PersonService } from '@photofant/services';

@Component({
  selector: 'pf-person-card',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './person-card.html',
  styleUrl: './person-card.scss',
})
export class PersonCard {
  private readonly personService = inject(PersonService);

  readonly person = input.required<PersonDto>();

  readonly select = output<void>();
  readonly rename = output<{ id: number; name: string }>();
  readonly importFiles = output<{ personId: number; files: File[] }>();
  readonly splitClick = output<void>();
  readonly dupeCheck = output<void>();

  protected readonly isEditing = signal(false);
  protected readonly editName = signal('');
  protected readonly isDragOver = signal(false);
  protected readonly actionsVisible = signal(false);

  private longPressTimer: ReturnType<typeof setTimeout> | null = null;

  private readonly nameInputRef = viewChild<ElementRef<HTMLInputElement>>('nameInput');

  protected get avatarUrl(): string | null {
    const faceId = this.person().portrait_face_id;
    return faceId != null ? this.personService.portraitUrl(faceId) : null;
  }

  protected get displayName(): string {
    const p = this.person();
    if (p.is_unknown) return 'Unbekannt';
    return p.name ?? '—';
  }

  protected onCardClick(event: MouseEvent): void {
    if (this.isEditing()) return;
    if (this.actionsVisible()) {
      this.actionsVisible.set(false);
      event.stopPropagation();
      return;
    }
    this.select.emit();
    event.stopPropagation();
  }

  protected onPointerDown(): void {
    if (this.person().is_unknown) return;
    this.longPressTimer = setTimeout(() => { this.actionsVisible.set(true); }, 600);
  }

  protected onPointerUp(): void {
    if (this.longPressTimer !== null) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
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
    this.actionsVisible.set(false);
    this.startEdit();
  }

  protected onSplitClick(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsVisible.set(false);
    this.splitClick.emit();
  }

  protected onDupeCheckClick(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsVisible.set(false);
    this.dupeCheck.emit();
  }

  protected onImportClick(event: MouseEvent): void {
    event.stopPropagation();
    this.actionsVisible.set(false);
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
