import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '../icon/icon';
import type { CaptionPresetDto } from '@photofant/models';
import type { ClassifyStep } from '@photofant/services';

export interface RerunPayload {
  steps: ClassifyStep[];
  captionPresetId: number | null;
}

interface StepOption {
  key: ClassifyStep;
  label: string;
  desc: string;
}

const DEFAULT_STEPS: readonly ClassifyStep[] = ['heuristics', 'tags', 'caption', 'embedding'];

const ALL_STEPS: StepOption[] = [
  { key: 'heuristics', label: 'Qualität',    desc: 'Auflösung + Schärfe → quality_score' },
  { key: 'tags',       label: 'Tags',        desc: 'WD14-Tagger (auto-Tags mit Konfidenz)' },
  { key: 'caption',    label: 'Caption',     desc: 'Florence-2 Bildbeschreibung' },
  { key: 'embedding',  label: 'Embedding',   desc: 'CLIP-Vektor für Ähnlichkeitssuche' },
  { key: 'faces',      label: 'Gesichter',   desc: 'Gesichtserkennung neu starten — löscht vorhandene Erkennungen' },
];

@Component({
  selector: 'pf-rerun-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './rerun-dialog.html',
  styleUrl: './rerun-dialog.scss',
})
export class RerunDialog {
  readonly scopeLabel = input.required<string>();
  readonly presets = input<CaptionPresetDto[]>([]);
  readonly confirm = output<RerunPayload>();
  readonly cancel = output<void>();

  protected readonly STEPS = ALL_STEPS;
  protected readonly selected = signal<Set<ClassifyStep>>(new Set(DEFAULT_STEPS));
  protected readonly selectedPresetId = signal<number | null>(null);

  protected readonly selectedSteps = computed((): ClassifyStep[] =>
    ALL_STEPS.map((step: StepOption) => step.key).filter((key: ClassifyStep) => this.selected().has(key))
  );

  protected readonly isCaptionSelected = computed((): boolean => this.selected().has('caption'));

  protected readonly isDisabled = computed((): boolean => this.selectedSteps().length === 0);

  protected readonly activePresets = computed((): CaptionPresetDto[] => this.presets());

  protected readonly effectivePresetId = computed((): number | null => {
    if (!this.isCaptionSelected()) { return null; }
    const explicit = this.selectedPresetId();
    if (explicit != null) { return explicit; }
    const defaultPreset = this.presets().find((preset: CaptionPresetDto) => preset.is_default);
    return defaultPreset?.id ?? null;
  });

  protected isSelected(key: ClassifyStep): boolean {
    return this.selected().has(key);
  }

  protected toggleStep(key: ClassifyStep): void {
    this.selected.update((current: Set<ClassifyStep>) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  protected selectPreset(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedPresetId.set(value ? Number(value) : null);
  }

  protected handleConfirm(): void {
    if (this.isDisabled()) { return; }
    this.confirm.emit({
      steps: this.selectedSteps(),
      captionPresetId: this.effectivePresetId(),
    });
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleScrimClick(): void {
    this.cancel.emit();
  }
}
