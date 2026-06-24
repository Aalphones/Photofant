import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
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
  selector: 'pf-wartung',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe],
  template: `
    <div class="wartung-layout">
      <header class="page-head">
        <h1 class="page-title">Wartung</h1>
        <p class="page-sub">Dateisystem-Abgleich, Cache-Rebuilds · keine Skripte nötig.</p>
      </header>

      <!-- Status-Leiste -->
      <div class="status-bar">
        <div class="stat">
          <div class="stat-label">Letzter FS&#8596;DB-Scan</div>
          @if (report()?.generated_at; as scannedAt) {
            <div class="stat-value muted">{{ scannedAt | date:'dd.MM.yyyy HH:mm' }}</div>
            <div class="stat-sub">
              @if (issueTotal() === 0) {
                <span class="ok">0 Abweichungen</span>
              } @else {
                <span class="warn">{{ issueTotal() }} Abweichung(en)</span>
              }
            </div>
          } @else {
            <div class="stat-value muted">Noch kein Scan</div>
            <div class="stat-sub">—</div>
          }
        </div>

        <div class="stat">
          <div class="stat-label">Datenbank</div>
          <div class="stat-value">{{ status() ? formatSize(status()!.db_size) : '—' }}</div>
          <div class="stat-sub">db.sqlite</div>
        </div>

        <div class="stat">
          <div class="stat-label">Thumbnails</div>
          <div class="stat-value">{{ status() ? status()!.thumbnail_count : '—' }}</div>
          <div class="stat-sub">{{ status() ? formatSize(status()!.cache_size) : 'thumbnails.sqlite' }}</div>
        </div>

        <div class="stat">
          <div class="stat-label">Face-Crops</div>
          <div class="stat-value muted">—</div>
          <div class="stat-sub">ab P7</div>
        </div>
      </div>

      <!-- Cache & Thumbnails -->
      <section class="section">
        <h2 class="section-heading">Cache &amp; Thumbnails</h2>

        <div class="card">
          <div class="card-row">
            <div>
              <div class="card-label">Fehlende Thumbnails ergänzen</div>
              <div class="card-desc">
                Generiert fehlende Größen (256 / 512 / 1024 px) für bestehende Bilder additiv —
                löscht nichts, überspringt bereits vorhandene Einträge. Einmaliger Lauf nach
                dem Update auf dreifache Thumbnail-Größen.
              </div>
            </div>
            <button
              class="btn-primary"
              [disabled]="isThumbnailRebuilding()"
              (click)="startThumbnailRebuild()"
            >
              @if (isThumbnailRebuilding()) {
                <span class="spinner"></span>
                Läuft…
              } @else {
                Thumbnails neu generieren
              }
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-row">
            <div>
              <div class="card-label">Thumbnails vollständig neu aufbauen</div>
              <div class="card-desc">
                Baut <code>thumbnails.sqlite</code> vollständig aus den vorhandenen
                Bilddateien neu auf. Gefahrlos — Originale werden nie verändert, ein
                Abbruch erzeugt keinen Schaden (fehlende Thumbnails entstehen bei Bedarf neu).
              </div>
            </div>
            <button
              class="btn-primary"
              [disabled]="rebuildingTarget() !== null"
              (click)="rebuildThumbnails()"
            >
              @if (rebuildingTarget() === 'thumbnails') {
                <span class="spinner"></span>
                Läuft…
              } @else {
                Alles rebuilden
              }
            </button>
          </div>
          <p class="card-hint">Weitere Rebuilds (Face-Crops) folgen mit P7. Fortschritt läuft im Job-Dock.</p>
        </div>
      </section>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; overflow-y: auto; }

    .wartung-layout {
      max-width: 760px;
      margin: 0 auto;
      padding: 32px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .page-head { display: flex; flex-direction: column; gap: 4px; }
    .page-title { font-size: 20px; font-weight: 700; color: var(--text); margin: 0; }
    .page-sub { font-size: 13px; color: var(--text-3); margin: 0; }

    .status-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }

    @media (max-width: 640px) {
      .status-bar { grid-template-columns: repeat(2, 1fr); }
    }

    .stat {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 3px;
      min-width: 0;
    }

    .stat-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-3);
      text-transform: uppercase;
      letter-spacing: .05em;
    }

    .stat-value {
      font-size: 18px;
      font-weight: 700;
      color: var(--text);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .stat-value.muted { color: var(--text-2); font-weight: 600; font-size: 14px; }

    .stat-sub { font-size: 11px; color: var(--text-3); }
    .stat-sub .ok { color: var(--good); font-weight: 600; }
    .stat-sub .warn { color: var(--warn); font-weight: 600; }

    .section { display: flex; flex-direction: column; gap: 12px; }

    .section-heading {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-3);
      text-transform: uppercase;
      letter-spacing: .06em;
      margin: 0;
    }

    .card {
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

    .card-desc { font-size: 12px; color: var(--text-3); line-height: 1.5; }
    .card-hint { font-size: 11px; color: var(--text-3); margin: 0; }

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

    .error-banner {
      font-size: 12px;
      color: var(--danger);
      background: var(--danger-weak);
      border-radius: var(--radius-s);
      padding: 8px 12px;
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

    .scan-status { font-size: 12px; color: var(--text-3); }
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

    .rec-issues { display: flex; flex-direction: column; gap: 1px; }

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

    .ri-acts { display: flex; gap: 6px; flex-shrink: 0; }

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
export class Wartung {
  private readonly store = inject(Store);

  readonly report = this.store.selectSignal(maintenanceSelectors.selectReport);
  readonly isScanning = this.store.selectSignal(maintenanceSelectors.selectIsScanning);
  readonly isRepairing = this.store.selectSignal(maintenanceSelectors.selectIsRepairing);
  readonly rebuildingTarget = this.store.selectSignal(maintenanceSelectors.selectRebuildingTarget);
  readonly isThumbnailRebuilding = this.store.selectSignal(maintenanceSelectors.selectIsThumbnailRebuilding);
  readonly status = this.store.selectSignal(maintenanceSelectors.selectStatus);
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
      this.store.dispatch(maintenanceActions.loadReport());
      this.store.dispatch(maintenanceActions.loadStatus());
    });
  }

  triggerReconcile(): void {
    this.store.dispatch(maintenanceActions.triggerReconcile());
  }

  startThumbnailRebuild(): void {
    this.store.dispatch(maintenanceActions.triggerThumbnailRebuild());
  }

  rebuildThumbnails(): void {
    this.store.dispatch(maintenanceActions.triggerRebuild({ target: 'thumbnails' }));
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
