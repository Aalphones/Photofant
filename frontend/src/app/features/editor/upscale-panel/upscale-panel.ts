import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
  signal,
} from '@angular/core';
import { Icon } from '@photofant/ui';
import type { ResolutionRun, WorkflowResolution } from '@photofant/models';
import { ResolutionField } from '../resolution-field/resolution-field';

export interface UpscaleEvent {
  resolution: ResolutionRun | null;
}

@Component({
  selector: 'pf-upscale-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ResolutionField],
  templateUrl: './upscale-panel.html',
  styleUrl: './upscale-panel.scss',
})
export class UpscalePanel {
  readonly generating = input(false);
  readonly resolution = input<WorkflowResolution | null>(null);

  readonly upscale = output<UpscaleEvent>();

  protected readonly megapixels = signal(2.0);

  protected onGenerate(): void {
    const resolution = this.resolution();
    this.upscale.emit({
      resolution: resolution != null
        ? { megapixels: this.megapixels(), aspect_ratio: resolution.aspectDefault }
        : null,
    });
  }
}
