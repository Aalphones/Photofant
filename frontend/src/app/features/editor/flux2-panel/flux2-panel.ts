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
import type { CapabilitiesDto, PromptTemplateDto, PromptTemplateParams } from '@photofant/models';

export interface FluxEditEvent {
  prompt: string;
  templateId: number | null;
  params: Record<string, unknown>;
}

@Component({
  selector: 'pf-flux2-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './flux2-panel.html',
  styleUrl: './flux2-panel.scss',
})
export class Flux2Panel {
  private readonly store = inject(Store);

  readonly personName = input<string | null>(null);
  readonly generating = input(false);
  readonly capabilities = input<CapabilitiesDto | null>(null);

  readonly fluxEdit = output<FluxEditEvent>();

  protected readonly templates = this.store.selectSignal(promptTemplateSelectors.selectTemplates);
  protected readonly prompt = signal('');
  protected readonly strength = signal(0.65);
  protected readonly steps = signal(4);
  protected readonly guidance = signal(1);
  protected readonly seed = signal(-1);
  protected readonly selectedTemplateId = signal<number | null>(null);

  protected readonly canGenerate = computed((): boolean =>
    this.prompt().trim().length > 0 && !this.generating()
  );

  constructor() {
    this.store.dispatch(promptTemplateActions.load());
  }

  protected applyTemplate(template: PromptTemplateDto): void {
    this.selectedTemplateId.set(template.id);
    let resolvedPrompt = template.prompt;
    const name = this.personName();
    if (name) {
      resolvedPrompt = resolvedPrompt.replace('{person}', name);
    }
    this.prompt.set(resolvedPrompt);

    const params: PromptTemplateParams = template.params ?? {};
    if (params.strength != null) { this.strength.set(params.strength); }
    if (params.steps != null) { this.steps.set(params.steps); }
    if (params.guidance != null) { this.guidance.set(params.guidance); }
    if (params.seed != null) { this.seed.set(params.seed); }
  }

  protected onGenerate(): void {
    this.fluxEdit.emit({
      prompt: this.prompt(),
      templateId: this.selectedTemplateId(),
      params: {
        strength: this.strength(),
        steps: this.steps(),
        guidance: this.guidance(),
        seed: this.seed(),
      },
    });
  }

  protected resetSeed(): void {
    this.seed.set(-1);
  }

  protected onStrengthChange(event: Event): void {
    this.strength.set(+(event.target as HTMLInputElement).value);
  }

  protected onStepsChange(event: Event): void {
    this.steps.set(+(event.target as HTMLInputElement).value);
  }

  protected onGuidanceChange(event: Event): void {
    this.guidance.set(+(event.target as HTMLInputElement).value);
  }

  protected onSeedInput(event: Event): void {
    this.seed.set(+(event.target as HTMLInputElement).value);
  }

  protected onPromptInput(event: Event): void {
    this.prompt.set((event.target as HTMLTextAreaElement).value);
    this.selectedTemplateId.set(null);
  }
}
