import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { AssetDto, AssetsPage, Collection, CollectionDetail } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { collectionsActions, collectionsSelectors, galleryActions, gallerySelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';
import { Lightbox } from '../galerie/lightbox/lightbox';
import { AlbumSettings } from './album-settings/album-settings';
import { AlbumGrid } from './album-grid/album-grid';

@Component({
  selector: 'pf-alben',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, AlbumSettings, Lightbox, AlbumGrid],
  templateUrl: './alben.html',
  styleUrl: './alben.scss',
})
export class Alben {
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly collections = this.store.selectSignal(collectionsSelectors.selectAll);
  protected readonly detail = this.store.selectSignal(collectionsSelectors.selectDetail);
  protected readonly isLoading = this.store.selectSignal(collectionsSelectors.selectIsLoading);

  protected readonly selectedId = signal<number | null>(null);
  protected readonly members = signal<AssetDto[]>([]);
  protected readonly settingsOpen = signal(false);

  protected readonly lightboxId = this.store.selectSignal(gallerySelectors.selectLightboxId);

  protected readonly creating = signal(false);
  protected readonly newName = signal('');

  protected readonly openCollection = computed((): CollectionDetail | null => {
    const detail = this.detail();
    return detail && detail.id === this.selectedId() ? detail : null;
  });

  // Manuelle Reihenfolge + gewähltes Cover (P10 Phase 1) — Original-`members()` ist
  // datumssortiert; hier einmal zentral nach `item_order`/`cover_asset_id` umsortiert,
  // damit Grid, Header-Cover und die Reihenfolge-Sektion in den Einstellungen dieselbe
  // Sicht teilen statt jeweils eigene Sortierlogik zu pflegen.
  protected readonly orderedMembers = computed((): AssetDto[] => {
    const collection = this.openCollection();
    const list = this.members();
    if (collection == null) { return list; }

    const byId = new Map(list.map((asset: AssetDto) => [asset.id, asset]));
    const ordered = collection.item_order
      .map((id: number) => byId.get(id))
      .filter((asset): asset is AssetDto => asset != null);
    const seen = new Set(ordered.map((asset: AssetDto) => asset.id));
    const rest = list.filter((asset: AssetDto) => !seen.has(asset.id));
    const result = [...ordered, ...rest];

    const coverId = collection.cover_asset_id;
    if (coverId == null) { return result; }
    const coverIndex = result.findIndex((asset: AssetDto) => asset.id === coverId);
    if (coverIndex <= 0) { return result; }
    const cover = result[coverIndex];
    if (cover == null) { return result; }
    result.splice(coverIndex, 1);
    return [cover, ...result];
  });

  private lastFetchedId = -1;
  private lastFetchedCount = -1;

  constructor() {
    this.store.dispatch(collectionsActions.load());

    // Re-fetch member thumbnails when the album changes or its membership count shifts
    // (the latter happens after a re-evaluation job completes).
    effect((): void => {
      const id = this.selectedId();
      if (id == null) {
        this.members.set([]);
        return;
      }
      const detail = this.detail();
      const count = detail && detail.id === id ? detail.member_count : -1;
      if (this.lastFetchedId !== id || this.lastFetchedCount !== count) {
        this.lastFetchedId = id;
        this.lastFetchedCount = count;
        this.fetchMembers(id);
      }
    });
  }

  private fetchMembers(collectionId: number): void {
    this.assetService
      .listAssets({ page: 1, page_size: 200, sort: 'date', order: 'desc', collectionId })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((page: AssetsPage) => this.members.set(page.items));
  }

  protected open(id: number): void {
    this.selectedId.set(id);
    this.settingsOpen.set(false);
    this.store.dispatch(collectionsActions.loadDetail({ id }));
  }

  protected back(): void {
    this.selectedId.set(null);
    this.settingsOpen.set(false);
    this.store.dispatch(collectionsActions.clearDetail());
  }

  protected toggleSettings(): void {
    this.settingsOpen.update((open: boolean) => !open);
  }

  protected startCreate(): void {
    this.creating.set(true);
    this.newName.set('');
  }

  protected confirmCreate(): void {
    const name = this.newName().trim();
    if (name) {
      this.store.dispatch(collectionsActions.create({ request: { name } }));
    }
    this.creating.set(false);
    this.newName.set('');
  }

  protected onCreateKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmCreate(); }
    else if (event.key === 'Escape') { this.creating.set(false); }
  }

  protected openMember(assetId: number): void {
    this.store.dispatch(galleryActions.setLightboxContext({ assets: this.orderedMembers() }));
    this.store.dispatch(galleryActions.openLightbox({ id: assetId }));
  }

  protected deleteOpen(): void {
    const id = this.selectedId();
    if (id == null) { return; }
    this.store.dispatch(collectionsActions.delete({ id }));
    this.back();
  }

  protected thumbnailUrl(assetOrId: { id: number; content_hash: string } | number): string {
    if (typeof assetOrId === 'number') {
      return this.assetService.thumbnailUrl(assetOrId, 256);
    }
    return this.assetService.thumbnailUrl(assetOrId.id, 256, assetOrId.content_hash);
  }

  protected isSmart(collection: Collection): boolean {
    return collection.kind === 'smart_album';
  }
}
