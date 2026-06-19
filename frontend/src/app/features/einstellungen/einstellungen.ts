import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Store } from '@ngrx/store';
import type { CapabilityDescriptor, CaptionPresetDto, Density, ModelDto, ProcessingConfig, ShortcutConfig, TagListItem } from '@photofant/models';
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
  tagsActions,
  tagsSelectors,
} from '@photofant/store';
import type { PresetSavePayload } from '@photofant/ui';
import { Icon, PresetDialog } from '@photofant/ui';
import { SECTIONS, SHORTCUT_ROWS, type Section } from './einstellungen.types';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PresetDialog, Icon],
  templateUrl: './einstellungen.html',
  styleUrl: './einstellungen.scss',
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

  /* ── Tags ─────────────────────────────────────────────── */
  private readonly allTagsList = this.store.selectSignal(tagsSelectors.selectAll);
  readonly isTagsLoading = this.store.selectSignal(tagsSelectors.selectIsLoading);
  readonly tagSearchQuery = signal<string>('');
  readonly filteredTagsList = computed((): TagListItem[] => {
    const query = this.tagSearchQuery().toLowerCase().trim();
    if (!query) { return this.allTagsList(); }
    return this.allTagsList().filter((tag: TagListItem) => tag.name.includes(query));
  });
  readonly renamingTagId = signal<number | null>(null);
  readonly renameDraftText = signal<string>('');
  readonly tagMergeSelected = signal<Set<number>>(new Set());
  readonly showTagMergeDialog = signal<boolean>(false);
  readonly tagMergeTargetId = signal<number | null>(null);
  readonly tagMergeSelectedTags = computed((): TagListItem[] => {
    const ids = this.tagMergeSelected();
    return this.allTagsList().filter((tag: TagListItem) => ids.has(tag.id));
  });

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
      this.store.dispatch(tagsActions.load());
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

  /* ── Tag-Methoden ────────────────────────────────────── */
  startTagRename(tag: TagListItem): void {
    this.renamingTagId.set(tag.id);
    this.renameDraftText.set(tag.name);
  }

  confirmTagRename(): void {
    const id = this.renamingTagId();
    const name = this.renameDraftText().trim();
    if (id != null && name) {
      this.store.dispatch(tagsActions.rename({ id, name }));
    }
    this.renamingTagId.set(null);
  }

  cancelTagRename(): void {
    this.renamingTagId.set(null);
  }

  onTagRenameKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmTagRename(); }
    else if (event.key === 'Escape') { this.cancelTagRename(); }
  }

  toggleTagMergeSelect(tagId: number): void {
    this.tagMergeSelected.update((selected: Set<number>) => {
      const next = new Set(selected);
      if (next.has(tagId)) { next.delete(tagId); } else { next.add(tagId); }
      return next;
    });
  }

  isTagMergeSelected(tagId: number): boolean {
    return this.tagMergeSelected().has(tagId);
  }

  openTagMergeDialog(): void {
    if (this.tagMergeSelected().size < 2) { return; }
    const ids = [...this.tagMergeSelected()];
    this.tagMergeTargetId.set(ids[0] ?? null);
    this.showTagMergeDialog.set(true);
  }

  setTagMergeTarget(tagId: number): void {
    this.tagMergeTargetId.set(tagId);
  }

  confirmTagMerge(): void {
    const intoId = this.tagMergeTargetId();
    const selected = [...this.tagMergeSelected()];
    if (intoId == null) { return; }
    const fromIds = selected.filter((id: number) => id !== intoId);
    this.store.dispatch(tagsActions.merge({ from_ids: fromIds, into_id: intoId }));
    this.tagMergeSelected.set(new Set());
    this.showTagMergeDialog.set(false);
  }

  cancelTagMerge(): void {
    this.showTagMergeDialog.set(false);
  }

  clearTagMergeSelection(): void {
    this.tagMergeSelected.set(new Set());
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) { return `${bytes} B`; }
    if (bytes < 1024 * 1024) { return `${(bytes / 1024).toFixed(1)} KB`; }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
