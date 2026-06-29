import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { Icon } from '@photofant/ui';
import type { ResolutionRun, WorkflowResolution } from '@photofant/models';
import { ResolutionField } from '../resolution-field/resolution-field';

export interface InpaintEvent {
  maskDataUrl: string;
  prompt: string;
  resolution: ResolutionRun | null;
}

@Component({
  selector: 'pf-inpaint-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ResolutionField],
  templateUrl: './inpaint-panel.html',
  styleUrl: './inpaint-panel.scss',
})
export class InpaintPanel {
  readonly generating = input(false);
  readonly maskDataUrl = input<string | null>(null);
  readonly resolution = input<WorkflowResolution | null>(null);

  readonly inpaint = output<InpaintEvent>();
  readonly brushSizeChange = output<number>();
  readonly brushModeChange = output<'paint' | 'erase'>();
  readonly clearMask = output<void>();

  protected readonly prompt = signal('');
  protected readonly brushSize = signal(30);
  protected readonly brushMode = signal<'paint' | 'erase'>('paint');
  protected readonly megapixels = signal(1.0);

  protected readonly hasMask = computed((): boolean => this.maskDataUrl() != null);

  protected readonly canGenerate = computed((): boolean =>
    this.hasMask() && !this.generating()
  );

  protected onPromptInput(event: Event): void {
    this.prompt.set((event.target as HTMLTextAreaElement).value);
  }

  protected onBrushSizeChange(event: Event): void {
    const size = +(event.target as HTMLInputElement).value;
    this.brushSize.set(size);
    this.brushSizeChange.emit(size);
  }

  protected toggleBrushMode(): void {
    const next = this.brushMode() === 'paint' ? 'erase' : 'paint';
    this.brushMode.set(next);
    this.brushModeChange.emit(next);
  }

  protected onClearMask(): void {
    this.clearMask.emit();
  }

  protected onGenerate(): void {
    const maskDataUrl = this.maskDataUrl();
    if (maskDataUrl == null) { return; }
    const resolution = this.resolution();
    this.inpaint.emit({
      maskDataUrl,
      prompt: this.prompt(),
      resolution: resolution != null
        ? { megapixels: this.megapixels(), aspect_ratio: resolution.aspectDefault }
        : null,
    });
  }
}
