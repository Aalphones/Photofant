import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';

export interface FaceBulkTrainingSetOption {
  id: number;
  name: string;
}

@Component({
  selector: 'pf-face-bulk-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './face-bulk-bar.html',
  styleUrl: './face-bulk-bar.scss',
})
export class FaceBulkBar {
  readonly count        = input.required<number>();
  readonly trainingSets = input<FaceBulkTrainingSetOption[]>([]);
  readonly canUpscale   = input<boolean>(false);

  readonly close            = output<void>();
  readonly deleteAction     = output<void>();
  readonly upscaleAction    = output<void>();
  readonly addToTrainingSet = output<number>();

  protected readonly showTrainingSetMenu = signal(false);

  protected readonly countLabel = computed((): string => {
    const n = this.count();
    return n === 1 ? '1 Gesicht ausgewählt' : `${n} Gesichter ausgewählt`;
  });

  protected toggleTrainingSetMenu(): void {
    this.showTrainingSetMenu.update((open: boolean) => !open);
  }

  protected pickTrainingSet(collectionId: number): void {
    this.addToTrainingSet.emit(collectionId);
    this.showTrainingSetMenu.set(false);
  }

  protected triggerUpscale(): void {
    this.upscaleAction.emit();
  }

  protected triggerDelete(): void {
    // Face-Löschen ist endgültig (kein Papierkorb/Undo wie bei Assets, siehe
    // person.service.ts::bulkDeleteFaces) — deshalb eine native Sicherheitsabfrage,
    // anders als der Asset-Bulk-Bar-Trash-Button (der landet zuerst im Papierkorb).
    const label = this.count() === 1 ? 'Dieses Gesicht' : `Diese ${this.count()} Gesichter`;
    if (window.confirm(`${label} endgültig löschen? Das kann nicht rückgängig gemacht werden.`)) {
      this.deleteAction.emit();
    }
  }

  protected onClose(): void {
    this.close.emit();
  }
}
