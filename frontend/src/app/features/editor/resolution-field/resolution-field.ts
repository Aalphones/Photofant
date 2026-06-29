import { ChangeDetectionStrategy, Component, input, model } from '@angular/core';
import type { WorkflowResolution } from '@photofant/models';

/**
 * Auflösungs-Steuerung für generative Panels. Der Workflow gibt nur eine sichere
 * Aspect-Option vor (aspectDefault) — die Megapixel sind frei wählbar. Die volle
 * Aspect-Liste bräuchte eine ComfyUI-/object_info-Abfrage (Folge-Idee).
 */
@Component({
  selector: 'pf-resolution-field',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './resolution-field.html',
  styleUrl: './resolution-field.scss',
})
export class ResolutionField {
  readonly resolution = input.required<WorkflowResolution>();
  readonly megapixels = model<number>(1.0);

  protected onMegapixelsInput(event: Event): void {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(value) && value > 0) {
      this.megapixels.set(value);
    }
  }
}
