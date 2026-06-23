import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { Icon } from '@photofant/ui';

export interface InpaintEvent {
  mask: string;
  prompt: string;
  params: Record<string, unknown>;
}

@Component({
  selector: 'pf-inpaint-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './inpaint-panel.html',
  styleUrl: './inpaint-panel.scss',
})
export class InpaintPanel {
  readonly generating = input(false);
  readonly maskDataUrl = input<string | null>(null);

  readonly inpaint = output<InpaintEvent>();
  readonly brushSizeChange = output<number>();
  readonly brushModeChange = output<'paint' | 'erase'>();
  readonly clearMask = output<void>();

  protected readonly prompt = signal('');
  protected readonly brushSize = signal(30);
  protected readonly brushMode = signal<'paint' | 'erase'>('paint');
  protected readonly steps = signal(20);
  protected readonly guidance = signal(7.5);
  protected readonly strength = signal(0.85);

  protected readonly hasMask = computed((): boolean => this.maskDataUrl() != null);

  protected readonly canGenerate = computed((): boolean =>
    this.hasMask() && this.prompt().trim().length > 0 && !this.generating()
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

  protected onStepsChange(event: Event): void {
    this.steps.set(+(event.target as HTMLInputElement).value);
  }

  protected onGuidanceChange(event: Event): void {
    this.guidance.set(+(event.target as HTMLInputElement).value);
  }

  protected onStrengthChange(event: Event): void {
    this.strength.set(+(event.target as HTMLInputElement).value);
  }

  protected onGenerate(): void {
    const mask = this.maskDataUrl();
    if (mask == null) { return; }
    this.inpaint.emit({
      mask,
      prompt: this.prompt(),
      params: {
        steps: this.steps(),
        guidance: this.guidance(),
        strength: this.strength(),
      },
    });
  }
}
