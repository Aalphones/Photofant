import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import type { Collection } from '@photofant/models';
import type { ExportFilterParams } from '@photofant/services';
import { ExportService } from '@photofant/services';
import { Icon } from '../icon/icon';

export interface ExportDialogFilters {
  sources: string[];
  qualityMin: number;
  tagIds: number[];
  personId: number | null;
  favourite: boolean | null;
}

@Component({
  selector: 'pf-export-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './export-dialog.html',
  styleUrl: './export-dialog.scss',
})
export class ExportDialog {
  private readonly exportService = inject(ExportService);
  private readonly destroyRef    = inject(DestroyRef);

  readonly filters = input.required<ExportDialogFilters>();
  readonly albums  = input<Collection[]>([]);
  readonly close   = output<void>();

  protected readonly toast        = signal<string | null>(null);
  protected readonly isBusy       = signal(false);
  protected includeVersions       = false;
  protected randomCount           = 5;
  protected randomImages          = 100;
  protected targetDir             = '';
  protected selectedAlbumId: number | null = null;

  private toastTimer: ReturnType<typeof setTimeout> | null = null;

  protected handleScrimClick(): void {
    this.close.emit();
  }

  protected onReveal(): void {
    this.exportService.revealExportFolder()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ error: () => this.showToast('Ordner konnte nicht geöffnet werden.') });
  }

  protected onExportFilter(): void {
    const filters = this.filters();
    const params: ExportFilterParams = {
      include_versions: this.includeVersions,
      favourite: filters.favourite,
    };
    if (filters.sources.length)  { params.sources = filters.sources; }
    if (filters.qualityMin > 0)  { params.quality_min = filters.qualityMin; }
    if (filters.tagIds.length)   { params.tag_ids = filters.tagIds; }
    if (filters.personId != null){ params.person_id = filters.personId; }
    if (this.targetDir.trim())   { params.target_dir = this.targetDir.trim(); }

    this.triggerJob(this.exportService.exportFavouritesFilter(params));
  }

  protected onExportByPerson(): void {
    this.triggerJob(this.exportService.exportFavouritesByPerson(this.targetDir.trim() || undefined));
  }

  protected onExportRandom(): void {
    this.triggerJob(this.exportService.exportFavouritesRandom({
      count: this.randomCount,
      images_per_set: this.randomImages,
      ...(this.targetDir.trim() ? { target_dir: this.targetDir.trim() } : {}),
    }));
  }

  protected onExportAlbum(): void {
    if (this.selectedAlbumId == null) { return; }
    this.triggerJob(this.exportService.exportCollection(this.selectedAlbumId, {
      ...(this.targetDir.trim() ? { target_dir: this.targetDir.trim() } : {}),
    }));
  }

  private triggerJob(obs$: ReturnType<typeof this.exportService.exportFavouritesFilter>): void {
    if (this.isBusy()) { return; }
    this.isBusy.set(true);
    obs$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.isBusy.set(false);
        this.showToast('Export gestartet — läuft im Hintergrund.');
      },
      error: () => {
        this.isBusy.set(false);
        this.showToast('Fehler beim Starten des Exports.');
      },
    });
  }

  private showToast(message: string): void {
    if (this.toastTimer != null) { clearTimeout(this.toastTimer); }
    this.toast.set(message);
    this.toastTimer = setTimeout(() => { this.toast.set(null); }, 4000);
  }
}
