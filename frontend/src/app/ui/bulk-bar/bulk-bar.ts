import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { of, switchMap } from 'rxjs';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Icon } from '../icon/icon';
import { TagService } from '../../services/tag.service';
import type { TagListItem } from '@photofant/models';

export interface BulkAlbumOption {
  id: number;
  name: string;
}

@Component({
  selector: 'pf-bulk-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './bulk-bar.html',
  styleUrl: './bulk-bar.scss',
})
export class BulkBar {
  readonly count = input.required<number>();
  readonly albums = input<BulkAlbumOption[]>([]);
  readonly trainingSets = input<BulkAlbumOption[]>([]);
  readonly canUpscale = input<boolean>(false);

  readonly close = output<void>();
  readonly tagAction = output<{ add: string[]; remove: number[] }>();
  readonly addToAlbum = output<number>();
  readonly addToTrainingSet = output<number>();
  readonly rerunAction = output<void>();
  readonly editAction = output<void>();
  readonly upscaleAction = output<void>();
  readonly dupeScanAction = output<void>();
  readonly trashAction = output<void>();

  private readonly tagService = inject(TagService);

  protected readonly showTagInput = signal(false);
  protected readonly tagInput = signal('');
  protected readonly showAlbumMenu = signal(false);
  protected readonly showTrainingSetMenu = signal(false);

  protected readonly tagSuggestions = toSignal(
    toObservable(this.tagInput).pipe(
      switchMap((value: string) => {
        const lastSegment = value.split(',').pop()?.trim() ?? '';
        return lastSegment.length >= 1
          ? this.tagService.listTags(lastSegment, 8)
          : of([]);
      }),
    ),
    { initialValue: [] as TagListItem[] },
  );

  protected readonly countLabel = computed((): string => {
    const n = this.count();
    return n === 1 ? '1 Bild ausgewählt' : `${n} Bilder ausgewählt`;
  });

  protected openTagInput(): void {
    this.showTagInput.set(true);
  }

  protected pickSuggestion(name: string): void {
    const raw = this.tagInput();
    const lastComma = raw.lastIndexOf(',');
    const prefix = lastComma === -1 ? '' : raw.slice(0, lastComma + 1) + ' ';
    this.tagInput.set(prefix + name);
    this.applyTags();
  }

  protected applyTags(): void {
    const raw = this.tagInput().trim();
    if (raw) {
      const tags = raw.split(',').map((tag: string) => tag.trim()).filter(Boolean);
      this.tagAction.emit({ add: tags, remove: [] });
    }
    this.tagInput.set('');
    this.showTagInput.set(false);
  }

  protected onTagKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.applyTags();
    } else if (event.key === 'Escape') {
      this.showTagInput.set(false);
      this.tagInput.set('');
    }
  }

  protected toggleAlbumMenu(): void {
    this.showAlbumMenu.update((open: boolean) => !open);
  }

  protected pickAlbum(collectionId: number): void {
    this.addToAlbum.emit(collectionId);
    this.showAlbumMenu.set(false);
  }

  protected toggleTrainingSetMenu(): void {
    this.showTrainingSetMenu.update((open: boolean) => !open);
  }

  protected pickTrainingSet(collectionId: number): void {
    this.addToTrainingSet.emit(collectionId);
    this.showTrainingSetMenu.set(false);
  }

  protected openRerunDialog(): void {
    this.rerunAction.emit();
  }

  protected openEditDialog(): void {
    this.editAction.emit();
  }

  protected triggerUpscale(): void {
    this.upscaleAction.emit();
  }

  protected onClose(): void {
    this.close.emit();
  }

  protected triggerDupeScan(): void {
    this.dupeScanAction.emit();
  }

  protected moveToTrash(): void {
    this.trashAction.emit();
  }
}
