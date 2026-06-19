import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { CapabilityDescriptor, CaptionPresetDto, ModelDto } from '@photofant/models';
import { modelsActions, modelsSelectors, presetsActions, presetsSelectors } from '@photofant/store';
import type { PresetSavePayload } from '@photofant/ui';
import { Icon, PresetDialog } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen-bearbeitung',
  imports: [Icon, PresetDialog],
  templateUrl: './bearbeitung.html',
  styleUrl: './bearbeitung.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Bearbeitung {
  private readonly store = inject(Store);

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
      this.store.dispatch(presetsActions.loadPresets());
      this.store.dispatch(modelsActions.loadModels());
    });
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
}
