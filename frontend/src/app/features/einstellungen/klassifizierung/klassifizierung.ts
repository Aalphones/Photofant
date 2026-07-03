import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { ClassificationCategory } from '@photofant/models';
import { classificationActions, classificationSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';
import { KategorieEditor } from './kategorie-editor/kategorie-editor';

@Component({
  selector: 'pf-einstellungen-klassifizierung',
  imports: [Icon, KategorieEditor],
  templateUrl: './klassifizierung.html',
  styleUrl: './klassifizierung.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Klassifizierung {
  private readonly store = inject(Store);

  readonly categories = this.store.selectSignal(classificationSelectors.selectAll);
  readonly isLoading = this.store.selectSignal(classificationSelectors.selectIsLoading);

  readonly selectedCategoryId = signal<number | null>(null);

  readonly newCategoryName = signal<string>('');
  readonly renamingCategoryId = signal<number | null>(null);
  readonly renameDraftText = signal<string>('');

  readonly selectedCategory = computed((): ClassificationCategory | null => {
    const id = this.selectedCategoryId();
    if (id == null) { return null; }
    return this.categories().find((category: ClassificationCategory) => category.id === id) ?? null;
  });

  constructor() {
    effect(() => {
      this.store.dispatch(classificationActions.load());
    });

    effect(() => {
      const categories = this.categories();
      const firstCategory = categories[0];
      if (this.selectedCategoryId() == null && firstCategory != null) {
        this.selectedCategoryId.set(firstCategory.id);
      }
    });
  }

  selectCategory(category: ClassificationCategory): void {
    this.selectedCategoryId.set(category.id);
  }

  reclassifyAll(): void {
    this.store.dispatch(classificationActions.reclassifyAll());
  }

  addCategory(): void {
    const name = this.newCategoryName().trim();
    if (!name) { return; }
    this.store.dispatch(classificationActions.createCategory({ name, mode: 'single' }));
    this.newCategoryName.set('');
  }

  onNewCategoryKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.addCategory(); }
  }

  startCategoryRename(category: ClassificationCategory): void {
    this.renamingCategoryId.set(category.id);
    this.renameDraftText.set(category.name);
  }

  confirmCategoryRename(): void {
    const id = this.renamingCategoryId();
    const name = this.renameDraftText().trim();
    if (id != null && name) {
      this.store.dispatch(classificationActions.patchCategory({ id, patch: { name } }));
    }
    this.renamingCategoryId.set(null);
  }

  cancelCategoryRename(): void {
    this.renamingCategoryId.set(null);
  }

  onCategoryRenameKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmCategoryRename(); }
    else if (event.key === 'Escape') { this.cancelCategoryRename(); }
  }

  deleteCategory(category: ClassificationCategory): void {
    const confirmed = window.confirm(
      `Kategorie „${category.name}" löschen? Alle ${category.labels.length} Labels und bereits erkannte Klassen für diese Kategorie werden entfernt.`
    );
    if (!confirmed) { return; }
    if (this.selectedCategoryId() === category.id) {
      this.selectedCategoryId.set(null);
    }
    this.store.dispatch(classificationActions.deleteCategory({ id: category.id }));
  }
}
