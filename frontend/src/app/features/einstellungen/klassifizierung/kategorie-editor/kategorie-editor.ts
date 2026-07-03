import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { ClassificationCategory, ClassificationLabel, ClassificationMode } from '@photofant/models';
import { classificationActions } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen-kategorie-editor',
  imports: [Icon],
  templateUrl: './kategorie-editor.html',
  styleUrl: './kategorie-editor.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KategorieEditor {
  private readonly store = inject(Store);

  readonly category = input.required<ClassificationCategory>();

  readonly newLabelName = signal<string>('');
  readonly renamingLabelId = signal<number | null>(null);
  readonly renameDraftText = signal<string>('');
  readonly expandedLabelId = signal<number | null>(null);
  readonly clipPromptsDraft = signal<string>('');
  readonly wd14TagsDraft = signal<string>('');

  readonly sortedLabels = computed((): ClassificationLabel[] =>
    [...this.category().labels].sort((a: ClassificationLabel, b: ClassificationLabel) => a.position - b.position)
  );

  setMode(mode: ClassificationMode): void {
    if (this.category().mode === mode) { return; }
    this.store.dispatch(classificationActions.patchCategory({ id: this.category().id, patch: { mode } }));
  }

  addLabel(): void {
    const name = this.newLabelName().trim();
    if (!name) { return; }
    this.store.dispatch(classificationActions.createLabel({ categoryId: this.category().id, name }));
    this.newLabelName.set('');
  }

  onNewLabelKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.addLabel(); }
  }

  startLabelRename(label: ClassificationLabel): void {
    this.renamingLabelId.set(label.id);
    this.renameDraftText.set(label.name);
  }

  confirmLabelRename(): void {
    const id = this.renamingLabelId();
    const name = this.renameDraftText().trim();
    if (id != null && name) {
      this.store.dispatch(classificationActions.patchLabel({
        id,
        categoryId: this.category().id,
        patch: { name },
      }));
    }
    this.renamingLabelId.set(null);
  }

  cancelLabelRename(): void {
    this.renamingLabelId.set(null);
  }

  onLabelRenameKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmLabelRename(); }
    else if (event.key === 'Escape') { this.cancelLabelRename(); }
  }

  deleteLabel(label: ClassificationLabel): void {
    const confirmed = window.confirm(`Label „${label.name}" löschen?`);
    if (!confirmed) { return; }
    this.store.dispatch(classificationActions.deleteLabel({ id: label.id, categoryId: this.category().id }));
  }

  isExpanded(label: ClassificationLabel): boolean {
    return this.expandedLabelId() === label.id;
  }

  toggleExpanded(label: ClassificationLabel): void {
    if (this.isExpanded(label)) {
      this.expandedLabelId.set(null);
      return;
    }
    this.expandedLabelId.set(label.id);
    this.clipPromptsDraft.set((label.clip_prompts ?? []).join(', '));
    this.wd14TagsDraft.set((label.wd14_tags ?? []).join(', '));
  }

  private parseCommaList(value: string): string[] | null {
    const items = value
      .split(',')
      .map((item: string) => item.trim())
      .filter((item: string) => item.length > 0);
    return items.length > 0 ? items : null;
  }

  saveAdvanced(label: ClassificationLabel): void {
    this.store.dispatch(classificationActions.patchLabel({
      id: label.id,
      categoryId: this.category().id,
      patch: {
        clip_prompts: this.parseCommaList(this.clipPromptsDraft()),
        wd14_tags: this.parseCommaList(this.wd14TagsDraft()),
      },
    }));
  }
}
