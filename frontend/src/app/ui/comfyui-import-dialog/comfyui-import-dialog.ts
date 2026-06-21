import { ChangeDetectionStrategy, Component, inject, input, OnInit, output, signal } from '@angular/core';
import type { ComfyUIImportResponse, ComfyUIResultItem } from '@photofant/models';
import { ComfyUIService } from '../../services/comfyui.service';
import { Icon } from '../icon/icon';

@Component({
  selector: 'pf-comfyui-import-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './comfyui-import-dialog.html',
  styleUrl: './comfyui-import-dialog.scss',
})
export class ComfyuiImportDialog implements OnInit {
  private readonly comfyuiService = inject(ComfyUIService);

  readonly assetId = input.required<number>();
  readonly promptId = input<string | undefined>(undefined);

  readonly close = output<void>();
  readonly imported = output<ComfyUIImportResponse>();

  protected readonly results = signal<ComfyUIResultItem[]>([]);
  protected readonly selectedItem = signal<ComfyUIResultItem | null>(null);
  protected readonly isLoading = signal(true);
  protected readonly isImporting = signal(false);
  protected readonly errorMsg = signal<string | null>(null);
  protected readonly importError = signal<string | null>(null);

  ngOnInit(): void {
    this.comfyuiService.listResults(this.promptId()).subscribe({
      next: (response) => {
        this.results.set(response.items);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMsg.set('ComfyUI-Ergebnisse konnten nicht geladen werden.');
        this.isLoading.set(false);
      },
    });
  }

  protected previewUrl(item: ComfyUIResultItem): string {
    return this.comfyuiService.getResultViewUrl(item.filename, item.subfolder);
  }

  protected isSelected(item: ComfyUIResultItem): boolean {
    return this.selectedItem()?.filename === item.filename && this.selectedItem()?.subfolder === item.subfolder;
  }

  protected toggleSelect(item: ComfyUIResultItem): void {
    if (this.isSelected(item)) {
      this.selectedItem.set(null);
    } else {
      this.selectedItem.set(item);
    }
  }

  protected onClose(): void {
    this.close.emit();
  }

  protected onImport(): void {
    const item = this.selectedItem();
    if (!item || this.isImporting()) {
      return;
    }
    this.importError.set(null);
    this.isImporting.set(true);
    this.comfyuiService.importResult(this.assetId(), item.filename, item.subfolder).subscribe({
      next: (response: ComfyUIImportResponse) => {
        this.isImporting.set(false);
        this.imported.emit(response);
        this.close.emit();
      },
      error: () => {
        this.isImporting.set(false);
        this.importError.set('Import fehlgeschlagen. Datei noch im ComfyUI-Output vorhanden?');
      },
    });
  }
}
