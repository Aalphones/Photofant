import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { DatePipe } from '@angular/common';
import { maintenanceActions, maintenanceSelectors } from '@photofant/store';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe],
  template: `
    <div class="settings-layout">
      <div class="settings-section">
        <h2 class="settings-heading">Backup</h2>

        <div class="settings-card">
          <div class="card-row">
            <div>
              <div class="card-label">Datenbank-Backup</div>
              <div class="card-desc">
                Erstellt einen konsistenten Snapshot via SQLite Online Backup API.
                Ziel: <code>.photofant/backups/</code>
              </div>
            </div>
            <button
              class="btn-primary"
              [disabled]="isRunningBackup()"
              (click)="triggerBackup()"
            >
              @if (isRunningBackup()) {
                <span class="spinner"></span>
                Läuft…
              } @else {
                Backup erstellen
              }
            </button>
          </div>

          @if (error()) {
            <div class="error-banner">{{ error() }}</div>
          }
        </div>

        <div class="settings-card">
          <div class="backups-header">
            <span class="card-label">Vorhandene Backups</span>
            <button class="btn-ghost" (click)="refreshBackups()">Aktualisieren</button>
          </div>

          @if (isLoadingBackups()) {
            <div class="backups-loading">
              <span class="spinner"></span>
              <span>Lade…</span>
            </div>
          } @else if (backups().length === 0) {
            <p class="backups-empty">Noch kein Backup vorhanden.</p>
          } @else {
            <ul class="backups-list">
              @for (backup of backups(); track backup.filename) {
                <li class="backup-row">
                  <span class="backup-name">{{ backup.filename }}</span>
                  <span class="backup-meta">
                    {{ formatSize(backup.size) }} &nbsp;·&nbsp;
                    {{ backup.created_at | date:'dd.MM.yyyy HH:mm' }}
                  </span>
                </li>
              }
            </ul>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; overflow-y: auto; }

    .settings-layout {
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 24px;
    }

    .settings-heading {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-3);
      text-transform: uppercase;
      letter-spacing: .06em;
      margin: 0 0 12px;
    }

    .settings-section { display: flex; flex-direction: column; gap: 12px; }

    .settings-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .card-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .card-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 4px;
    }

    .card-desc {
      font-size: 12px;
      color: var(--text-3);
      line-height: 1.5;
    }

    code {
      font-family: var(--mono);
      font-size: 11px;
      background: var(--bg);
      padding: 1px 5px;
      border-radius: 4px;
      color: var(--accent);
    }

    .btn-primary {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      background: var(--accent);
      color: var(--bg);
      border-radius: var(--radius-s);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
      flex-shrink: 0;
      transition: background .12s, opacity .12s;
    }

    .btn-primary:hover:not(:disabled) { background: var(--accent-press); }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }

    .btn-ghost {
      font-size: 12px;
      color: var(--text-3);
      padding: 4px 8px;
      border-radius: var(--radius-s);
      transition: background .12s, color .12s;
    }

    .btn-ghost:hover { background: var(--surface-hover); color: var(--text); }

    .error-banner {
      font-size: 12px;
      color: var(--danger);
      background: var(--danger-weak);
      border-radius: var(--radius-s);
      padding: 8px 12px;
    }

    .backups-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .backups-loading {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-3);
    }

    .backups-empty {
      font-size: 13px;
      color: var(--text-3);
      margin: 0;
    }

    .backups-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .backup-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      border-radius: var(--radius-s);
      background: var(--bg-2);
      gap: 12px;
    }

    .backup-name {
      font-family: var(--mono);
      font-size: 12px;
      color: var(--text-2);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .backup-meta {
      font-size: 11px;
      color: var(--text-3);
      white-space: nowrap;
      flex-shrink: 0;
    }

    .spinner {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      border: 2px solid var(--line-2);
      border-top-color: currentColor;
      animation: pf-spin .8s linear infinite;
      flex-shrink: 0;
    }
  `],
})
export class Einstellungen {
  private readonly store = inject(Store);

  readonly backups = this.store.selectSignal(maintenanceSelectors.selectBackups);
  readonly isLoadingBackups = this.store.selectSignal(maintenanceSelectors.selectIsLoadingBackups);
  readonly isRunningBackup = this.store.selectSignal(maintenanceSelectors.selectIsRunningBackup);
  readonly error = this.store.selectSignal(maintenanceSelectors.selectError);

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadBackups());
    });
  }

  triggerBackup(): void {
    this.store.dispatch(maintenanceActions.triggerBackup({ targetDir: null }));
  }

  refreshBackups(): void {
    this.store.dispatch(maintenanceActions.loadBackups());
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
