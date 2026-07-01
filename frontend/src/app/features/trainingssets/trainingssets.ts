import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { AssetsPage, CaptionAction, CollectionDetail, TrainingSetItem, TrainingSetStats } from '@photofant/models';
import { AssetService, ClassifyService, CollectionService, ExportService } from '@photofant/services';
import { collectionsActions, collectionsSelectors, jobsSelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';
import { TrainingSetCaptions } from './training-set-captions/training-set-captions';
import { TrainingSetDupes } from './training-set-dupes/training-set-dupes';
import { TrainingSetExport } from './training-set-export/training-set-export';
import type { TrainingSetExportPayload } from './training-set-export/training-set-export';
import { TrainingSetItemCell } from './training-set-item/training-set-item';
import { TrainingSetSettingsPanel } from './training-set-settings/training-set-settings';
import { TrainingSetStatsPanel } from './training-set-stats/training-set-stats';

type SidePanel = 'none' | 'settings' | 'stats' | 'dupes';

@Component({
  selector: 'pf-trainingssets',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, TrainingSetItemCell, TrainingSetSettingsPanel, TrainingSetStatsPanel, TrainingSetCaptions, TrainingSetDupes, TrainingSetExport, RerunDialog],
  templateUrl: './trainingssets.html',
  styleUrl: './trainingssets.scss',
})
export class Trainingssets {
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);
  private readonly collectionService = inject(CollectionService);
  private readonly classifyService = inject(ClassifyService);
  private readonly exportService = inject(ExportService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly sets = this.store.selectSignal(collectionsSelectors.selectTrainingSets);
  protected readonly albums = this.store.selectSignal(collectionsSelectors.selectAlbums);
  protected readonly detail = this.store.selectSignal(collectionsSelectors.selectDetail);
  protected readonly isLoading = this.store.selectSignal(collectionsSelectors.selectIsLoading);
  protected readonly rerunPresets = this.store.selectSignal(presetsSelectors.selectPresets);
  private readonly allJobs = this.store.selectSignal(jobsSelectors.allJobs);

  protected readonly selectedId = signal<number | null>(null);
  protected readonly items = signal<TrainingSetItem[]>([]);
  protected readonly stats = signal<TrainingSetStats | null>(null);
  protected readonly sidePanel = signal<SidePanel>('none');
  protected readonly showRerunDialog = signal(false);
  protected readonly showCaptionsDialog = signal(false);
  protected readonly showExportDialog = signal(false);
  protected readonly exportToast = signal<string | null>(null);
  private exportToastTimer: ReturnType<typeof setTimeout> | null = null;

  protected readonly creating = signal(false);
  protected readonly newName = signal('');
  protected readonly cloneFromAlbumId = signal<number | null>(null);

  protected readonly openSet = computed((): CollectionDetail | null => {
    const detail = this.detail();
    return detail && detail.id === this.selectedId() ? detail : null;
  });

  private lastFetchedId = -1;
  private lastFetchedCount = -1;
  private pendingCaptionsJobId: string | null = null;

  constructor() {
    this.store.dispatch(collectionsActions.load());

    // Item-Liste neu laden, wenn ein anderes Set geöffnet wird oder sich die Mitgliederzahl
    // ändert (z.B. nach Bulk-Bar "Zu Trainingsset" oder Entfernen).
    effect((): void => {
      const id = this.selectedId();
      if (id == null) {
        this.items.set([]);
        return;
      }
      const detail = this.detail();
      const count = detail && detail.id === id ? detail.member_count : -1;
      if (this.lastFetchedId !== id || this.lastFetchedCount !== count) {
        this.lastFetchedId = id;
        this.lastFetchedCount = count;
        this.fetchItems(id);
      }
    });

    // Caption-Tool läuft als Queue-Job (Critical Rule 5) — Items erst neu laden, wenn er durch ist.
    effect((): void => {
      const jobId = this.pendingCaptionsJobId;
      if (jobId == null) { return; }
      const job = this.allJobs().find((current) => current.id === jobId);
      if (job != null && job.state === 'done') {
        this.pendingCaptionsJobId = null;
        const id = this.selectedId();
        if (id != null) { this.fetchItems(id); }
      }
    });
  }

  private fetchItems(collectionId: number): void {
    this.collectionService.getItems(collectionId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((items: TrainingSetItem[]) => this.items.set(items));
  }

  private fetchStats(collectionId: number): void {
    this.collectionService.getStats(collectionId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((stats: TrainingSetStats) => this.stats.set(stats));
  }

  protected open(id: number): void {
    this.selectedId.set(id);
    this.sidePanel.set('none');
    this.store.dispatch(collectionsActions.loadDetail({ id }));
  }

  protected back(): void {
    this.selectedId.set(null);
    this.sidePanel.set('none');
    this.store.dispatch(collectionsActions.clearDetail());
  }

  protected toggleSettings(): void {
    this.sidePanel.update((panel: SidePanel) => (panel === 'settings' ? 'none' : 'settings'));
  }

  protected toggleStats(): void {
    const opening = this.sidePanel() !== 'stats';
    this.sidePanel.update((panel: SidePanel) => (panel === 'stats' ? 'none' : 'stats'));
    const id = this.selectedId();
    if (opening && id != null) { this.fetchStats(id); }
  }

  protected toggleDupes(): void {
    this.sidePanel.update((panel: SidePanel) => (panel === 'dupes' ? 'none' : 'dupes'));
  }

  protected onDupesResolved(): void {
    const set = this.openSet();
    if (set == null) { return; }
    this.fetchItems(set.id);
    this.store.dispatch(collectionsActions.loadDetail({ id: set.id }));
  }

  protected deleteOpen(): void {
    const id = this.selectedId();
    if (id == null) { return; }
    this.store.dispatch(collectionsActions.delete({ id }));
    this.back();
  }

  protected startCreate(): void {
    this.creating.set(true);
    this.newName.set('');
    this.cloneFromAlbumId.set(null);
  }

  protected cancelCreate(): void {
    this.creating.set(false);
  }

  protected confirmCreate(): void {
    const name = this.newName().trim();
    if (!name) { this.creating.set(false); return; }
    const sourceAlbumId = this.cloneFromAlbumId();

    this.collectionService.createCollection({ name, kind: 'training_set' })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((created: CollectionDetail) => {
        if (sourceAlbumId == null) {
          this.store.dispatch(collectionsActions.load());
          return;
        }
        this.assetService
          .listAssets({ page: 1, page_size: 1000, sort: 'date', order: 'desc', collectionId: sourceAlbumId })
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe((page: AssetsPage) => {
            const assetIds = page.items.map((asset) => asset.id);
            if (assetIds.length === 0) {
              this.store.dispatch(collectionsActions.load());
              return;
            }
            this.collectionService.addItems(created.id, assetIds)
              .pipe(takeUntilDestroyed(this.destroyRef))
              .subscribe(() => this.store.dispatch(collectionsActions.load()));
          });
      });

    this.creating.set(false);
    this.newName.set('');
    this.cloneFromAlbumId.set(null);
  }

  protected onCreateKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.confirmCreate(); }
    else if (event.key === 'Escape') { this.creating.set(false); }
  }

  protected thumbnailUrl(item: TrainingSetItem): string {
    return this.assetService.thumbnailUrl(item.id, 256, item.content_hash);
  }

  protected thumbnailUrlForCover(cover: { id: number; content_hash: string }): string {
    return this.assetService.thumbnailUrl(cover.id, 256, cover.content_hash);
  }

  protected onCaptionSaved(item: TrainingSetItem, captionOverride: string | null): void {
    const set = this.openSet();
    if (set == null) { return; }
    this.items.update((list: TrainingSetItem[]) =>
      list.map((current) => (current.id === item.id
        ? { ...current, caption_override: captionOverride, effective_caption: captionOverride ?? current.caption }
        : current)));
    this.collectionService.updateItemCaption(set.id, item.id, captionOverride)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  protected onTagAdded(item: TrainingSetItem, name: string): void {
    const set = this.openSet();
    if (set == null) { return; }
    this.assetService.patchTags(item.id, [name], [])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.fetchItems(set.id));
  }

  protected onTagRemoved(item: TrainingSetItem, tagId: number): void {
    const set = this.openSet();
    if (set == null) { return; }
    this.assetService.patchTags(item.id, [], [tagId])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.fetchItems(set.id));
  }

  protected onItemRemoved(item: TrainingSetItem): void {
    const set = this.openSet();
    if (set == null) { return; }
    this.collectionService.removeItem(set.id, item.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.items.update((list: TrainingSetItem[]) => list.filter((current) => current.id !== item.id));
        this.store.dispatch(collectionsActions.loadDetail({ id: set.id }));
      });
  }

  protected onRerunOpen(): void {
    this.store.dispatch(presetsActions.loadPresets());
    this.showRerunDialog.set(true);
  }

  protected onRerunCancel(): void {
    this.showRerunDialog.set(false);
  }

  protected onRerunConfirm(payload: RerunPayload): void {
    this.showRerunDialog.set(false);
    const assetIds = this.items().map((item: TrainingSetItem) => item.id);
    if (assetIds.length === 0) { return; }
    this.classifyService.rerun({
      asset_ids: assetIds,
      steps: payload.steps,
      ...(payload.captionPresetId != null ? { caption_preset_id: payload.captionPresetId } : {}),
    }).subscribe();
  }

  protected onCaptionsOpen(): void {
    this.showCaptionsDialog.set(true);
  }

  protected onCaptionsCancel(): void {
    this.showCaptionsDialog.set(false);
  }

  protected onCaptionsApply(event: { action: CaptionAction; params: Record<string, string> }): void {
    this.showCaptionsDialog.set(false);
    const set = this.openSet();
    if (set == null) { return; }
    this.collectionService.applyCaptionAction(set.id, event.action, event.params)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(({ job_id }) => { this.pendingCaptionsJobId = job_id; });
  }

  protected onExportOpen(): void {
    this.showExportDialog.set(true);
  }

  protected onExportCancel(): void {
    this.showExportDialog.set(false);
  }

  protected onExportApply(payload: TrainingSetExportPayload): void {
    this.showExportDialog.set(false);
    const set = this.openSet();
    if (set == null) { return; }
    this.exportService.exportCollection(set.id, {
      sidecar: payload.sidecar,
      split_ratio: payload.splitRatio,
      ...(payload.targetDir ? { target_dir: payload.targetDir } : {}),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.showExportToast('Export gestartet — läuft im Hintergrund.'),
        error: () => this.showExportToast('Fehler beim Starten des Exports.'),
      });
  }

  private showExportToast(message: string): void {
    if (this.exportToastTimer != null) { clearTimeout(this.exportToastTimer); }
    this.exportToast.set(message);
    this.exportToastTimer = setTimeout(() => { this.exportToast.set(null); }, 4000);
  }
}
