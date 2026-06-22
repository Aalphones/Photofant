import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { Store } from '@ngrx/store';
import type { Collection, Density, GroupKey, PersonDto, SortKey, SortOrder, TagFacetItem } from '@photofant/models';
import { collectionsSelectors, filtersActions, filtersSelectors, gallerySelectors, personsSelectors, presetsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

interface FilterChip {
  kind: 'source' | 'qualityMin' | 'tag' | 'collection' | 'person';
  chipKey: string;
  label: string;
  id?: number;
  value?: string;
  thumbnailUrl?: string;
}

@Component({
  selector: 'pf-sub-toolbar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './sub-toolbar.html',
  styleUrl: './sub-toolbar.scss',
})
export class SubToolbar {
  private readonly store           = inject(Store);

  readonly railToggle      = output<void>();
  readonly selToggle       = output<void>();
  readonly workflowToggle  = output<void>();

  readonly selectionMode  = input<boolean>(false);
  readonly workflowMode   = input<boolean>(false);

  protected readonly total      = this.store.selectSignal(gallerySelectors.selectServerTotal);
  protected readonly sort       = this.store.selectSignal(filtersSelectors.sort);
  protected readonly order      = this.store.selectSignal(filtersSelectors.order);
  protected readonly group      = this.store.selectSignal(filtersSelectors.group);
  protected readonly density    = this.store.selectSignal(filtersSelectors.density);
  protected readonly presets    = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly sources    = this.store.selectSignal(filtersSelectors.sources);
  protected readonly qualityMin = this.store.selectSignal(filtersSelectors.qualityMin);
  protected readonly tagIds     = this.store.selectSignal(filtersSelectors.tagIds);
  protected readonly collectionId = this.store.selectSignal(filtersSelectors.collectionId);
  protected readonly personId     = this.store.selectSignal(filtersSelectors.personId);
  protected readonly collections  = this.store.selectSignal(collectionsSelectors.selectAll);
  protected readonly persons      = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly facets       = this.store.selectSignal(gallerySelectors.selectFacets);

  protected readonly SOURCE_LABELS: Record<string, string> = {
    original: 'Original',
    flux: 'Flux',
    sdxl: 'SDXL',
  };

  protected readonly chips = computed((): FilterChip[] => {
    const result: FilterChip[] = [];
    for (const source of this.sources()) {
      result.push({ kind: 'source', chipKey: 'Quelle', label: this.SOURCE_LABELS[source] ?? source, value: source });
    }
    if (this.qualityMin() > 0) {
      result.push({ kind: 'qualityMin', chipKey: 'Qualität', label: `≥ ${Math.round(this.qualityMin() * 100)}` });
    }
    const tags = this.facets()?.tags_top ?? [];
    for (const tagId of this.tagIds()) {
      const tag = tags.find((t: TagFacetItem) => t.id === tagId);
      result.push({ kind: 'tag', chipKey: 'Tag', label: tag?.name ?? `${tagId}`, id: tagId });
    }
    const collectionId = this.collectionId();
    if (collectionId != null) {
      const collection = this.collections().find((c: Collection) => c.id === collectionId);
      result.push({ kind: 'collection', chipKey: 'Album', label: collection?.name ?? `${collectionId}`, id: collectionId });
    }
    const personId = this.personId();
    if (personId != null) {
      const person = this.persons().find((p: PersonDto) => p.id === personId);
      const label = person?.name ?? `Person #${personId}`;
      const portraitFaceId = person?.portrait_face_id;
      result.push({
        kind: 'person',
        chipKey: 'Person',
        label,
        id: personId,
        ...(portraitFaceId != null ? { thumbnailUrl: `/api/faces/${portraitFaceId}/thumbnail` } : {}),
      });
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
    } else if (chip.kind === 'collection') {
      this.store.dispatch(filtersActions.setCollectionId({ collectionId: null }));
    } else if (chip.kind === 'person') {
      this.store.dispatch(filtersActions.setPersonId({ personId: null }));
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
}
