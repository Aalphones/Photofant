import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { collectionsActions, collectionsSelectors, comfyuiActions, comfyuiSelectors, filtersActions, filtersSelectors, galleryActions, gallerySelectors, jobsActions, personsActions, personsSelectors, presetsActions, presetsSelectors, reviewActions, tagsActions } from '@photofant/store';
import { AssetService, ClassifyService, ComfyUIService, PersonService } from '@photofant/services';
import { GalerieGrid } from './grid/grid';
import { FaceGrid } from './face-grid/face-grid';
import { SubToolbar } from './sub-toolbar/sub-toolbar';
import { Lightbox } from './lightbox/lightbox';
import { FilterRail } from './filter-rail/filter-rail';
import { RunLeiste } from './run-leiste/run-leiste';
import type { RunFirePayload } from './run-leiste/run-leiste';
import { AssignPersonDialog, BulkBar, BulkEditDialog, ExportDialog, Icon, RerunDialog } from '@photofant/ui';
import type { BulkEditPayload, ExportDialogFilters, RerunPayload } from '@photofant/ui';

@Component({
  selector: 'pf-galerie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SubToolbar, GalerieGrid, FaceGrid, Lightbox, FilterRail, RunLeiste, Icon, BulkBar, BulkEditDialog, RerunDialog, ExportDialog, AssignPersonDialog, RouterLink],
  templateUrl: './galerie.html',
  styleUrl: './galerie.scss',
  host: { '(document:keydown.escape)': 'onEscape()' },
})
export class Galerie {
  private readonly store           = inject(Store);
  private readonly router          = inject(Router);
  private readonly route           = inject(ActivatedRoute);
  private readonly classifyService = inject(ClassifyService);
  private readonly assetService    = inject(AssetService);
  private readonly comfyuiService  = inject(ComfyUIService);
  private readonly personService   = inject(PersonService);
  private readonly destroyRef      = inject(DestroyRef);

  protected readonly groups        = this.store.selectSignal(gallerySelectors.selectGroups);
  protected readonly density       = this.store.selectSignal(filtersSelectors.density);
  protected readonly isLoading     = this.store.selectSignal(gallerySelectors.selectIsLoading);
  protected readonly hasMore       = this.store.selectSignal(gallerySelectors.selectHasMore);
  protected readonly lightboxId    = this.store.selectSignal(gallerySelectors.selectLightboxId);
  protected readonly lightboxKind  = this.store.selectSignal(gallerySelectors.selectLightboxKind);
  protected readonly selectionMode = this.store.selectSignal(gallerySelectors.selectSelectionMode);
  protected readonly selectedIds   = this.store.selectSignal(gallerySelectors.selectSelectedIds);
  private readonly allAssets       = this.store.selectSignal(gallerySelectors.selectAll);
  private readonly anchorId        = this.store.selectSignal(gallerySelectors.selectAnchorId);
  protected readonly mediaType     = this.store.selectSignal(filtersSelectors.mediaType);
  protected readonly faceItems     = this.store.selectSignal(gallerySelectors.selectFaceItems);
  protected readonly faceHasMore   = this.store.selectSignal(gallerySelectors.selectFaceHasMore);

  private readonly filterSources      = this.store.selectSignal(filtersSelectors.sources);
  private readonly filterQualityMin   = this.store.selectSignal(filtersSelectors.qualityMin);
  private readonly filterTagIds       = this.store.selectSignal(filtersSelectors.tagIds);
  private readonly filterCollectionId = this.store.selectSignal(filtersSelectors.collectionId);
  private readonly filterPersonId     = this.store.selectSignal(filtersSelectors.personId);
  private readonly filterFavourite    = this.store.selectSignal(filtersSelectors.favourite);
  private readonly filterSort         = this.store.selectSignal(filtersSelectors.sort);
  private readonly filterOrder        = this.store.selectSignal(filtersSelectors.order);

  protected readonly showExportDialog = signal(false);

  protected readonly exportFilters = computed((): ExportDialogFilters => ({
    sources:    this.filterSources(),
    qualityMin: this.filterQualityMin(),
    tagIds:     this.filterTagIds(),
    personId:   this.filterPersonId(),
    favourite:  this.filterFavourite(),
  }));

  protected readonly albums = this.store.selectSignal(collectionsSelectors.selectAlbums);
  protected readonly trainingSets = this.store.selectSignal(collectionsSelectors.selectTrainingSets);

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly railOpen = signal(false);
  protected readonly showBulkRerunDialog = signal(false);
  protected readonly showBulkEditDialog = signal(false);
  protected readonly showAssignPersonDialog = signal(false);
  protected readonly bulkRerunPresets = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly dupeScanToast = signal<string | null>(null);
  private dupeScanToastTimer: ReturnType<typeof setTimeout> | null = null;

  // --- Workflow-Modus (Run-Leiste) ---
  protected readonly activeWorkflows   = this.store.selectSignal(comfyuiSelectors.selectActiveWorkflows);
  protected readonly comfyConfig       = this.store.selectSignal(comfyuiSelectors.selectConfig);
  protected readonly workflowMode      = signal(false);
  protected readonly activeWorkflowId  = signal<string | null>(null);
  protected readonly slotBindings         = signal<Record<string, number | number[]>>({});
  protected readonly faceSlotBindings     = signal<Record<string, number | number[]>>({});
  protected readonly versionSlotBindings  = signal<Record<string, number | number[]>>({});
  protected readonly assetHashMap      = this.store.selectSignal(gallerySelectors.selectHashMap);
  protected readonly armedSlotKey      = signal<string | null>(null);
  protected readonly batchAxisKey      = signal<string | null>(null);
  protected readonly isFiring          = signal(false);
  protected readonly runToast          = signal<string | null>(null);
  private runToastTimer: ReturnType<typeof setTimeout> | null = null;

  protected readonly isArmed = computed((): boolean => this.armedSlotKey() !== null);

  protected readonly activeWorkflow = computed(() => {
    const workflowId = this.activeWorkflowId();
    if (workflowId === null) { return null; }
    return this.activeWorkflows().find((workflow) => workflow.key === workflowId) ?? null;
  });

  // Standard-Upscale-Workflow für die Bulk-Aktion (nur wenn ComfyUI aktiv + gesetzt + gültig).
  protected readonly upscaleWorkflow = computed(() => {
    const key = this.comfyConfig().defaultUpscale;
    if (!key) { return null; }
    return this.activeWorkflows().find((workflow) => workflow.key === key) ?? null;
  });

  protected readonly canBulkUpscale = computed((): boolean =>
    this.comfyConfig().enabled && this.upscaleWorkflow() != null
  );

  protected readonly isEmpty = computed((): boolean => {
    if (this.mediaType() === 'faces') {
      return !this.isLoading() && this.faceItems().length === 0;
    }
    return !this.isLoading() && this.groups().length === 0;
  });

  protected readonly selectedCount = computed((): number => this.selectedIds().length);

  constructor() {
    // Always clear favourite filter when entering gallery — Favoriten-View locks it to true
    this.store.dispatch(filtersActions.setFavourite({ favourite: null }));

    // URL → store: apply filter params from URL on load
    const qp = this.route.snapshot.queryParamMap;
    const urlSources = (qp.get('sources') ?? '').split(',').filter(Boolean);
    const urlQMin    = parseFloat(qp.get('q_min') ?? '0') || 0;
    const urlTagIds  = (qp.get('tags') ?? '').split(',').map(Number).filter((n: number) => n > 0);
    const urlCollection = Number(qp.get('collection') ?? '') || 0;
    const urlPersonId   = Number(qp.get('person') ?? '') || 0;

    if (urlSources.length) this.store.dispatch(filtersActions.setSources({ sources: urlSources }));
    if (urlQMin > 0)       this.store.dispatch(filtersActions.setQualityMin({ qualityMin: urlQMin }));
    if (urlTagIds.length)  this.store.dispatch(filtersActions.setTagIds({ tagIds: urlTagIds }));
    if (urlCollection > 0) this.store.dispatch(filtersActions.setCollectionId({ collectionId: urlCollection }));
    if (urlPersonId > 0) {
      this.store.dispatch(filtersActions.setPersonId({ personId: urlPersonId }));
      this.store.dispatch(personsActions.loadPersons());
    }

    this.store.dispatch(collectionsActions.load());
    this.store.dispatch(galleryActions.requestPage());
    // Config + Workflows laden, damit Bulk-Upscale die Default-Zuordnung kennt.
    this.store.dispatch(comfyuiActions.loadConfig());
    this.store.dispatch(comfyuiActions.loadWorkflows());

    // store → URL: keep query params in sync
    effect((): void => {
      const params: Record<string, string> = {};
      const sources      = this.filterSources();
      const qualityMin   = this.filterQualityMin();
      const tagIds       = this.filterTagIds();
      const collectionId = this.filterCollectionId();
      const personId     = this.filterPersonId();
      const sort         = this.filterSort();
      const order        = this.filterOrder();

      if (sources.length)       params['sources']    = sources.join(',');
      if (qualityMin > 0)       params['q_min']      = String(qualityMin);
      if (tagIds.length)        params['tags']       = tagIds.join(',');
      if (collectionId != null) params['collection'] = String(collectionId);
      if (personId != null)     params['person']     = String(personId);
      if (sort !== 'date')      params['sort']       = sort;
      if (order !== 'desc')     params['order']      = order;

      void this.router.navigate([], {
        queryParams: params,
        replaceUrl: true,
        relativeTo: this.route,
      });
    });
  }

  protected onLoadMore(): void {
    if (!this.isLoading() && this.hasMore()) {
      this.store.dispatch(galleryActions.requestNextPage());
    }
  }

  protected onFaceLoadMore(): void {
    if (!this.isLoading() && this.faceHasMore()) {
      this.store.dispatch(galleryActions.requestNextPage());
    }
  }

  // Face-Stapel-Klick öffnet die vereinheitlichte Lightbox im Gesichter-Modus (P15 Phase 7);
  // versionId (Stapel-Version, Phase 3) wählt darin die initiale Stage-Version.
  protected onOpenFace(event: { faceId: number; assetId: number | null; versionId: number | null }): void {
    this.store.dispatch(galleryActions.openFaceLightbox({
      faceId: event.faceId, assetId: event.assetId, versionId: event.versionId,
    }));
  }

  protected onBindFace(event: { faceId: number; assetId: number | null }): void {
    const armedKey = this.armedSlotKey();
    if (armedKey === null) { return; }
    // Gesicht direkt binden — unabhängig davon ob ein Quell-Asset existiert
    const currentAssetBindings = { ...this.slotBindings() };
    delete currentAssetBindings[armedKey];
    this.slotBindings.set(currentAssetBindings);
    if (this.batchAxisKey() === armedKey) { this.batchAxisKey.set(null); }
    this.faceSlotBindings.set({ ...this.faceSlotBindings(), [armedKey]: event.faceId });
    this.armedSlotKey.set(null);
  }

  protected onOpenAsset(event: { id: number; versionId: number | null }): void {
    this.store.dispatch(galleryActions.openLightbox({ id: event.id, versionId: event.versionId }));
  }

  protected toggleSelectionMode(): void {
    if (this.selectionMode()) {
      this.store.dispatch(galleryActions.disableSelectionMode());
    } else {
      this.store.dispatch(galleryActions.enableSelectionMode());
    }
  }

  protected onSelectAll(ids: number[]): void {
    this.store.dispatch(galleryActions.selectAll({ ids }));
  }

  protected onRangeSelect(targetId: number): void {
    const anchorId = this.anchorId();
    if (anchorId === null) {
      this.store.dispatch(galleryActions.toggleSelected({ id: targetId }));
      return;
    }
    const assets = this.allAssets();
    const anchorIndex = assets.findIndex((asset) => asset.id === anchorId);
    const targetIndex = assets.findIndex((asset) => asset.id === targetId);
    if (anchorIndex === -1 || targetIndex === -1) {
      this.store.dispatch(galleryActions.toggleSelected({ id: targetId }));
      return;
    }
    const start = Math.min(anchorIndex, targetIndex);
    const end = Math.max(anchorIndex, targetIndex);
    const rangeIds = assets.slice(start, end + 1).map((asset) => asset.id);
    this.store.dispatch(galleryActions.selectRange({ ids: rangeIds }));
  }

  protected onBulkClose(): void {
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkTag(payload: { add: string[]; remove: number[] }): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(tagsActions.bulkTag({
      asset_ids: ids,
      add: payload.add,
      remove: payload.remove,
    }));
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onAddToAlbum(collectionId: number): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(collectionsActions.addItems({ collectionId, assetIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onAddToTrainingSet(collectionId: number): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(collectionsActions.addItems({ collectionId, assetIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkRerunOpen(): void {
    this.store.dispatch(presetsActions.loadPresets());
    this.showBulkRerunDialog.set(true);
  }

  protected onBulkRerunConfirm(payload: RerunPayload): void {
    this.showBulkRerunDialog.set(false);
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.classifyService.rerun({
      asset_ids: ids,
      steps: payload.steps,
      ...(payload.captionPresetId != null ? { caption_preset_id: payload.captionPresetId } : {}),
    }).subscribe();
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkRerunCancel(): void {
    this.showBulkRerunDialog.set(false);
  }

  protected onBulkDupeScan(): void {
    const ids = this.selectedIds();
    if (ids.length < 2) { return; }
    this.store.dispatch(reviewActions.triggerDupeScanSelection({ assetIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
    if (this.dupeScanToastTimer != null) { clearTimeout(this.dupeScanToastTimer); }
    this.dupeScanToast.set(`Duplikat-Scan für ${ids.length} Bilder gestartet`);
    this.dupeScanToastTimer = setTimeout(() => { this.dupeScanToast.set(null); }, 4000);
  }

  protected onBulkEditOpen(): void {
    this.showBulkEditDialog.set(true);
  }

  protected onBulkEditConfirm(payload: BulkEditPayload): void {
    this.showBulkEditDialog.set(false);
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.assetService.bulkEdit(ids, payload.op, payload.params).subscribe();
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkEditCancel(): void {
    this.showBulkEditDialog.set(false);
  }

  protected onBulkAssignPersonOpen(): void {
    this.store.dispatch(personsActions.loadPersons());
    this.showAssignPersonDialog.set(true);
  }

  protected onBulkAssignPersonConfirm(personId: number): void {
    this.showAssignPersonDialog.set(false);
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.personService.bulkAssignPerson(personId, ids)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.store.dispatch(jobsActions.toggleDock());
        this.store.dispatch(galleryActions.clearSelection());
      });
  }

  protected onBulkAssignPersonCancel(): void {
    this.showAssignPersonDialog.set(false);
  }

  protected onBulkUpscale(): void {
    const workflow = this.upscaleWorkflow();
    const ids = this.selectedIds();
    if (workflow == null || ids.length === 0) { return; }
    const imageSlot = workflow.inputs.find((input) => input.kind === 'image');
    if (imageSlot == null) { return; }
    // Default-Pfad: Backend importiert Ergebnis jedes Jobs automatisch als neue Version.
    this.comfyuiService.runDefaultWorkflow('upscale', {
      target_asset_ids: ids,
      inputs: { [imageSlot.key]: ids },
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: { jobs: { job_id: string }[] }) => {
          const count = response.jobs.length;
          this.showRunToast(`${count} Upscale-Job${count !== 1 ? 's' : ''} gestartet — Ergebnis wird automatisch importiert`);
        },
        error: (error: unknown) => {
          const message = error instanceof Error ? error.message : 'Fehler beim Senden an ComfyUI';
          this.showRunToast(`Fehler: ${message}`);
        },
      });
    this.store.dispatch(galleryActions.clearSelection());
  }

  protected onBulkTrash(): void {
    const ids = this.selectedIds();
    if (!ids.length) { return; }
    this.store.dispatch(galleryActions.clearSelection());
    this.assetService.bulkTrash(ids)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.store.dispatch(galleryActions.reset());
      });
  }

  // --- Workflow-Modus ---

  protected onEscape(): void {
    if (this.armedSlotKey() !== null) {
      this.armedSlotKey.set(null);
    }
  }

  protected toggleWorkflowMode(): void {
    if (this.workflowMode()) {
      this.resetWorkflowMode();
    } else {
      this.store.dispatch(comfyuiActions.loadWorkflows());
      this.workflowMode.set(true);
    }
  }

  protected onWorkflowChanged(workflowKey: string | null): void {
    const hasBindings =
      Object.keys(this.slotBindings()).length > 0 ||
      Object.keys(this.faceSlotBindings()).length > 0 ||
      Object.keys(this.versionSlotBindings()).length > 0;
    if (hasBindings && workflowKey !== this.activeWorkflowId()) {
      if (!window.confirm('Workflow wechseln? Alle aktuellen Bindungen werden gelöscht.')) {
        return;
      }
    }
    this.activeWorkflowId.set(workflowKey);
    this.slotBindings.set({});
    this.faceSlotBindings.set({});
    this.versionSlotBindings.set({});
    this.armedSlotKey.set(null);
    this.batchAxisKey.set(null);
  }

  protected onSlotArmed(slotKey: string | null): void {
    this.armedSlotKey.set(slotKey);
  }

  /** Galerie-Klick wenn ein Slot scharf: Einzelbild binden + entschärfen */
  protected onBindAsset(event: { id: number; versionId: number | null }): void {
    const assetId = event.id;
    const armedKey = this.armedSlotKey();
    if (armedKey === null) {
      this.onOpenAsset(event);
      return;
    }
    // Gesicht-Bindung für diesen Slot löschen (Asset überschreibt Gesicht)
    const currentFaceBindings = { ...this.faceSlotBindings() };
    delete currentFaceBindings[armedKey];
    this.faceSlotBindings.set(currentFaceBindings);

    const currentBindings = this.slotBindings();
    const updatedBindings = { ...currentBindings, [armedKey]: assetId };
    if (this.batchAxisKey() === armedKey) { this.batchAxisKey.set(null); }
    this.slotBindings.set(updatedBindings);
    this.armedSlotKey.set(null);
  }

  /** Strg+Klick wenn ein Slot scharf: zum Batch-Array hinzufügen */
  protected onBatchBindAsset(assetId: number): void {
    const armedKey = this.armedSlotKey();
    if (armedKey === null) { return; }

    // Gesicht-Bindung für diesen Slot löschen (Asset überschreibt Gesicht)
    const currentFaceBindings = { ...this.faceSlotBindings() };
    delete currentFaceBindings[armedKey];
    this.faceSlotBindings.set(currentFaceBindings);

    const currentBindings = this.slotBindings();
    const existing = currentBindings[armedKey];
    const existingArray = Array.isArray(existing)
      ? existing
      : existing != null ? [existing] : [];

    if (existingArray.includes(assetId)) { return; }

    const updatedArray = [...existingArray, assetId];

    // Batch-Achse verschieben wenn nötig (zweiter Slot bekommt Multi-Select)
    const previousBatchKey = this.batchAxisKey();
    if (previousBatchKey !== null && previousBatchKey !== armedKey) {
      const oldBatch = currentBindings[previousBatchKey];
      const oldFirst = Array.isArray(oldBatch) ? oldBatch[0] : oldBatch;
      this.slotBindings.set({
        ...currentBindings,
        [previousBatchKey]: oldFirst ?? 0,
        [armedKey]: updatedArray,
      });
      this.showBatchAxisHint();
    } else {
      this.slotBindings.set({ ...currentBindings, [armedKey]: updatedArray });
    }
    this.batchAxisKey.set(armedKey);
  }

  protected onRunFire(payload: RunFirePayload): void {
    if (this.isFiring()) { return; }
    this.isFiring.set(true);
    this.comfyuiService.runWorkflow(payload.workflowKey, payload.inputs, payload.faceInputs, {}, payload.versionInputs)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
      next: (response) => {
        this.isFiring.set(false);
        this.armedSlotKey.set(null);
        const count = response.jobs.length;
        this.showRunToast(`${count} Job${count !== 1 ? 's' : ''} an ComfyUI gesendet`);
      },
      error: (error: unknown) => {
        this.isFiring.set(false);
        const message = error instanceof Error ? error.message : 'Fehler beim Senden an ComfyUI';
        this.showRunToast(`Fehler: ${message}`);
      },
    });
  }

  protected resetWorkflowMode(): void {
    this.workflowMode.set(false);
    this.activeWorkflowId.set(null);
    this.slotBindings.set({});
    this.faceSlotBindings.set({});
    this.versionSlotBindings.set({});
    this.armedSlotKey.set(null);
    this.batchAxisKey.set(null);
  }

  private showRunToast(message: string): void {
    if (this.runToastTimer != null) { clearTimeout(this.runToastTimer); }
    this.runToast.set(message);
    this.runToastTimer = setTimeout(() => { this.runToast.set(null); }, 5000);
  }

  private showBatchAxisHint(): void {
    this.showRunToast('Batch-Achse verschoben — zweiter Slot übernimmt die Multi-Auswahl');
  }
}
