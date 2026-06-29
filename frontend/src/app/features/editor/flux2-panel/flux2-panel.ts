import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { promptTemplateActions, promptTemplateSelectors } from '@photofant/store';
import type { PromptTemplateDto, ResolutionRun, WorkflowResolution } from '@photofant/models';
import { ResolutionField } from '../resolution-field/resolution-field';

export interface EditEvent {
  prompt: string;
  resolution: ResolutionRun | null;
}

@Component({
  selector: 'pf-flux2-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ResolutionField],
  templateUrl: './flux2-panel.html',
  styleUrl: './flux2-panel.scss',
})
export class Flux2Panel {
  private readonly store = inject(Store);

  readonly generating = input(false);
  readonly resolution = input<WorkflowResolution | null>(null);

  readonly edit = output<EditEvent>();

  protected readonly templates = this.store.selectSignal(promptTemplateSelectors.selectTemplates);
  protected readonly prompt = signal('');
  protected readonly selectedTemplateId = signal<number | null>(null);
  protected readonly megapixels = signal(1.0);

  protected readonly canGenerate = computed((): boolean =>
    this.prompt().trim().length > 0 && !this.generating()
  );

  constructor() {
    this.store.dispatch(promptTemplateActions.load());
  }

  protected applyTemplate(template: PromptTemplateDto): void {
    this.selectedTemplateId.set(template.id);
    this.prompt.set(template.prompt);
  }

  protected onGenerate(): void {
    const resolution = this.resolution();
    this.edit.emit({
      prompt: this.prompt(),
      resolution: resolution != null
        ? { megapixels: this.megapixels(), aspect_ratio: resolution.aspectDefault }
        : null,
    });
  }

  protected onPromptInput(event: Event): void {
    this.prompt.set((event.target as HTMLTextAreaElement).value);
    this.selectedTemplateId.set(null);
  }
}
