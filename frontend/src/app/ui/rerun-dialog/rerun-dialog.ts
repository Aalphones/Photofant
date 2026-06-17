import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '../icon/icon';
import type { ClassifyStep } from '@photofant/services';

interface StepOption {
  key: ClassifyStep;
  label: string;
  desc: string;
}

const ALL_STEPS: StepOption[] = [
  { key: 'heuristics', label: 'Qualität',    desc: 'Auflösung + Schärfe → quality_score' },
  { key: 'tags',       label: 'Tags',        desc: 'WD14-Tagger (auto-Tags mit Konfidenz)' },
  { key: 'caption',    label: 'Caption',     desc: 'Florence-2 Bildbeschreibung' },
  { key: 'embedding',  label: 'Embedding',   desc: 'CLIP-Vektor für Ähnlichkeitssuche' },
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
  readonly confirm = output<ClassifyStep[]>();
  readonly cancel = output<void>();

  protected readonly STEPS = ALL_STEPS;
  protected readonly selected = signal<Set<ClassifyStep>>(new Set(ALL_STEPS.map((step: StepOption) => step.key)));

  protected readonly selectedSteps = computed((): ClassifyStep[] =>
    ALL_STEPS.map((step: StepOption) => step.key).filter((key: ClassifyStep) => this.selected().has(key))
  );

  protected readonly isDisabled = computed((): boolean => this.selectedSteps().length === 0);

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

  protected handleConfirm(): void {
    if (this.isDisabled()) { return; }
    this.confirm.emit(this.selectedSteps());
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleScrimClick(): void {
    this.cancel.emit();
  }
}
