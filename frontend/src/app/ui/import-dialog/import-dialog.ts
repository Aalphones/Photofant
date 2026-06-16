import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  input,
  OnInit,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AssetService } from '../../services/asset.service';
import { Icon } from '../icon/icon';

export type ImportMode = 'path' | 'upload';

@Component({
  selector: 'pf-import-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, Icon],
  templateUrl: './import-dialog.html',
  styleUrl: './import-dialog.scss',
})
export class ImportDialog implements OnInit {
  private readonly assetService = inject(AssetService);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  readonly initialFiles = input<File[]>([]);
  readonly close = output<void>();
  readonly imported = output<string>();

  protected readonly mode = signal<ImportMode>('path');
  protected readonly pathInput = signal('');
  protected readonly files = signal<File[]>([]);
  protected readonly isDragging = signal(false);
  protected readonly isLoading = signal(false);
  protected readonly errorMsg = signal<string | null>(null);

  private dragDepth = 0;
  private readonly fileInputRef = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  ngOnInit(): void {
    const initial = this.initialFiles();
    if (initial.length > 0) {
      this.files.set([...initial]);
      this.mode.set('upload');
    }

    const handler = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') this.onClose();
    };
    this.document.addEventListener('keydown', handler);
    this.destroyRef.onDestroy(() => this.document.removeEventListener('keydown', handler));
  }

  protected setMode(mode: ImportMode): void {
    this.mode.set(mode);
    this.errorMsg.set(null);
  }

  protected onClose(): void {
    this.close.emit();
  }

  protected openFilePicker(): void {
    this.fileInputRef()?.nativeElement.click();
  }

  protected onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.files.update((current: File[]) => [...current, ...Array.from(input.files!)]);
    }
    input.value = '';
  }

  protected removeFile(index: number): void {
    this.files.update((current: File[]) => current.filter((_: File, i: number) => i !== index));
  }

  protected onDragEnter(event: DragEvent): void {
    event.preventDefault();
    this.dragDepth++;
    this.isDragging.set(true);
  }

  protected onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.dragDepth--;
    if (this.dragDepth <= 0) {
      this.dragDepth = 0;
      this.isDragging.set(false);
    }
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragDepth = 0;
    this.isDragging.set(false);
    const dropped = event.dataTransfer?.files;
    if (dropped && dropped.length > 0) {
      const images = Array.from(dropped).filter((file: File) =>
        file.type.startsWith('image/')
      );
      if (images.length > 0) {
        this.files.update((current: File[]) => [...current, ...images]);
        this.mode.set('upload');
      }
    }
  }

  protected canSubmit(): boolean {
    if (this.isLoading()) return false;
    if (this.mode() === 'path') return this.pathInput().trim().length > 0;
    return this.files().length > 0;
  }

  protected submit(): void {
    this.errorMsg.set(null);
    this.isLoading.set(true);

    const request$ = this.mode() === 'path'
      ? this.assetService.importPaths(this.parsePaths())
      : this.assetService.uploadFiles(this.files());

    request$.subscribe({
      next: (response: { job_id: string }) => {
        this.isLoading.set(false);
        this.imported.emit(response.job_id);
        this.close.emit();
      },
      error: () => {
        this.isLoading.set(false);
        this.errorMsg.set('Import fehlgeschlagen. Backend erreichbar?');
      },
    });
  }

  private parsePaths(): string[] {
    return this.pathInput()
      .split('\n')
      .map((line: string) => line.trim())
      .filter((line: string) => line.length > 0);
  }

  protected formatSize(bytes: number): string {
    if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(1) + ' MB';
    if (bytes >= 1_024) return Math.round(bytes / 1_024) + ' KB';
    return bytes + ' B';
  }
}
