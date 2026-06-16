import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import { DatePipe } from '@angular/common';
import type {
  DriftFile,
  IssueKind,
  MissingFile,
  OrphanFile,
  RepairActionKind,
  RepairItem,
} from '@photofant/models';
import { maintenanceActions, maintenanceSelectors } from '@photofant/store';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe],
  template: `
    <div class="settings-layout">
      <div class="settings-section">
        <h2 class="settings-heading">Backup &amp; Wartung</h2>

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

      <div class="settings-section">
        <h2 class="settings-heading">FS&#8596;DB-Abgleich</h2>

        <div class="settings-card">
          <div class="card-row">
            <div>
              <div class="card-label">Dateisystem mit Datenbank abgleichen</div>
              <div class="card-desc">
                Findet verwaiste Dateien (auf der Platte, nicht in der DB),
                fehlende Dateien (in der DB, nicht auf der Platte) und Pfad-Drift
                nach manuellen Verschiebungen.
              </div>
            </div>
            <button class="btn-primary" [disabled]="isScanning()" (click)="triggerReconcile()">
              @if (isScanning()) {
                <span class="spinner"></span>
                Scan läuft…
              } @else {
                Scan starten
              }
            </button>
          </div>

          @if (error()) {
            <div class="error-banner">{{ error() }}</div>
          }

          @if (report(); as rep) {
            @if (rep.generated_at) {
              <div class="scan-status">
                Letzter Scan: {{ rep.generated_at | date:'dd.MM.yyyy HH:mm' }} ·
                @if (issueTotal() === 0) {
                  <span class="status-good">Alles konsistent</span>
                } @else {
                  <span class="status-warn">{{ issueTotal() }} Abweichung(en)</span>
                }
              </div>
            }

            @if (issueTotal() > 0) {
              <div class="rec-tabs">
                <button class="rec-tab" [class.on]="activeTab() === 'orphan'" (click)="setTab('orphan')">
                  Verwaist <span class="tab-badge">{{ rep.orphaned_files.length }}</span>
                </button>
                <button class="rec-tab" [class.on]="activeTab() === 'missing'" (click)="setTab('missing')">
                  Fehlend <span class="tab-badge err">{{ rep.missing_files.length }}</span>
                </button>
                <button class="rec-tab" [class.on]="activeTab() === 'drift'" (click)="setTab('drift')">
                  Pfad-Drift <span class="tab-badge">{{ rep.path_drift.length }}</span>
                </button>
              </div>

              <div class="rec-issues">
                @switch (activeTab()) {
                  @case ('orphan') {
                    @for (orphan of rep.orphaned_files; track orphan.path) {
                      <div class="rec-issue">
                        <div class="ri-body">
                          <div class="ri-path">{{ orphan.path }}</div>
                          <div class="ri-meta">
                            <span class="rec-badge orphan">Verwaist</span>
                            <span>{{ formatSize(orphan.size) }}</span>
                            <span>{{ orphan.detail }}</span>
                          </div>
                        </div>
                        <div class="ri-acts">
                          <button class="btn-ghost-sm" [disabled]="isRepairing()" (click)="indexOrphan(orphan)">Indizieren</button>
                          <button class="btn-danger-sm" [disabled]="isRepairing()" (click)="trashOrphan(orphan)">Papierkorb</button>
                        </div>
                      </div>
                    } @empty {
                      <p class="rec-empty">Keine verwaisten Dateien.</p>
                    }
                  }
                  @case ('missing') {
                    @for (missing of rep.missing_files; track missing.instance_id) {
                      <div class="rec-issue">
                        <div class="ri-body">
                          <div class="ri-path">{{ missing.path }}</div>
                          <div class="ri-meta">
                            <span class="rec-badge missing">Fehlend</span>
                            <span>{{ missing.person_name ?? '_unknown' }}</span>
                            <span>{{ missing.detail }}</span>
                          </div>
                        </div>
                        <div class="ri-acts">
                          <button class="btn-ghost-sm" [disabled]="isRepairing()" (click)="markMissing(missing)">Als fehlend markieren</button>
                          <button class="btn-danger-sm" [disabled]="isRepairing()" (click)="trashMissing(missing)">DB-Eintrag löschen</button>
                        </div>
                      </div>
                    } @empty {
                      <p class="rec-empty">Keine fehlenden Dateien.</p>
                    }
                  }
                  @case ('drift') {
                    @for (drift of rep.path_drift; track drift.instance_id) {
                      <div class="rec-issue">
                        <div class="ri-body">
                          <div class="ri-path">{{ drift.found_path }}</div>
                          <div class="ri-meta">
                            <span class="rec-badge drift">Pfad-Drift</span>
                            <span>{{ drift.person_name ?? '_unknown' }}</span>
                            <span>DB: {{ drift.db_path }}</span>
                          </div>
                        </div>
                        <div class="ri-acts">
                          <button class="btn-ghost-sm" [disabled]="isRepairing()" (click)="fixDrift(drift)">Pfad korrigieren</button>
                        </div>
                      </div>
                    } @empty {
                      <p class="rec-empty">Kein Pfad-Drift.</p>
                    }
                  }
                }
              </div>
            }
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

    .scan-status {
      font-size: 12px;
      color: var(--text-3);
    }

    .status-good { color: var(--good); font-weight: 600; }
    .status-warn { color: var(--warn); font-weight: 600; }

    .rec-tabs {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--line);
    }

    .rec-tab {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-3);
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      transition: color .12s, border-color .12s;
    }

    .rec-tab:hover { color: var(--text-2); }
    .rec-tab.on { color: var(--text); border-bottom-color: var(--accent); }

    .tab-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 999px;
      background: var(--surface-2);
      color: var(--text-2);
    }

    .tab-badge.err { background: var(--danger-weak); color: var(--danger); }

    .rec-issues {
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .rec-issue {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px;
      border-radius: var(--radius-s);
      background: var(--bg-2);
    }

    .ri-body { min-width: 0; flex: 1; }

    .ri-path {
      font-family: var(--mono);
      font-size: 12px;
      color: var(--text-2);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .ri-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
      font-size: 11px;
      color: var(--text-3);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .rec-badge {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .04em;
      padding: 1px 6px;
      border-radius: 4px;
      flex-shrink: 0;
    }

    .rec-badge.orphan  { background: color-mix(in oklch, var(--warn) 18%, transparent); color: var(--warn); }
    .rec-badge.missing { background: var(--danger-weak); color: var(--danger); }
    .rec-badge.drift   { background: var(--accent-weak); color: var(--accent); }

    .ri-acts {
      display: flex;
      gap: 6px;
      flex-shrink: 0;
    }

    .btn-ghost-sm, .btn-danger-sm {
      font-size: 12px;
      font-weight: 600;
      padding: 5px 10px;
      border-radius: var(--radius-s);
      white-space: nowrap;
      transition: background .12s, color .12s, opacity .12s;
    }

    .btn-ghost-sm { color: var(--text-2); background: var(--surface); }
    .btn-ghost-sm:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }

    .btn-danger-sm { color: var(--danger); background: var(--danger-weak); }
    .btn-danger-sm:hover:not(:disabled) { background: color-mix(in oklch, var(--danger) 28%, transparent); }

    .btn-ghost-sm:disabled, .btn-danger-sm:disabled { opacity: .5; cursor: not-allowed; }

    .rec-empty {
      font-size: 13px;
      color: var(--text-3);
      margin: 0;
      padding: 8px 2px;
    }
  `],
})
export class Einstellungen {
  private readonly store = inject(Store);

  readonly backups = this.store.selectSignal(maintenanceSelectors.selectBackups);
  readonly isLoadingBackups = this.store.selectSignal(maintenanceSelectors.selectIsLoadingBackups);
  readonly isRunningBackup = this.store.selectSignal(maintenanceSelectors.selectIsRunningBackup);
  readonly report = this.store.selectSignal(maintenanceSelectors.selectReport);
  readonly isScanning = this.store.selectSignal(maintenanceSelectors.selectIsScanning);
  readonly isRepairing = this.store.selectSignal(maintenanceSelectors.selectIsRepairing);
  readonly error = this.store.selectSignal(maintenanceSelectors.selectError);

  readonly activeTab = signal<IssueKind>('orphan');
  readonly issueTotal = computed((): number => {
    const currentReport = this.report();
    if (!currentReport) {
      return 0;
    }
    return (
      currentReport.orphaned_files.length +
      currentReport.missing_files.length +
      currentReport.path_drift.length
    );
  });

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadBackups());
      this.store.dispatch(maintenanceActions.loadReport());
    });
  }

  triggerBackup(): void {
    this.store.dispatch(maintenanceActions.triggerBackup({ targetDir: null }));
  }

  refreshBackups(): void {
    this.store.dispatch(maintenanceActions.loadBackups());
  }

  triggerReconcile(): void {
    this.store.dispatch(maintenanceActions.triggerReconcile());
  }

  setTab(tab: IssueKind): void {
    this.activeTab.set(tab);
  }

  indexOrphan(orphan: OrphanFile): void {
    this.dispatchRepair({ kind: 'orphan', path: orphan.path }, 'index');
  }

  trashOrphan(orphan: OrphanFile): void {
    this.dispatchRepair({ kind: 'orphan', path: orphan.path }, 'trash');
  }

  markMissing(missing: MissingFile): void {
    this.dispatchRepair({ kind: 'missing', instance_id: missing.instance_id }, 'mark_missing');
  }

  trashMissing(missing: MissingFile): void {
    this.dispatchRepair({ kind: 'missing', instance_id: missing.instance_id }, 'trash');
  }

  fixDrift(drift: DriftFile): void {
    this.dispatchRepair(
      { kind: 'drift', instance_id: drift.instance_id, found_path: drift.found_path },
      'fix_path',
    );
  }

  private dispatchRepair(item: RepairItem, action: RepairActionKind): void {
    this.store.dispatch(maintenanceActions.repair({ actions: [{ item, action }] }));
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
