import { ChangeDetectionStrategy, Component, computed, inject, output, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { Density, GroupKey, SortKey, SortOrder, TagFacetItem } from '@photofant/models';
import { filtersActions, filtersSelectors, gallerySelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { ClassifyService } from '@photofant/services';
import { Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';

interface FilterChip {
  kind: 'source' | 'qualityMin' | 'tag';
  label: string;
  id?: number;
  value?: string;
}

@Component({
  selector: 'pf-sub-toolbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, RerunDialog],
  templateUrl: './sub-toolbar.html',
  styleUrl: './sub-toolbar.scss',
})
export class SubToolbar {
  private readonly store           = inject(Store);
  private readonly classifyService = inject(ClassifyService);

  readonly railToggle = output<void>();

  protected readonly showRerunAllDialog = signal(false);

  protected readonly total      = this.store.selectSignal(gallerySelectors.selectServerTotal);
  protected readonly sort       = this.store.selectSignal(filtersSelectors.sort);
  protected readonly order      = this.store.selectSignal(filtersSelectors.order);
  protected readonly group      = this.store.selectSignal(filtersSelectors.group);
  protected readonly density    = this.store.selectSignal(filtersSelectors.density);
  protected readonly presets    = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly sources    = this.store.selectSignal(filtersSelectors.sources);
  protected readonly qualityMin = this.store.selectSignal(filtersSelectors.qualityMin);
  protected readonly tagIds     = this.store.selectSignal(filtersSelectors.tagIds);
  protected readonly facets     = this.store.selectSignal(gallerySelectors.selectFacets);

  protected readonly SOURCE_LABELS: Record<string, string> = {
    original: 'Original',
    flux: 'Flux',
    sdxl: 'SDXL',
  };

  protected readonly chips = computed((): FilterChip[] => {
    const result: FilterChip[] = [];
    for (const source of this.sources()) {
      result.push({ kind: 'source', label: this.SOURCE_LABELS[source] ?? source, value: source });
    }
    if (this.qualityMin() > 0) {
      result.push({ kind: 'qualityMin', label: `Qualität ≥ ${Math.round(this.qualityMin() * 100)}` });
    }
    const tags = this.facets()?.tags_top ?? [];
    for (const tagId of this.tagIds()) {
      const tag = tags.find((t: TagFacetItem) => t.id === tagId);
      result.push({ kind: 'tag', label: tag?.name ?? `Tag ${tagId}`, id: tagId });
    }
    return result;
  });

  protected readonly hasActiveFilters = computed((): boolean => this.chips().length > 0);

  protected readonly GROUPS: { key: GroupKey; label: string }[] = [
    { key: 'month',  label: 'Monat' },
    { key: 'person', label: 'Person' },
    { key: 'source', label: 'Quelle' },
  ];

  protected readonly DENSITIES: { key: Density; size: number }[] = [
    { key: 'sm', size: 13 },
    { key: 'md', size: 15 },
    { key: 'lg', size: 17 },
  ];

  protected removeChip(chip: FilterChip): void {
    if (chip.kind === 'source' && chip.value !== undefined) {
      const next = this.sources().filter((s: string) => s !== chip.value);
      this.store.dispatch(filtersActions.setSources({ sources: next }));
    } else if (chip.kind === 'qualityMin') {
      this.store.dispatch(filtersActions.setQualityMin({ qualityMin: 0 }));
    } else if (chip.kind === 'tag' && chip.id !== undefined) {
      const next = this.tagIds().filter((id: number) => id !== chip.id);
      this.store.dispatch(filtersActions.setTagIds({ tagIds: next }));
    }
  }

  protected clearAllFilters(): void {
    this.store.dispatch(filtersActions.clearAllFilters());
  }

  protected cycleSortKey(): void {
    const currentSort = this.sort();
    const currentOrder = this.order();
    let nextSort: SortKey;
    let nextOrder: SortOrder;

    if (currentSort === 'date') {
      nextSort = 'size';
      nextOrder = 'desc';
    } else if (currentOrder === 'desc') {
      nextSort = 'size';
      nextOrder = 'asc';
    } else {
      nextSort = 'date';
      nextOrder = 'desc';
    }

    this.store.dispatch(filtersActions.setSort({ sort: nextSort, order: nextOrder }));
  }

  protected setGroup(group: GroupKey): void {
    this.store.dispatch(filtersActions.setGroup({ group }));
  }

  protected setDensity(density: Density): void {
    this.store.dispatch(filtersActions.setDensity({ density }));
  }

  protected sortLabel(): string {
    return this.sort() === 'date' ? 'Datum' : 'Größe';
  }

  protected openRerunAllDialog(): void {
    this.store.dispatch(presetsActions.loadPresets());
    this.showRerunAllDialog.set(true);
  }

  protected onRerunAllConfirm(payload: RerunPayload): void {
    this.showRerunAllDialog.set(false);
    this.classifyService.rerun({
      asset_ids: 'all',
      steps: payload.steps,
      ...(payload.captionPresetId != null ? { caption_preset_id: payload.captionPresetId } : {}),
    }).subscribe();
  }

  protected onRerunAllCancel(): void {
    this.showRerunAllDialog.set(false);
  }
}
