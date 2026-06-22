import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { EditorStep } from '@photofant/models';

@Component({
  selector: 'pf-step-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './step-bar.html',
  styleUrl: './step-bar.scss',
})
export class StepBar {
  readonly steps = input.required<EditorStep[]>();
  readonly currentSeq = input.required<number>();
  readonly originalPreviewUrl = input<string | null>(null);
  readonly applying = input(false);

  readonly rollback = output<number>();

  protected onRollback(seq: number): void {
    this.rollback.emit(seq);
  }

  protected stepLabel(step: EditorStep): string {
    return step.label;
  }

  protected isStepCurrent(step: EditorStep): boolean {
    return step.seq === this.currentSeq();
  }

  protected isOriginalCurrent(): boolean {
    return this.currentSeq() === 0;
  }
}
