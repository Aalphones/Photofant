import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { TagListItem } from '@photofant/models';
import { tagsActions, tagsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen-tags',
  imports: [Icon],
  templateUrl: './tags.html',
  styleUrl: './tags.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tags {
  private readonly store = inject(Store);

  private readonly allTagsList = this.store.selectSignal(tagsSelectors.selectAll);
  readonly isTagsLoading = this.store.selectSignal(tagsSelectors.selectIsLoading);
  readonly tagSearchQuery = signal<string>('');
  readonly filteredTagsList = computed((): TagListItem[] => {
    const query = this.tagSearchQuery().toLowerCase().trim();
    if (!query) { return this.allTagsList(); }
    return this.allTagsList().filter((tag: TagListItem) => tag.name.includes(query));
  });
  readonly renamingTagId = signal<number | null>(null);
  readonly renameDraftText = signal<string>('');
  readonly tagMergeSelected = signal<Set<number>>(new Set());
  readonly showTagMergeDialog = signal<boolean>(false);
  readonly tagMergeTargetId = signal<number | null>(null);
  readonly tagMergeSelectedTags = computed((): TagListItem[] => {
    const ids = this.tagMergeSelected();
    return this.allTagsList().filter((tag: TagListItem) => ids.has(tag.id));
  });
  readonly editingAliasTagId = signal<number | null>(null);
  readonly aliasDraftText = signal<string>('');
  readonly tagNameById = computed((): Map<number, string> => {
    const map = new Map<number, string>();
    for (const tag of this.allTagsList()) {
      map.set(tag.id, tag.name);
    }
    return map;
  });

  constructor() {
    effect(() => {
      this.store.dispatch(tagsActions.load());
    });
  }

  startTagRename(tag: TagListItem): void {
    this.renamingTagId.set(tag.id);
    this.renameDraftText.set(tag.name);
  }

  confirmTagRename(): void {
    const id = this.renamingTagId();
    const name = this.renameDraftText().trim();
    if (id != null && name) {
      this.store.dispatch(tagsActions.rename({ id, name }));
    }
    this.renamingTagId.set(null);
  }

  cancelTagRename(): void {
    this.renamingTagId.set(null);
  }

  onTagRenameKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmTagRename(); }
    else if (event.key === 'Escape') { this.cancelTagRename(); }
  }

  toggleTagMergeSelect(tagId: number): void {
    this.tagMergeSelected.update((selected: Set<number>) => {
      const next = new Set(selected);
      if (next.has(tagId)) { next.delete(tagId); } else { next.add(tagId); }
      return next;
    });
  }

  isTagMergeSelected(tagId: number): boolean {
    return this.tagMergeSelected().has(tagId);
  }

  openTagMergeDialog(): void {
    if (this.tagMergeSelected().size < 2) { return; }
    const ids = [...this.tagMergeSelected()];
    this.tagMergeTargetId.set(ids[0] ?? null);
    this.showTagMergeDialog.set(true);
  }

  setTagMergeTarget(tagId: number): void {
    this.tagMergeTargetId.set(tagId);
  }

  confirmTagMerge(): void {
    const intoId = this.tagMergeTargetId();
    const selected = [...this.tagMergeSelected()];
    if (intoId == null) { return; }
    const fromIds = selected.filter((id: number) => id !== intoId);
    this.store.dispatch(tagsActions.merge({ from_ids: fromIds, into_id: intoId }));
    this.tagMergeSelected.set(new Set());
    this.showTagMergeDialog.set(false);
  }

  cancelTagMerge(): void {
    this.showTagMergeDialog.set(false);
  }

  clearTagMergeSelection(): void {
    this.tagMergeSelected.set(new Set());
  }

  startAliasEdit(tag: TagListItem): void {
    if (tag.alias_of != null) { return; }
    this.editingAliasTagId.set(tag.id);
    this.aliasDraftText.set(tag.aliases.join(', '));
  }

  confirmAliasEdit(): void {
    const id = this.editingAliasTagId();
    if (id == null) { return; }
    const names = this.aliasDraftText()
      .split(',')
      .map((name: string) => name.trim())
      .filter((name: string) => name.length > 0);
    this.store.dispatch(tagsActions.setAliases({ id, names }));
    this.editingAliasTagId.set(null);
  }

  cancelAliasEdit(): void {
    this.editingAliasTagId.set(null);
  }

  onAliasKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmAliasEdit(); }
    else if (event.key === 'Escape') { this.cancelAliasEdit(); }
  }
}
