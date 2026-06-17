import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { Density, GroupKey, SortKey, SortOrder } from '@photofant/models';
import { filtersActions, filtersSelectors, gallerySelectors } from '@photofant/store';
import { ClassifyService } from '@photofant/services';
import type { ClassifyStep } from '@photofant/services';
import { Icon, RerunDialog } from '@photofant/ui';

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

  protected readonly showRerunAllDialog = signal(false);

  protected readonly total   = this.store.selectSignal(gallerySelectors.selectTotal);
  protected readonly sort    = this.store.selectSignal(filtersSelectors.sort);
  protected readonly order   = this.store.selectSignal(filtersSelectors.order);
  protected readonly group   = this.store.selectSignal(filtersSelectors.group);
  protected readonly density = this.store.selectSignal(filtersSelectors.density);

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
    this.showRerunAllDialog.set(true);
  }

  protected onRerunAllConfirm(steps: ClassifyStep[]): void {
    this.showRerunAllDialog.set(false);
    this.classifyService.rerun({ asset_ids: 'all', steps }).subscribe();
  }

  protected onRerunAllCancel(): void {
    this.showRerunAllDialog.set(false);
  }
}
