import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import type { CaptionAction, TrainingSetItem } from '@photofant/models';
import { Icon } from '@photofant/ui';

interface ActionOption {
  key: CaptionAction;
  label: string;
  desc: string;
}

const ACTIONS: ActionOption[] = [
  { key: 'trigger_word', label: 'Trigger-Word', desc: 'Wort voranstellen — einmalig, wird nicht doppelt vorangestellt' },
  { key: 'prefix', label: 'Prefix', desc: 'Text vor jede Caption stellen' },
  { key: 'suffix', label: 'Suffix', desc: 'Text an jede Caption anhängen' },
  { key: 'find_replace', label: 'Suchen & Ersetzen', desc: 'Textstelle in allen Captions ersetzen' },
];

function previewTransform(base: string, action: CaptionAction, params: Record<string, string>): string {
  const text = base ?? '';
  if (action === 'trigger_word') {
    const word = (params['word'] ?? '').trim();
    if (!word) { return text; }
    if (text === word || text.startsWith(`${word}, `)) { return text; }
    return text ? `${word}, ${text}` : word;
  }
  if (action === 'prefix') {
    const prefix = (params['text'] ?? '').trim();
    if (!prefix) { return text; }
    if (text.startsWith(prefix)) { return text; }
    return text ? `${prefix} ${text}` : prefix;
  }
  if (action === 'suffix') {
    const suffix = (params['text'] ?? '').trim();
    if (!suffix) { return text; }
    if (text.endsWith(suffix)) { return text; }
    return text ? `${text} ${suffix}` : suffix;
  }
  const find = params['find'] ?? '';
  if (!find) { return text; }
  const replace = params['replace'] ?? '';
  return text.split(find).join(replace);
}

@Component({
  selector: 'pf-training-set-captions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './training-set-captions.html',
  styleUrl: './training-set-captions.scss',
})
export class TrainingSetCaptions {
  readonly items = input.required<TrainingSetItem[]>();
  readonly apply = output<{ action: CaptionAction; params: Record<string, string> }>();
  readonly cancel = output<void>();

  protected readonly ACTIONS = ACTIONS;
  protected readonly action = signal<CaptionAction>('trigger_word');
  protected readonly word = signal('');
  protected readonly prefixText = signal('');
  protected readonly suffixText = signal('');
  protected readonly findText = signal('');
  protected readonly replaceText = signal('');

  protected readonly params = computed((): Record<string, string> => {
    const currentAction = this.action();
    if (currentAction === 'trigger_word') { return { word: this.word() }; }
    if (currentAction === 'prefix') { return { text: this.prefixText() }; }
    if (currentAction === 'suffix') { return { text: this.suffixText() }; }
    return { find: this.findText(), replace: this.replaceText() };
  });

  protected readonly activeActionDesc = computed((): string =>
    ACTIONS.find((option: ActionOption) => option.key === this.action())?.desc ?? '');

  protected readonly isDisabled = computed((): boolean => {
    const currentAction = this.action();
    const currentParams = this.params();
    if (currentAction === 'find_replace') { return !currentParams['find']; }
    if (currentAction === 'trigger_word') { return !currentParams['word']?.trim(); }
    return !currentParams['text']?.trim();
  });

  protected readonly previewSamples = computed((): { before: string; after: string }[] => {
    const currentAction = this.action();
    const currentParams = this.params();
    return this.items()
      .slice(0, 5)
      .map((item: TrainingSetItem): { before: string; after: string } => {
        const before = item.effective_caption ?? '';
        return { before, after: previewTransform(before, currentAction, currentParams) };
      });
  });

  protected selectAction(key: CaptionAction): void {
    this.action.set(key);
  }

  protected onWordInput(value: string): void {
    this.word.set(value);
  }

  protected onPrefixInput(value: string): void {
    this.prefixText.set(value);
  }

  protected onSuffixInput(value: string): void {
    this.suffixText.set(value);
  }

  protected onFindInput(value: string): void {
    this.findText.set(value);
  }

  protected onReplaceInput(value: string): void {
    this.replaceText.set(value);
  }

  protected onScrimClick(): void {
    this.cancel.emit();
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleApply(): void {
    if (this.isDisabled()) { return; }
    this.apply.emit({ action: this.action(), params: this.params() });
  }
}
