import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Store } from '@ngrx/store';
import { maintenanceActions, maintenanceSelectors, personsActions, personsSelectors } from '@photofant/store';

@Component({
  selector: 'pf-einstellungen-backup-wartung',
  imports: [DatePipe],
  templateUrl: './backup-wartung.html',
  styleUrl: './backup-wartung.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BackupWartung {
  private readonly store = inject(Store);

  readonly backups = this.store.selectSignal(maintenanceSelectors.selectBackups);
  readonly isLoadingBackups = this.store.selectSignal(maintenanceSelectors.selectIsLoadingBackups);
  readonly isRunningBackup = this.store.selectSignal(maintenanceSelectors.selectIsRunningBackup);
  readonly error = this.store.selectSignal(maintenanceSelectors.selectError);
  readonly isClustering = this.store.selectSignal(personsSelectors.selectIsClustering);

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadBackups());
    });
  }

  triggerBackup(): void {
    this.store.dispatch(maintenanceActions.triggerBackup({ targetDir: null }));
  }

  triggerClustering(): void {
    this.store.dispatch(personsActions.triggerClustering());
  }

  refreshBackups(): void {
    this.store.dispatch(maintenanceActions.loadBackups());
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) { return `${bytes} B`; }
    if (bytes < 1024 * 1024) { return `${(bytes / 1024).toFixed(1)} KB`; }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
