import {
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  inject,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { Store } from '@ngrx/store';
import type { TagFacetItem } from '@photofant/models';
import { collectionsSelectors, filtersActions, filtersSelectors, gallerySelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-filter-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, DecimalPipe],
  templateUrl: './filter-rail.html',
  styleUrl: './filter-rail.scss',
})
export class FilterRail {
  private readonly store = inject(Store);

  readonly close = output<void>();

  protected readonly facets       = this.store.selectSignal(gallerySelectors.selectFacets);
  protected readonly sources      = this.store.selectSignal(filtersSelectors.sources);
  protected readonly qualityMin   = this.store.selectSignal(filtersSelectors.qualityMin);
  protected readonly tagIds       = this.store.selectSignal(filtersSelectors.tagIds);
  protected readonly collections  = this.store.selectSignal(collectionsSelectors.selectAll);
  protected readonly collectionId = this.store.selectSignal(filtersSelectors.collectionId);

  protected readonly tagQuery = signal('');

  protected readonly filteredTags = computed((): TagFacetItem[] => {
    const query = this.tagQuery().toLowerCase();
    const all = this.facets()?.tags_top ?? [];
    return query
      ? all.filter((tag: TagFacetItem) => tag.name.includes(query)).slice(0, 30)
      : all.slice(0, 12);
  });

  // Accordion open/close state per facet
  protected readonly openQuelle    = signal(true);
  protected readonly openQualitaet = signal(true);
  protected readonly openTags      = signal(true);
  protected readonly openSammlung  = signal(true);

  // Slider drag
  private readonly sliderTrackRef = viewChild<ElementRef<HTMLDivElement>>('sliderTrack');

  protected readonly SOURCE_LABELS: Record<string, string> = {
    original: 'Original',
    flux: 'Flux',
    sdxl: 'SDXL',
  };

  protected toggleSource(source: string): void {
    const current = this.sources();
    const next = current.includes(source)
      ? current.filter((s: string) => s !== source)
      : [...current, source];
    this.store.dispatch(filtersActions.setSources({ sources: next }));
  }

  protected setQualityMin(qualityMin: number): void {
    this.store.dispatch(filtersActions.setQualityMin({ qualityMin }));
  }

  protected toggleTag(tagId: number): void {
    const current = this.tagIds();
    const next = current.includes(tagId)
      ? current.filter((id: number) => id !== tagId)
      : [...current, tagId];
    this.store.dispatch(filtersActions.setTagIds({ tagIds: next }));
  }

  protected toggleCollection(collectionId: number): void {
    const next = this.collectionId() === collectionId ? null : collectionId;
    this.store.dispatch(filtersActions.setCollectionId({ collectionId: next }));
  }

  protected sourceFacetCount(source: string): number {
    return this.facets()?.sources.find((f) => f.value === source)?.count ?? 0;
  }

  protected sliderMouseDown(event: MouseEvent): void {
    const trackEl = this.sliderTrackRef()?.nativeElement;
    if (!trackEl) return;

    const rect = trackEl.getBoundingClientRect();
    const clamp = (x: number): number => Math.min(1, Math.max(0, x));
    const fromEvent = (ev: MouseEvent): number =>
      Math.round(clamp((ev.clientX - rect.left) / rect.width) * 100) / 100;

    this.setQualityMin(fromEvent(event));

    const onMove = (moveEvent: MouseEvent): void => {
      this.setQualityMin(fromEvent(moveEvent));
    };
    const onUp = (): void => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }
}
