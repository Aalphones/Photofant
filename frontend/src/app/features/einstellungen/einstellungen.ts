import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { CapabilityDescriptor, CaptionPresetDto, Density, ModelDto, ProcessingConfig } from '@photofant/models';
import type { DateFormat, Locale } from '@photofant/services';
import { SettingsService } from '@photofant/services';
import {
  filtersActions,
  filtersSelectors,
  maintenanceActions,
  maintenanceSelectors,
  modelsActions,
  modelsSelectors,
  presetsActions,
  presetsSelectors,
} from '@photofant/store';
import type { PresetSavePayload } from '@photofant/ui';
import { PresetDialog } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, PresetDialog],
  template: `
    <div class="settings-layout">

      <!-- ── Darstellung ──────────────────────────────────────────── -->
      <div class="settings-section">
        <h2 class="settings-heading">Darstellung</h2>

        <div class="settings-card">
          <p class="settings-group-label">Galerie</p>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Metadaten unter Bild anzeigen</div>
              <div class="card-desc">Zeigt Quelle und Tags unter jedem Bild im Raster.</div>
            </div>
            <button
              class="st-switch"
              [class.st-switch--on]="displaySettings().showMeta"
              role="switch"
              [attr.aria-checked]="displaySettings().showMeta"
              (click)="setShowMeta(!displaySettings().showMeta)"
            ></button>
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Animations-Effekte reduzieren</div>
              <div class="card-desc">Deaktiviert Überblend- und Slide-Animationen.</div>
            </div>
            <button
              class="st-switch"
              [class.st-switch--on]="displaySettings().reducedMotion"
              role="switch"
              [attr.aria-checked]="displaySettings().reducedMotion"
              (click)="setReducedMotion(!displaySettings().reducedMotion)"
            ></button>
          </div>
        </div>

        <div class="settings-card">
          <p class="settings-group-label">Sprache & Region</p>

          <div class="card-row card-row--top">
            <div class="card-label">Sprache</div>
            <select
              class="st-select"
              [value]="displaySettings().locale"
              (change)="setLocale($any($event.target).value)"
            >
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
          </div>

          <div class="card-row card-row--top">
            <div class="card-label">Datumsformat</div>
            <select
              class="st-select"
              [value]="displaySettings().dateFormat"
              (change)="setDateFormat($any($event.target).value)"
            >
              <option value="dmy">TT.MM.JJJJ</option>
              <option value="ymd">JJJJ-MM-TT</option>
              <option value="mdy">MM/DD/YYYY</option>
            </select>
          </div>
        </div>
      </div>

      <!-- ── Bibliothek ─────────────────────────────────────────────── -->
      <div class="settings-section">
        <h2 class="settings-heading">Bibliothek</h2>

        @if (rebootRequired()) {
          <div class="reboot-banner">
            🟡 Neustart erforderlich — die neue Bibliothek wird erst nach dem Neustart der App verwendet.
          </div>
        }

        <div class="settings-card">
          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Sammlungs-Ordner</div>
              <div class="card-desc">
                Hauptverzeichnis für alle Bilder und die Datenbank.
                Bilder und Datenbank müssen manuell in den neuen Ordner kopiert werden.
              </div>
            </div>
            @if (!isDataRootEditing()) {
              <div class="path-display">
                <code>{{ dataRoot() ?? '–' }}</code>
                <button class="btn-ghost" (click)="startDataRootEdit()">Ändern</button>
              </div>
            } @else {
              <div class="path-edit">
                <input
                  class="dir-input"
                  type="text"
                  [value]="pendingDataRoot()"
                  (input)="pendingDataRoot.set($any($event.target).value)"
                  (keydown.enter)="saveDataRootEdit()"
                  (keydown.escape)="cancelDataRootEdit()"
                />
                <button class="btn-primary" (click)="saveDataRootEdit()">Speichern</button>
                <button class="btn-ghost" (click)="cancelDataRootEdit()">Abbrechen</button>
              </div>
            }
          </div>
        </div>

        <div class="settings-card">
          <div class="card-row">
            <div>
              <div class="card-label">Modell-Ordner</div>
              <div class="card-desc">
                Zielverzeichnis für neue Downloads. Bestehende Pfade bleiben bei Änderung erhalten.
              </div>
            </div>
            @if (!isDirEditing()) {
              <div class="path-display">
                <code>{{ modelsDir() ?? '–' }}</code>
                <button class="btn-ghost" (click)="startDirEdit()">Ändern</button>
              </div>
            } @else {
              <div class="path-edit">
                <input
                  class="dir-input"
                  type="text"
                  [value]="pendingDir()"
                  (input)="pendingDir.set($any($event.target).value)"
                  (keydown.enter)="saveDirEdit()"
                  (keydown.escape)="cancelDirEdit()"
                />
                <button class="btn-primary" (click)="saveDirEdit()">Speichern</button>
                <button class="btn-ghost" (click)="cancelDirEdit()">Abbrechen</button>
              </div>
            }
          </div>
        </div>
      </div>

      <!-- ── Verarbeitung ─────────────────────────────────────────────── -->
      <div class="settings-section">
        <h2 class="settings-heading">Verarbeitung</h2>

        <div class="settings-card">
          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Auto-Tagging (WD14)</div>
              <div class="card-desc">Beim Import automatisch WD14-Tags generieren.</div>
            </div>
            <button
              class="st-switch"
              [class.st-switch--on]="processingConfig().autoTag"
              role="switch"
              [attr.aria-checked]="processingConfig().autoTag"
              (click)="patchProcessingConfig({ autoTag: !processingConfig().autoTag })"
            ></button>
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Auto-Caption (Florence-2)</div>
              <div class="card-desc">Beim Import automatisch Bildbeschreibungen generieren.</div>
            </div>
            <button
              class="st-switch"
              [class.st-switch--on]="processingConfig().autoCaption"
              role="switch"
              [attr.aria-checked]="processingConfig().autoCaption"
              (click)="patchProcessingConfig({ autoCaption: !processingConfig().autoCaption })"
            ></button>
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">CLIP-Embedding</div>
              <div class="card-desc">Beim Import automatisch semantische Suchdaten berechnen.</div>
            </div>
            <button
              class="st-switch"
              [class.st-switch--on]="processingConfig().autoEmbed"
              role="switch"
              [attr.aria-checked]="processingConfig().autoEmbed"
              (click)="patchProcessingConfig({ autoEmbed: !processingConfig().autoEmbed })"
            ></button>
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Mindest-Konfidenz (WD14)</div>
              <div class="card-desc">Tags unterhalb dieses Wertes werden verworfen. Default: 0.5</div>
            </div>
            <input
              class="st-number-input"
              type="number"
              min="0"
              max="1"
              step="0.05"
              [value]="processingConfig().minProbability"
              (change)="onMinProbabilityChange($any($event.target))"
            >
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Max. Tags pro Bild</div>
              <div class="card-desc">Maximale Anzahl automatisch gesetzter Tags, nach Konfidenz sortiert. Default: 30</div>
            </div>
            <input
              class="st-number-input"
              type="number"
              min="1"
              max="200"
              [value]="processingConfig().maxTags"
              (change)="onMaxTagsChange($any($event.target))"
            >
          </div>

          <div class="card-row card-row--top">
            <div>
              <div class="card-label">Mindestschärfe (Laplacian-Varianz)</div>
              <div class="card-desc">Bilder unterhalb gelten als unscharf. Default: 200</div>
            </div>
            <input
              class="st-number-input"
              type="number"
              min="0"
              max="1000"
              step="10"
              [value]="processingConfig().blurThreshold"
              (change)="onBlurThresholdChange($any($event.target))"
            >
          </div>
        </div>
      </div>

      <!-- ── Captioner-Presets ──────────────────────────────────────── -->
      @if (captionerModel() != null) {
        <div class="settings-section">
          <h2 class="settings-heading">Caption-Presets</h2>

          <div class="settings-card">
            <div class="card-row">
              <div>
                <div class="card-label">Presets für {{ captionerModel()!.name }}</div>
                <div class="card-desc">
                  Benannte, wiederverwendbare Captioner-Konfigurationen. Beim Caption-Lauf wählt du Modell + Preset.
                </div>
              </div>
              <button class="btn-primary" (click)="openCreateDialog()">Neu</button>
            </div>

            @if (isLoadingPresets()) {
              <div class="presets-loading"><span class="spinner"></span> Lade…</div>
            } @else if (presets().length === 0) {
              <p class="presets-empty">Noch keine Presets vorhanden.</p>
            } @else {
              <ul class="presets-list">
                @for (preset of presets(); track preset.id) {
                  <li class="preset-row">
                    <div class="preset-info">
                      <span class="preset-name">{{ preset.name }}</span>
                      @if (preset.is_default) {
                        <span class="preset-badge">Standard</span>
                      }
                      <span class="preset-meta">{{ presetSummary(preset) }}</span>
                    </div>
                    <div class="preset-actions">
                      @if (!preset.is_default) {
                        <button class="btn-ghost" (click)="setDefault(preset)">Standard</button>
                      }
                      <button class="btn-ghost" (click)="openEditDialog(preset)">Bearbeiten</button>
                      <button class="btn-ghost btn-ghost--danger" (click)="deletePreset(preset)">Löschen</button>
                    </div>
                  </li>
                }
              </ul>
            }
          </div>
        </div>
      }

      <!-- ── Backup ────────────────────────────────────────────────── -->
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

    <!-- ── Preset-Dialog ────────────────────────────────────────────── -->
    @if (showPresetDialog() && captionerCapabilities() != null) {
      <pf-preset-dialog
        [capabilities]="captionerCapabilities()!"
        [preset]="editingPreset()"
        (save)="onPresetSave($event)"
        (cancel)="closePresetDialog()"
      />
    }
  `,
  styles: [`
    :host { display: block; height: 100%; overflow-y: auto; }

    .settings-layout {
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 24px;
      display: flex;
      flex-direction: column;
      gap: 32px;
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
    .btn-ghost--danger:hover { color: var(--danger); }

    .error-banner {
      font-size: 12px;
      color: var(--danger);
      background: var(--danger-weak);
      border-radius: var(--radius-s);
      padding: 8px 12px;
    }

    /* Presets */
    .presets-loading, .presets-empty {
      font-size: 13px;
      color: var(--text-3);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .presets-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .preset-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 9px 10px;
      border-radius: var(--radius-s);
      background: var(--bg-2);
    }

    .preset-info {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .preset-name {
      font-size: 13px;
      font-weight: 500;
      color: var(--text);
    }

    .preset-badge {
      font-size: 10px;
      font-weight: 600;
      background: var(--accent-dim);
      color: var(--accent);
      padding: 1px 6px;
      border-radius: 10px;
      flex-shrink: 0;
    }

    .preset-meta {
      font-size: 11px;
      color: var(--text-3);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .preset-actions {
      display: flex;
      gap: 4px;
      flex-shrink: 0;
    }

    /* Backups */
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

    .settings-group-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-3);
      text-transform: uppercase;
      letter-spacing: .1em;
      margin: 0 0 10px;
    }

    .card-row--top {
      align-items: flex-start;
      padding-top: 4px;
    }

    .st-select {
      height: 32px;
      padding: 0 26px 0 10px;
      background: var(--bg) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") no-repeat right 8px center;
      border: 1px solid var(--line);
      border-radius: var(--radius-s);
      color: var(--text);
      font-size: 13px;
      appearance: none;
      flex-shrink: 0;
      cursor: pointer;
      min-width: 130px;
    }

    .st-select:focus {
      outline: none;
      border-color: var(--accent-line);
      box-shadow: 0 0 0 3px var(--accent-weak);
    }

    /* Toggle-Switch */
    .st-switch {
      position: relative;
      width: 42px;
      height: 24px;
      border-radius: 12px;
      background: var(--line-2);
      flex-shrink: 0;
      transition: background .15s;
      cursor: pointer;
    }

    .st-switch::after {
      content: '';
      position: absolute;
      top: 3px;
      left: 3px;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: var(--text);
      transition: transform .15s;
    }

    .st-switch--on {
      background: var(--accent);
    }

    .st-switch--on::after {
      transform: translateX(18px);
    }

    .reboot-banner {
      font-size: 13px;
      color: var(--text-2);
      background: var(--warning-weak, color-mix(in srgb, var(--accent) 10%, transparent));
      border: 1px solid var(--warning-line, var(--line));
      border-radius: var(--radius-s);
      padding: 10px 14px;
    }

    .path-display {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .path-edit {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1;
      justify-content: flex-end;
    }

    .dir-input {
      height: 34px;
      padding: 0 10px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius-s);
      color: var(--text);
      font-family: var(--mono);
      font-size: 12px;
      outline: none;
      min-width: 0;
      width: 260px;
      flex-shrink: 1;
    }
    .dir-input:focus { border-color: var(--accent-line); box-shadow: 0 0 0 3px var(--accent-weak); }

    .st-number-input {
      height: 32px;
      width: 90px;
      padding: 0 8px;
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: var(--radius-s);
      color: var(--text);
      font-size: 13px;
      text-align: right;
      flex-shrink: 0;
    }
    .st-number-input:focus { outline: none; border-color: var(--accent-line); box-shadow: 0 0 0 3px var(--accent-weak); }

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
  private readonly settings = inject(SettingsService);

  /* ── Darstellung ──────────────────────────────────────────────── */
  readonly density = this.store.selectSignal(filtersSelectors.density);
  readonly displaySettings = this.settings.snapshot;

  setDensity(value: Density): void {
    this.store.dispatch(filtersActions.setDensity({ density: value }));
  }

  setShowMeta(value: boolean): void {
    this.settings.setShowMeta(value);
  }

  setReducedMotion(value: boolean): void {
    this.settings.setReducedMotion(value);
  }

  setLocale(value: Locale): void {
    this.settings.setLocale(value);
  }

  setDateFormat(value: DateFormat): void {
    this.settings.setDateFormat(value);
  }

  /* ── Bibliothek ───────────────────────────────────────────────── */
  readonly dataRoot = this.store.selectSignal(modelsSelectors.selectDataRoot);
  readonly rebootRequired = this.store.selectSignal(modelsSelectors.selectRebootRequired);
  readonly modelsDir = this.store.selectSignal(modelsSelectors.selectModelsDir);
  readonly processingConfig = this.store.selectSignal(modelsSelectors.selectProcessingConfig);
  readonly isDataRootEditing = signal<boolean>(false);
  readonly pendingDataRoot = signal<string>('');
  readonly isDirEditing = signal<boolean>(false);
  readonly pendingDir = signal<string>('');

  readonly backups = this.store.selectSignal(maintenanceSelectors.selectBackups);
  readonly isLoadingBackups = this.store.selectSignal(maintenanceSelectors.selectIsLoadingBackups);
  readonly isRunningBackup = this.store.selectSignal(maintenanceSelectors.selectIsRunningBackup);
  readonly error = this.store.selectSignal(maintenanceSelectors.selectError);

  readonly presets = this.store.selectSignal(presetsSelectors.selectPresets);
  readonly isLoadingPresets = this.store.selectSignal(presetsSelectors.selectIsLoading);

  readonly showPresetDialog = signal<boolean>(false);
  readonly editingPreset = signal<CaptionPresetDto | null>(null);

  readonly captionerModel = computed((): ModelDto | null => {
    const models = this.store.selectSignal(modelsSelectors.selectModels)();
    return models.find((model: ModelDto) => model.role === 'captioner' && (model.status === 'active' || model.status === 'inplace')) ?? null;
  });

  readonly captionerCapabilities = computed((): CapabilityDescriptor | null =>
    this.captionerModel()?.capabilities ?? null
  );

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadBackups());
      this.store.dispatch(modelsActions.loadConfig());
      this.store.dispatch(modelsActions.loadModels());
      this.store.dispatch(presetsActions.loadPresets());
    });
  }

  startDataRootEdit(): void {
    this.pendingDataRoot.set(this.dataRoot() ?? '');
    this.isDataRootEditing.set(true);
  }

  cancelDataRootEdit(): void {
    this.isDataRootEditing.set(false);
  }

  saveDataRootEdit(): void {
    const newPath = this.pendingDataRoot().trim();
    if (newPath.length > 0) {
      this.store.dispatch(modelsActions.updateDataRoot({ path: newPath }));
    }
    this.isDataRootEditing.set(false);
  }

  startDirEdit(): void {
    this.pendingDir.set(this.modelsDir() ?? '');
    this.isDirEditing.set(true);
  }

  cancelDirEdit(): void {
    this.isDirEditing.set(false);
  }

  saveDirEdit(): void {
    const newDir = this.pendingDir().trim();
    if (newDir.length > 0) {
      this.store.dispatch(modelsActions.updateModelsDir({ path: newDir }));
    }
    this.isDirEditing.set(false);
  }

  /* ── Verarbeitung ─────────────────────────────────────────────── */
  patchProcessingConfig(patch: Partial<ProcessingConfig>): void {
    this.store.dispatch(modelsActions.updateProcessingConfig({ patch }));
  }

  onMinProbabilityChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1, Math.max(0, isNaN(raw) ? 0.5 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ minProbability: clamped });
  }

  onMaxTagsChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(200, Math.max(1, isNaN(raw) ? 30 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ maxTags: clamped });
  }

  onBlurThresholdChange(target: HTMLInputElement): void {
    const raw = parseFloat(target.value);
    const clamped = Math.min(1000, Math.max(0, isNaN(raw) ? 200 : raw));
    target.value = String(clamped);
    this.patchProcessingConfig({ blurThreshold: clamped });
  }

  triggerBackup(): void {
    this.store.dispatch(maintenanceActions.triggerBackup({ targetDir: null }));
  }

  refreshBackups(): void {
    this.store.dispatch(maintenanceActions.loadBackups());
  }

  openCreateDialog(): void {
    this.editingPreset.set(null);
    this.showPresetDialog.set(true);
  }

  openEditDialog(preset: CaptionPresetDto): void {
    this.editingPreset.set(preset);
    this.showPresetDialog.set(true);
  }

  closePresetDialog(): void {
    this.showPresetDialog.set(false);
    this.editingPreset.set(null);
  }

  onPresetSave(payload: PresetSavePayload): void {
    const editing = this.editingPreset();
    if (editing != null) {
      this.store.dispatch(presetsActions.updatePreset({
        id: editing.id,
        body: { name: payload.name, config: payload.config, is_default: payload.isDefault },
      }));
    } else {
      this.store.dispatch(presetsActions.createPreset({
        body: { name: payload.name, config: payload.config, is_default: payload.isDefault },
      }));
    }
    this.closePresetDialog();
  }

  setDefault(preset: CaptionPresetDto): void {
    this.store.dispatch(presetsActions.updatePreset({
      id: preset.id,
      body: { is_default: true },
    }));
  }

  deletePreset(preset: CaptionPresetDto): void {
    this.store.dispatch(presetsActions.deletePreset({ id: preset.id }));
  }

  presetSummary(preset: CaptionPresetDto): string {
    const token = preset.config['task_token'];
    if (token == null) { return ''; }
    const labels: Record<string, string> = {
      '<CAPTION>': 'Kurz',
      '<DETAILED_CAPTION>': 'Detailliert',
      '<MORE_DETAILED_CAPTION>': 'Ausführlich',
    };
    return labels[String(token)] ?? String(token);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) { return `${bytes} B`; }
    if (bytes < 1024 * 1024) { return `${(bytes / 1024).toFixed(1)} KB`; }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
