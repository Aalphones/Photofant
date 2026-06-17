import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import type { TagListItem } from '@photofant/models';
import { tagsActions, tagsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-tags',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './tags.html',
  styleUrl: './tags.scss',
})
export class Tags {
  private readonly store = inject(Store);

  protected readonly allTags   = this.store.selectSignal(tagsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(tagsSelectors.selectIsLoading);

  protected readonly searchQuery = signal('');

  protected readonly filteredTags = computed((): TagListItem[] => {
    const query = this.searchQuery().toLowerCase().trim();
    if (!query) { return this.allTags(); }
    return this.allTags().filter((tag: TagListItem) =>
      tag.name.includes(query)
    );
  });

  // ── Rename ───────────────────────────────────────────────────────────────

  protected readonly renamingId  = signal<number | null>(null);
  protected readonly renameDraft = signal('');

  // ── Merge ────────────────────────────────────────────────────────────────

  protected readonly mergeSelected = signal<Set<number>>(new Set());
  protected readonly showMergeDialog = signal(false);
  protected readonly mergeTargetId   = signal<number | null>(null);

  protected readonly mergeSelectedTags = computed((): TagListItem[] => {
    const ids = this.mergeSelected();
    return this.allTags().filter((tag: TagListItem) => ids.has(tag.id));
  });

  constructor() {
    this.store.dispatch(tagsActions.load());
  }

  protected startRename(tag: TagListItem): void {
    this.renamingId.set(tag.id);
    this.renameDraft.set(tag.name);
  }

  protected confirmRename(): void {
    const id   = this.renamingId();
    const name = this.renameDraft().trim();
    if (id != null && name) {
      this.store.dispatch(tagsActions.rename({ id, name }));
    }
    this.renamingId.set(null);
  }

  protected cancelRename(): void {
    this.renamingId.set(null);
  }

  protected onRenameKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmRename(); }
    else if (event.key === 'Escape') { this.cancelRename(); }
  }

  protected toggleMergeSelect(id: number): void {
    this.mergeSelected.update((selected: Set<number>) => {
      const next = new Set(selected);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }

  protected isMergeSelected(id: number): boolean {
    return this.mergeSelected().has(id);
  }

  protected openMergeDialog(): void {
    if (this.mergeSelected().size < 2) { return; }
    // Default target = first selected tag (highest count, sorted by adapter)
    const ids = [...this.mergeSelected()];
    this.mergeTargetId.set(ids[0] ?? null);
    this.showMergeDialog.set(true);
  }

  protected setMergeTarget(id: number): void {
    this.mergeTargetId.set(id);
  }

  protected confirmMerge(): void {
    const intoId   = this.mergeTargetId();
    const selected = [...this.mergeSelected()];
    if (intoId == null) { return; }
    const fromIds = selected.filter((id: number) => id !== intoId);
    this.store.dispatch(tagsActions.merge({ from_ids: fromIds, into_id: intoId }));
    this.mergeSelected.set(new Set());
    this.showMergeDialog.set(false);
  }

  protected cancelMerge(): void {
    this.showMergeDialog.set(false);
  }

  protected clearMergeSelection(): void {
    this.mergeSelected.set(new Set());
  }
}
