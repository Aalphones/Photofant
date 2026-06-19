import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Store } from '@ngrx/store';
import type { CapabilityDescriptor, CaptionPresetDto, Density, ModelDto, ProcessingConfig, ShortcutConfig } from '@photofant/models';
import type { DateFormat, Locale } from '@photofant/services';
import { SettingsService } from '@photofant/services';
import { ShortcutService } from '../../services/shortcut.service';
import {
  filtersActions,
  maintenanceActions,
  maintenanceSelectors,
  modelsActions,
  modelsSelectors,
  presetsActions,
  presetsSelectors,
} from '@photofant/store';
import type { PresetSavePayload } from '@photofant/ui';
import { Icon, PresetDialog } from '@photofant/ui';

interface ShortcutRow {
  action: string;
  label: string;
  group: string;
}

interface Section {
  id: string;
  icon: string;
  label: string;
}

const SHORTCUT_ROWS: ShortcutRow[] = [
  { action: 'lightbox.close',  label: 'Lightbox schließen',    group: 'Lightbox' },
  { action: 'lightbox.prev',   label: 'Vorheriges Bild',       group: 'Lightbox' },
  { action: 'lightbox.next',   label: 'Nächstes Bild',         group: 'Lightbox' },
  { action: 'asset.favourite', label: 'Favorit umschalten',    group: 'Lightbox' },
  { action: 'asset.delete',    label: 'In Papierkorb legen',   group: 'Lightbox' },
];

const SECTIONS: Section[] = [
  { id: 'bibliothek',   icon: 'folder',   label: 'Bibliothek' },
  { id: 'verarbeitung', icon: 'refresh',  label: 'Verarbeitung' },
  { id: 'darstellung',  icon: 'gallery',  label: 'Darstellung' },
  { id: 'bearbeitung',  icon: 'pencil',   label: 'Bearbeitung' },
  { id: 'shortcuts',    icon: 'keyboard', label: 'Tastaturkürzel' },
  { id: 'backup',       icon: 'shield',   label: 'Backup & Wartung' },
  { id: 'info',         icon: 'info',     label: 'Info' },
];

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, PresetDialog, Icon],
  template: `
    <div class="st-page">

      <!-- ── linke Sektions-Nav ──────────────────────────────── -->
      <aside class="st-nav" [class.section-open]="mobileOpen()">
        <div class="st-nav-title">Einstellungen</div>
        @for (sect of sections; track sect.id) {
          <button
            class="st-nav-item"
            [class.on]="activeSection() === sect.id"
            (click)="goSection(sect.id)"
          >
            <div class="st-nav-ico">
              <pf-icon [name]="sect.icon" [size]="16" />
            </div>
            {{ sect.label }}
          </button>
        }
      </aside>

      <!-- ── rechter Inhaltsbereich ──────────────────────────── -->
      <div class="st-body" [class.section-closed]="!mobileOpen()">

        <!-- Mobile: Zurück-Button -->
        <div class="st-nav-back" (click)="goBack()">
          <pf-icon name="arrowLeft" [size]="16" />
          Einstellungen
        </div>

        @switch (activeSection()) {

          <!-- ═══ BIBLIOTHEK ══════════════════════════════════ -->
          @case ('bibliothek') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Bibliothek</h2>
                <p>Ordner und Speicherorte für Bilder, Datenbank und Modelle.</p>
              </div>

              @if (rebootRequired()) {
                <div class="st-note warn">
                  <pf-icon name="alertTriangle" [size]="15" />
                  <span>Neustart erforderlich — die neue Bibliothek wird erst nach dem Neustart der App verwendet.</span>
                </div>
              }

              <div class="st-group-label">Speicherorte</div>
              <div class="st-group">

                <!-- Sammlungs-Ordner -->
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Sammlungs-Ordner</div>
                    <div class="st-row-sub">Wurzelverzeichnis aller Bilddateien und der Datenbank. Bilder und DB müssen manuell in den neuen Ordner kopiert werden.</div>
                    @if (isDataRootEditing()) {
                      <div class="path-edit">
                        <input
                          class="dir-input"
                          type="text"
                          [value]="pendingDataRoot()"
                          (input)="pendingDataRoot.set($any($event.target).value)"
                          (keydown.enter)="saveDataRootEdit()"
                          (keydown.escape)="cancelDataRootEdit()"
                        />
                        <button class="st-btn accent" (click)="saveDataRootEdit()">Speichern</button>
                        <button class="st-btn ghost" (click)="cancelDataRootEdit()">Abbrechen</button>
                      </div>
                    }
                  </div>
                  @if (!isDataRootEditing()) {
                    <div class="st-row-ctrl">
                      <div class="st-path">
                        <pf-icon name="folder" [size]="14" />
                        <span class="sp-val">{{ dataRoot() ?? '–' }}</span>
                        <button class="sp-btn" (click)="startDataRootEdit()">Ändern</button>
                      </div>
                    </div>
                  }
                </div>

                <!-- Modell-Ordner -->
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Modell-Ordner</div>
                    <div class="st-row-sub">Standard-Ziel für neue Modell-Downloads. Bestehende Pfade bleiben bei Änderung erhalten.</div>
                    @if (isDirEditing()) {
                      <div class="path-edit">
                        <input
                          class="dir-input"
                          type="text"
                          [value]="pendingDir()"
                          (input)="pendingDir.set($any($event.target).value)"
                          (keydown.enter)="saveDirEdit()"
                          (keydown.escape)="cancelDirEdit()"
                        />
                        <button class="st-btn accent" (click)="saveDirEdit()">Speichern</button>
                        <button class="st-btn ghost" (click)="cancelDirEdit()">Abbrechen</button>
                      </div>
                    }
                  </div>
                  @if (!isDirEditing()) {
                    <div class="st-row-ctrl">
                      <div class="st-path">
                        <pf-icon name="folder" [size]="14" />
                        <span class="sp-val">{{ modelsDir() ?? '–' }}</span>
                        <button class="sp-btn" (click)="startDirEdit()">Ändern</button>
                      </div>
                    </div>
                  }
                </div>

              </div><!-- /st-group -->

              <div class="st-note accent">
                <pf-icon name="info" [size]="15" />
                <span>Alle Bilddateien liegen ausschließlich im Dateisystem. Die Datenbank hält nur Metadaten — ein regelmäßiges Backup schützt vor Datenverlust.</span>
              </div>
            </div>
          }

          <!-- ═══ VERARBEITUNG ════════════════════════════════ -->
          @case ('verarbeitung') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Verarbeitung</h2>
                <p>Pipeline-Parameter für Import, Tagging und Caption-Erstellung.</p>
              </div>

              <div class="st-group-label">Auto-Pipeline</div>
              <div class="st-group">
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Auto-Tagging (WD14)</div>
                    <div class="st-row-sub">Beim Import automatisch WD14-Tags generieren.</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-switch"
                      [class.on]="processingConfig().autoTag"
                      role="switch"
                      [attr.aria-checked]="processingConfig().autoTag"
                      (click)="patchProcessingConfig({ autoTag: !processingConfig().autoTag })"
                    ><i></i></button>
                  </div>
                </div>
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Auto-Caption (Florence-2)</div>
                    <div class="st-row-sub">Beim Import automatisch Bildbeschreibungen generieren.</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-switch"
                      [class.on]="processingConfig().autoCaption"
                      role="switch"
                      [attr.aria-checked]="processingConfig().autoCaption"
                      (click)="patchProcessingConfig({ autoCaption: !processingConfig().autoCaption })"
                    ><i></i></button>
                  </div>
                </div>
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">CLIP-Embedding</div>
                    <div class="st-row-sub">Beim Import automatisch semantische Suchdaten berechnen.</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-switch"
                      [class.on]="processingConfig().autoEmbed"
                      role="switch"
                      [attr.aria-checked]="processingConfig().autoEmbed"
                      (click)="patchProcessingConfig({ autoEmbed: !processingConfig().autoEmbed })"
                    ><i></i></button>
                  </div>
                </div>
              </div>

              <div class="st-group-label">Qualitätsfilter</div>
              <div class="st-group">
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Mindest-Konfidenz (WD14)</div>
                    <div class="st-row-sub">Tags unterhalb dieses Wertes werden verworfen. Default: 0.5</div>
                  </div>
                  <div class="st-row-ctrl">
                    <input
                      class="st-num"
                      type="number"
                      min="0"
                      max="1"
                      step="0.05"
                      [value]="processingConfig().minProbability"
                      (change)="onMinProbabilityChange($any($event.target))"
                    >
                  </div>
                </div>
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Max. Tags pro Bild</div>
                    <div class="st-row-sub">Maximale Anzahl automatisch gesetzter Tags, nach Konfidenz sortiert. Default: 30</div>
                  </div>
                  <div class="st-row-ctrl">
                    <input
                      class="st-num"
                      type="number"
                      min="1"
                      max="200"
                      [value]="processingConfig().maxTags"
                      (change)="onMaxTagsChange($any($event.target))"
                    >
                  </div>
                </div>
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Mindestschärfe (Laplacian-Varianz)</div>
                    <div class="st-row-sub">Bilder unterhalb gelten als unscharf. Default: 200</div>
                  </div>
                  <div class="st-row-ctrl">
                    <input
                      class="st-num"
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
            </div>
          }

          <!-- ═══ DARSTELLUNG ═════════════════════════════════ -->
          @case ('darstellung') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Darstellung</h2>
                <p>Galerie-Raster, Metadaten-Dichte und Sprache.</p>
              </div>

              <div class="st-group-label">Galerie</div>
              <div class="st-group">
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Metadaten unter Bild anzeigen</div>
                    <div class="st-row-sub">Zeigt Quelle und Tags unter jedem Bild im Raster.</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-switch"
                      [class.on]="displaySettings().showMeta"
                      role="switch"
                      [attr.aria-checked]="displaySettings().showMeta"
                      (click)="setShowMeta(!displaySettings().showMeta)"
                    ><i></i></button>
                  </div>
                </div>
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Animations-Effekte reduzieren</div>
                    <div class="st-row-sub">Deaktiviert Überblend- und Slide-Animationen für barrierefreieres Erleben.</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-switch"
                      [class.on]="displaySettings().reducedMotion"
                      role="switch"
                      [attr.aria-checked]="displaySettings().reducedMotion"
                      (click)="setReducedMotion(!displaySettings().reducedMotion)"
                    ><i></i></button>
                  </div>
                </div>
              </div>

              <div class="st-group-label">Sprache & Region</div>
              <div class="st-group">
                <div class="st-row">
                  <div class="st-row-body">
                    <div class="st-row-title">Sprache</div>
                  </div>
                  <div class="st-row-ctrl">
                    <select
                      class="st-select"
                      [value]="displaySettings().locale"
                      (change)="setLocale($any($event.target).value)"
                    >
                      <option value="de">Deutsch</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                </div>
                <div class="st-row">
                  <div class="st-row-body">
                    <div class="st-row-title">Datumsformat</div>
                  </div>
                  <div class="st-row-ctrl">
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
            </div>
          }

          <!-- ═══ BEARBEITUNG (Caption-Presets) ══════════════ -->
          @case ('bearbeitung') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Bearbeitung</h2>
                <p>Benannte, wiederverwendbare Captioner-Presets verwalten.</p>
              </div>

              @if (captionerModel() != null) {
                <div class="st-group">
                  <div class="st-row">
                    <div class="st-row-body">
                      <div class="st-row-title">Presets für {{ captionerModel()!.name }}</div>
                      <div class="st-row-sub">Beim Caption-Lauf wählst du Modell + Preset.</div>
                    </div>
                    <div class="st-row-ctrl">
                      <button class="st-btn accent" (click)="openCreateDialog()">Neu</button>
                    </div>
                  </div>

                  @if (isLoadingPresets()) {
                    <div class="group-loading">
                      <span class="spinner"></span> Lade…
                    </div>
                  } @else if (presets().length === 0) {
                    <p class="group-empty">Noch keine Presets vorhanden.</p>
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
                              <button class="st-btn ghost" style="height:28px;padding:0 10px;font-size:12px" (click)="setDefault(preset)">Standard</button>
                            }
                            <button class="st-btn ghost" style="height:28px;padding:0 10px;font-size:12px" (click)="openEditDialog(preset)">Bearbeiten</button>
                            <button class="st-btn danger" style="height:28px;padding:0 10px;font-size:12px" (click)="deletePreset(preset)">Löschen</button>
                          </div>
                        </li>
                      }
                    </ul>
                  }
                </div>
              } @else {
                <div class="st-note info">
                  <pf-icon name="info" [size]="15" />
                  <span>Kein Captioner-Modell aktiv. Lade ein Florence-2-Modell in der Modell-Verwaltung, um Presets anzulegen.</span>
                </div>
              }
            </div>
          }

          <!-- ═══ TASTATURKÜRZEL ══════════════════════════════ -->
          @case ('shortcuts') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Tastaturkürzel</h2>
                <p>Klicke auf einen Eintrag, um ihn neu zu belegen. Dann die gewünschte Taste drücken.</p>
              </div>

              <div class="st-group">
                @for (row of shortcutRows; track row.action) {
                  <div class="st-sc-row" [class.editing]="listeningAction() === row.action">
                    <div class="st-sc-action">{{ row.label }}</div>
                    <div class="st-sc-keys">
                      @if (listeningAction() === row.action) {
                        <span class="st-sc-listening">Taste drücken …</span>
                      } @else {
                        <button
                          class="st-key"
                          title="Klicken um Taste zu ändern"
                          (click)="startListening(row.action)"
                        >{{ formatKeys(resolvedShortcuts().get(row.action)) }}</button>
                      }
                    </div>
                  </div>
                }
              </div>

              <div class="shortcuts-footer">
                <button class="st-btn ghost" (click)="resetShortcuts()">Auf Standard zurücksetzen</button>
              </div>
            </div>
          }

          <!-- ═══ BACKUP & WARTUNG ════════════════════════════ -->
          @case ('backup') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Backup & Wartung</h2>
                <p>Datenbank-Snapshots erstellen und vorhandene Backups verwalten.</p>
              </div>

              <div class="st-group">
                <div class="st-row top">
                  <div class="st-row-body">
                    <div class="st-row-title">Datenbank-Backup</div>
                    <div class="st-row-sub">Erstellt einen konsistenten Snapshot via SQLite Online Backup API. Ziel: <code>.photofant/backups/</code></div>
                  </div>
                  <div class="st-row-ctrl">
                    <button
                      class="st-btn accent"
                      [disabled]="isRunningBackup()"
                      (click)="triggerBackup()"
                    >
                      @if (isRunningBackup()) {
                        <span class="spinner"></span> Läuft…
                      } @else {
                        Backup erstellen
                      }
                    </button>
                  </div>
                </div>
                @if (error()) {
                  <div class="error-banner">{{ error() }}</div>
                }
              </div>

              <div class="st-group">
                <div class="st-row">
                  <div class="st-row-body">
                    <div class="st-row-title">Vorhandene Backups</div>
                  </div>
                  <div class="st-row-ctrl">
                    <button class="st-btn ghost" (click)="refreshBackups()">Aktualisieren</button>
                  </div>
                </div>
                @if (isLoadingBackups()) {
                  <div class="group-loading">
                    <span class="spinner"></span> Lade…
                  </div>
                } @else if (backups().length === 0) {
                  <p class="group-empty">Noch kein Backup vorhanden.</p>
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
          }

          <!-- ═══ INFO ═════════════════════════════════════════ -->
          @case ('info') {
            <div class="st-section">
              <div class="st-section-head">
                <h2>Info</h2>
                <p>Version, Laufzeitumgebung und Systemdetails.</p>
              </div>

              <div class="st-group">
                @if (isLoadingAppInfo()) {
                  <div class="group-loading">
                    <span class="spinner"></span> Lade…
                  </div>
                } @else if (appInfo() != null) {
                  <div class="info-note">Keine Netzwerkverbindung — alle Daten lokal.</div>
                  <dl class="info-grid">
                    <dt>Version</dt>
                    <dd><code>{{ appInfo()!.version }}</code></dd>

                    <dt>Python</dt>
                    <dd><code>{{ appInfo()!.python_version.split(' ')[0] }}</code></dd>

                    <dt>ONNX Runtime</dt>
                    <dd><code>{{ appInfo()!.onnx_version }}</code></dd>

                    <dt>Letzte Migration</dt>
                    <dd><code>{{ appInfo()!.last_migration ?? '–' }}</code></dd>

                    <dt>Datenbank</dt>
                    <dd>
                      <code>{{ appInfo()!.db_path }}</code>
                      <span class="info-meta">{{ formatSize(appInfo()!.db_size_bytes) }}</span>
                    </dd>

                    <dt>Thumbnail-Cache</dt>
                    <dd>
                      <code>{{ appInfo()!.cache_db_path }}</code>
                      <span class="info-meta">{{ formatSize(appInfo()!.cache_db_size_bytes) }}</span>
                    </dd>

                    @if (appInfo()!.gpu_name != null) {
                      <dt>GPU</dt>
                      <dd>
                        <code>{{ appInfo()!.gpu_name }}</code>
                        @if (appInfo()!.vram_gb != null) {
                          <span class="info-meta">{{ appInfo()!.vram_gb }} GB VRAM</span>
                        }
                      </dd>
                      @if (appInfo()!.cuda_version != null) {
                        <dt>CUDA</dt>
                        <dd><code>{{ appInfo()!.cuda_version }}</code></dd>
                      }
                    }

                    @if (objectKeys(appInfo()!.env_flags).length > 0) {
                      <dt>Env-Flags</dt>
                      <dd>
                        @for (key of objectKeys(appInfo()!.env_flags); track key) {
                          <div class="info-flag"><code>{{ key }}={{ appInfo()!.env_flags[key] }}</code></div>
                        }
                      </dd>
                    }
                  </dl>
                } @else {
                  <p class="group-empty">Info konnte nicht geladen werden.</p>
                }
              </div>

              <div class="st-note accent">
                <pf-icon name="shield" [size]="15" />
                <span>Kein Netzwerkverkehr zur Laufzeit. Alle Daten bleiben lokal. Keine Authentifizierung, kein Account, keine Telemetrie.</span>
              </div>
            </div>
          }

        }<!-- /@switch -->

      </div><!-- /st-body -->
    </div><!-- /st-page -->

    <!-- ── Preset-Dialog (global, ausserhalb des Layouts) ───── -->
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
    :host { display: block; height: 100%; overflow: hidden; }
    .st-page { display: flex; height: 100%; overflow: hidden; }
    .st-nav { width: 220px; flex: none; border-right: 1px solid var(--line); display: flex; flex-direction: column; background: var(--bg); overflow-y: auto; padding: 16px 10px 24px; }
    .st-nav-title { font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--text-3); font-weight: 600; padding: 2px 8px 10px; }
    .st-nav-item { display: flex; align-items: center; gap: 11px; width: 100%; padding: 9px 10px; border-radius: var(--radius); font-size: 13.5px; font-weight: 500; color: var(--text-2); }
    .st-nav-item.on { background: var(--accent-weak); color: var(--accent); font-weight: 600; }
    .st-nav-ico { width: 30px; height: 30px; border-radius: 8px; flex: none; display: grid; place-items: center; background: var(--surface); color: var(--text-3); }
    .st-nav-item.on .st-nav-ico { background: var(--accent); color: #fff; }
    .st-nav-back { display: none; }
    .st-body { flex: 1; min-width: 0; overflow-y: auto; padding: 28px 32px 60px; }
    .st-section { max-width: 660px; }
    .st-section-head { margin-bottom: 22px; }
    .st-section-head h2 { margin: 0 0 4px; font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
    .st-section-head p { margin: 0; font-size: 13px; color: var(--text-3); line-height: 1.5; }
    .st-group { background: var(--bg-2); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; margin-bottom: 20px; }
    .st-group-label { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-3); font-weight: 600; padding: 0 2px 8px; }
    .st-row { display: flex; align-items: center; gap: 16px; padding: 14px 16px; border-bottom: 1px solid var(--line); }
    .st-row:last-child { border-bottom: none; }
    .st-row.top { align-items: flex-start; }
    .st-row-body { flex: 1; min-width: 0; }
    .st-row-title { font-size: 13.5px; font-weight: 500; color: var(--text); }
    .st-row-sub { font-size: 12px; color: var(--text-3); margin-top: 3px; line-height: 1.45; }
    .st-row-ctrl { flex: none; display: flex; align-items: center; gap: 10px; }
    .path-edit { display: flex; align-items: center; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
    .dir-input { height: 34px; padding: 0 10px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-s); color: var(--text); font-family: var(--mono); font-size: 12px; outline: none; width: 260px; flex-shrink: 1; }
    .st-path { display: flex; align-items: center; gap: 9px; padding: 8px 11px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--line); font-family: var(--mono); font-size: 12px; color: var(--text-2); min-width: 0; overflow: hidden; }
    .sp-val { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
    .sp-btn { flex: none; font-size: 11.5px; font-weight: 600; color: var(--accent); padding: 4px 8px; border-radius: 7px; }
    .st-note { display: flex; gap: 9px; padding: 11px 13px; border-radius: var(--radius); font-size: 12px; color: var(--text-2); line-height: 1.5; margin-bottom: 20px; }
    .st-note.info { background: var(--bg-2); border: 1px solid var(--line); }
    .st-note.accent { background: var(--accent-weak); border: 1px solid var(--accent-line); }
    .st-note.warn { background: var(--surface); border: 1px solid var(--line); }
    .error-banner { font-size: 12px; color: var(--danger); background: var(--danger-weak); border-radius: var(--radius-s); padding: 8px 12px; margin: 0 16px 8px; }
    .st-btn { display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 14px; border-radius: 9px; font-size: 13px; font-weight: 600; }
    .st-btn.ghost { background: var(--surface); border: 1px solid var(--line); color: var(--text); }
    .st-btn.ghost:hover { background: var(--surface-hover); }
    .st-btn.accent { background: var(--accent); color: #fff; }
    .st-btn.danger { background: var(--surface); border: 1px solid var(--line); color: var(--danger); }
    .st-btn.danger:hover { background: var(--danger-weak); border-color: var(--danger); }
    .st-btn:disabled { opacity: .45; }
    .st-switch { position: relative; width: 42px; height: 24px; border-radius: 999px; flex: none; cursor: pointer; background: var(--line-2); border: 1px solid var(--line-2); }
    .st-switch.on { background: var(--accent); border-color: var(--accent); }
    .st-switch > i { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; transition: transform .16s; }
    .st-switch.on > i { transform: translateX(18px); }
    .st-select { appearance: none; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-s); color: var(--text); font-size: 13px; padding: 7px 28px 7px 11px; outline: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6' fill='%23888'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 9px center; cursor: pointer; min-width: 130px; }
    .st-num { height: 32px; width: 90px; padding: 0 8px; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius-s); color: var(--text); font-size: 13px; text-align: right; outline: none; }
    .dir-input:focus,.st-select:focus,.st-num:focus { border-color: var(--accent-line); box-shadow: 0 0 0 3px var(--accent-weak); }
    code { font-family: var(--mono); font-size: 11px; background: var(--bg); padding: 1px 5px; border-radius: 4px; color: var(--accent); }
    .info-grid dd code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
    .spinner { width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--line-2); border-top-color: currentColor; animation: pf-spin .8s linear infinite; flex-shrink: 0; }
    .group-loading,.group-empty { font-size: 13px; color: var(--text-3); padding: 16px; margin: 0; }
    .group-loading { display: flex; align-items: center; gap: 8px; }
    .presets-list { list-style: none; margin: 0; padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 1px; }
    .preset-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); }
    .preset-info { display: flex; align-items: center; gap: 8px; min-width: 0; }
    .preset-name { font-size: 13px; font-weight: 500; color: var(--text); }
    .preset-badge { font-size: 10px; font-weight: 600; background: var(--accent-weak); color: var(--accent); padding: 1px 6px; border-radius: 10px; flex-shrink: 0; }
    .preset-meta { font-size: 11px; color: var(--text-3); }
    .preset-actions { display: flex; gap: 4px; flex-shrink: 0; }
    .backups-list { list-style: none; margin: 0; padding: 0; }
    .backup-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-top: 1px solid var(--line); }
    .backup-name { font-family: var(--mono); font-size: 12px; color: var(--text-2); }
    .backup-meta { font-size: 11px; color: var(--text-3); }
    .st-sc-row { display: flex; align-items: center; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--line); }
    .st-sc-row:last-child { border-bottom: none; }
    .st-sc-row.editing { background: var(--accent-weak); }
    .st-sc-action { flex: 1; font-size: 13px; color: var(--text); }
    .st-sc-keys { display: flex; gap: 4px; align-items: center; flex: none; }
    .st-key { display: inline-grid; place-items: center; min-width: 28px; height: 24px; padding: 0 7px; border-radius: 6px; background: var(--surface); border: 1px solid var(--line-2); font-size: 11.5px; font-family: var(--mono); color: var(--text); cursor: pointer; }
    .st-sc-listening { font-size: 12px; color: var(--accent); font-style: italic; }
    .shortcuts-footer { display: flex; justify-content: flex-end; padding: 10px 0 0; }
    .info-note { font-size: 11px; color: var(--text-3); padding: 12px 16px 0; }
    .info-grid { display: grid; grid-template-columns: 140px 1fr; gap: 8px 16px; margin: 0; padding: 12px 16px; }
    .info-grid dt { font-size: 12px; color: var(--text-3); align-self: start; padding-top: 2px; }
    .info-grid dd { font-size: 12px; color: var(--text-2); margin: 0; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .info-meta { font-size: 11px; color: var(--text-3); }
    @media (max-width: 860px) {
      .st-page { flex-direction: column; }
      .st-nav { width: 100%; border-right: none; border-bottom: 1px solid var(--line); }
      .st-nav.section-open { display: none; }
      .st-body.section-closed { display: none; }
      .st-nav-back { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--accent); padding: 0 0 14px; cursor: pointer; }
      .st-row { flex-wrap: wrap; gap: 8px; }
      .st-row-ctrl { width: 100%; }
    }
  `],
})
export class Einstellungen {
  private readonly store = inject(Store);
  private readonly settings = inject(SettingsService);
  private readonly shortcutService = inject(ShortcutService);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  /* ── Sektions-Navigation ──────────────────────────────── */
  readonly sections: Section[] = SECTIONS;
  readonly activeSection = signal<string>('bibliothek');
  readonly mobileOpen = signal<boolean>(false);

  goSection(id: string): void {
    this.activeSection.set(id);
    this.mobileOpen.set(true);
  }

  goBack(): void {
    this.mobileOpen.set(false);
  }

  /* ── Tastaturkürzel ───────────────────────────────────── */
  readonly shortcutRows = SHORTCUT_ROWS;
  readonly resolvedShortcuts = this.shortcutService.resolvedShortcuts;
  readonly listeningAction = signal<string | null>(null);

  /* ── Darstellung ──────────────────────────────────────── */
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

  /* ── Bibliothek ───────────────────────────────────────── */
  readonly dataRoot = this.store.selectSignal(modelsSelectors.selectDataRoot);
  readonly rebootRequired = this.store.selectSignal(modelsSelectors.selectRebootRequired);
  readonly modelsDir = this.store.selectSignal(modelsSelectors.selectModelsDir);
  readonly processingConfig = this.store.selectSignal(modelsSelectors.selectProcessingConfig);
  readonly isDataRootEditing = signal<boolean>(false);
  readonly pendingDataRoot = signal<string>('');
  readonly isDirEditing = signal<boolean>(false);
  readonly pendingDir = signal<string>('');

  /* ── Backup & Wartung ─────────────────────────────────── */
  readonly backups = this.store.selectSignal(maintenanceSelectors.selectBackups);
  readonly isLoadingBackups = this.store.selectSignal(maintenanceSelectors.selectIsLoadingBackups);
  readonly isRunningBackup = this.store.selectSignal(maintenanceSelectors.selectIsRunningBackup);
  readonly error = this.store.selectSignal(maintenanceSelectors.selectError);

  /* ── Info ─────────────────────────────────────────────── */
  readonly appInfo = this.store.selectSignal(maintenanceSelectors.selectAppInfo);
  readonly isLoadingAppInfo = this.store.selectSignal(maintenanceSelectors.selectIsLoadingAppInfo);

  /* ── Bearbeitung (Caption-Presets) ────────────────────── */
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

  readonly objectKeys = Object.keys;

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadBackups());
      this.store.dispatch(maintenanceActions.loadAppInfo());
      this.store.dispatch(modelsActions.loadConfig());
      this.store.dispatch(modelsActions.loadModels());
      this.store.dispatch(presetsActions.loadPresets());
    });

    const onCaptureKey = (event: KeyboardEvent): void => {
      const action = this.listeningAction();
      if (action == null) { return; }
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
      event.preventDefault();
      event.stopPropagation();
      this.applyCapture(action, event.key);
    };
    this.document.addEventListener('keydown', onCaptureKey, { capture: true });
    this.destroyRef.onDestroy(() =>
      this.document.removeEventListener('keydown', onCaptureKey, { capture: true })
    );
  }

  startListening(action: string): void {
    this.listeningAction.set(action);
  }

  private applyCapture(action: string, key: string): void {
    const current = this.resolvedShortcuts();
    const shortcuts = SHORTCUT_ROWS.map((row): { action: string; keys: string[] } => ({
      action: row.action,
      keys: row.action === action ? [key] : (current.get(row.action) ?? []),
    }));
    const config: ShortcutConfig = { version: 1, shortcuts };
    this.shortcutService.saveShortcuts(config);
    this.listeningAction.set(null);
  }

  resetShortcuts(): void {
    this.shortcutService.resetShortcuts();
  }

  formatKeys(keys: string[] | undefined): string {
    if (keys == null || keys.length === 0) { return '–'; }
    return keys
      .map((key: string) => {
        const labels: Record<string, string> = {
          ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓',
          Escape: 'Esc', Delete: 'Entf', Backspace: '⌫', Enter: '↵',
          ' ': 'Leertaste',
        };
        return labels[key] ?? key;
      })
      .join(' / ');
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

  /* ── Verarbeitung ─────────────────────────────────────── */
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
