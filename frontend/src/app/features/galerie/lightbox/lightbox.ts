import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { DOCUMENT } from '@angular/common';
import { combineLatest, of, switchMap } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import type { AssetDto, AssetSummary, DupePair, DupeResolution, FaceDto, FaceMatch, SimilarAsset, TagDto, TagListItem } from '@photofant/models';
import { AssetService, ClassifyService, PersonService, TagService } from '@photofant/services';
import { ShortcutService } from '../../../services/shortcut.service';
import { Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';
import { galleryActions, gallerySelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { ZoomStage } from './zoom-stage';
import { DupeCompare } from '../../review/review-dupes/dupe-compare/dupe-compare';

interface GenMetaEntry { key: string; value: string }

function extractGenMeta(meta: Record<string, unknown>): GenMetaEntry[] {
  const known: GenMetaEntry[] = [];
  const add = (label: string, ...keys: string[]): void => {
    for (const key of keys) {
      const value = meta[key];
      if (value != null && value !== '') {
        known.push({ key: label, value: String(value) });
        return;
      }
    }
  };
  add('Modell', 'model', 'checkpoint', 'ckpt_name');
  add('Sampler', 'sampler', 'sampler_name');
  add('Steps', 'steps', 'num_inference_steps');
  add('CFG', 'cfg', 'cfg_scale', 'guidance_scale');
  add('Seed', 'seed');
  add('Größe', 'size');
  add('Prompt', 'prompt', 'positive_prompt');
  return known;
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(1) + ' MB';
  if (bytes >= 1_024) return Math.round(bytes / 1_024) + ' KB';
  return bytes + ' B';
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(dateStr));
}

@Component({
  selector: 'pf-lightbox',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ZoomStage, Icon, RerunDialog, DupeCompare],
  templateUrl: './lightbox.html',
  styleUrl: './lightbox.scss',
})
export class Lightbox {
  private readonly store            = inject(Store);
  private readonly router           = inject(Router);
  private readonly assetService     = inject(AssetService);
  private readonly tagService       = inject(TagService);
  private readonly classifyService  = inject(ClassifyService);
  private readonly shortcutService  = inject(ShortcutService);
  private readonly document        = inject(DOCUMENT);
  private readonly personService    = inject(PersonService);
  private readonly destroyRef      = inject(DestroyRef);

  protected readonly showRerunDialog = signal(false);

  protected readonly asset    = this.store.selectSignal(gallerySelectors.selectLightboxAsset);
  protected readonly presets  = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly hasPrev  = this.store.selectSignal(gallerySelectors.selectLightboxHasPrev);
  protected readonly hasNext  = this.store.selectSignal(gallerySelectors.selectLightboxHasNext);

  protected readonly showGenMeta = signal(false);

  // Reload trigger: bump to force a fresh detail fetch
  private readonly reloadTrigger = signal(0);

  private readonly detail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]) =>
        asset != null ? this.assetService.getAsset(asset.id) : of(null)
      ),
    ),
  );

  // ── Tag autocomplete ──────────────────────────────────────────────────────

  protected readonly addingTag       = signal(false);
  protected readonly tagInputValue   = signal('');
  protected readonly tagSuggestions  = toSignal(
    toObservable(this.tagInputValue).pipe(
      switchMap((q: string) =>
        q.length >= 1 ? this.tagService.listTags(q, 8) : of([])
      ),
    ),
    { initialValue: [] as TagListItem[] },
  );

  // ── Caption editing ───────────────────────────────────────────────────────

  protected readonly editingCaption  = signal(false);
  protected readonly captionDraft    = signal('');

  // ── Similar assets overlay ────────────────────────────────────────────────

  protected readonly showSimilarOverlay  = signal(false);
  protected readonly similarLoading      = signal(false);
  protected readonly similarAssets       = signal<SimilarAsset[]>([]);
  protected readonly selectedSimilarPair = signal<DupePair | null>(null);

  // ── Face matches (person assignment) ─────────────────────────────────────
  protected readonly selectedFace       = signal<FaceDto | null>(null);
  protected readonly faceMatches        = signal<FaceMatch[]>([]);
  protected readonly faceMatchesLoading = signal(false);

  // ── Computed display ─────────────────────────────────────────────────────

  protected readonly displayTags = computed(() =>
    (this.detail()?.tags ?? []).filter((tag: TagDto) => !this.isTagHidden(tag.id))
  );

  protected readonly caption = computed((): string | null => this.detail()?.caption ?? null);

  protected readonly imageUrl = computed((): string => {
    const asset = this.asset();
    return asset != null ? this.assetService.fileUrl(asset.id) : '';
  });

  protected readonly genMeta = computed((): GenMetaEntry[] | null => {
    const asset = this.asset();
    return asset?.generation_meta != null ? extractGenMeta(asset.generation_meta) : null;
  });

  protected readonly dimensions = computed((): string => {
    const asset = this.asset();
    if (!asset?.width || !asset?.height) return '—';
    return `${asset.width} × ${asset.height}`;
  });

  protected readonly fileSize = computed((): string =>
    formatBytes(this.asset()?.file_size ?? null)
  );

  protected readonly formattedDate = computed((): string => {
    const asset = this.asset();
    return formatDate(asset?.created_at ?? asset?.imported_at ?? null);
  });

  protected readonly hashShort = computed((): string => {
    const hash = this.asset()?.content_hash;
    return hash ? hash.slice(0, 8) + '…' : '—';
  });

  protected readonly downloadUrl = computed((): string => {
    const asset = this.asset();
    return asset != null ? this.assetService.fileUrl(asset.id) : '#';
  });

  protected readonly isFavourite = computed((): boolean =>
    this.asset()?.favourite ?? false
  );

  protected readonly hasPHash = computed((): boolean =>
    this.asset()?.has_phash ?? false
  );

  protected readonly faces = computed((): FaceDto[] => this.detail()?.faces ?? []);

  protected faceLabel(face: FaceDto): string {
    const parts: string[] = [];
    if (face.age != null) {
      parts.push(`~${face.age} J.`);
    }
    if (face.score != null) {
      parts.push(`${Math.round(face.score * 100)}% sicher`);
    }
    return parts.join(' · ') || 'Gesicht';
  }

  protected faceScore(face: FaceDto): string {
    return face.score != null ? `${Math.round(face.score * 100)}%` : '';
  }

  protected readonly sourceLabel = computed((): string => {
    const source = this.asset()?.source;
    if (!source) return '—';
    const labels: Record<string, string> = {
      original: 'Original',
      flux: 'FLUX',
      sdxl: 'SDXL',
    };
    return labels[source] ?? source;
  });

  // Optimistic hidden tag IDs (removed but not yet reloaded)
  private readonly hiddenTagIds = signal<number[]>([]);

  private isTagHidden(tagId: number): boolean {
    return this.hiddenTagIds().includes(tagId);
  }

  constructor() {
    effect((): void => {
      const asset: AssetDto | null = this.asset();
      this.showGenMeta.set(asset?.source != null && asset.source !== 'original');
      // Reset editing state when navigating
      this.addingTag.set(false);
      this.tagInputValue.set('');
      this.editingCaption.set(false);
      this.hiddenTagIds.set([]);
      // Reset similar overlay when navigating to a different asset
      this.showSimilarOverlay.set(false);
      this.similarAssets.set([]);
      this.selectedSimilarPair.set(null);
      // Reset face matches
      this.selectedFace.set(null);
      this.faceMatches.set([]);
    });

    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      const shortcuts = this.shortcutService.resolvedShortcuts();
      if (shortcuts.get('lightbox.close')?.includes(event.key))  { this.close(); }
      else if (shortcuts.get('lightbox.prev')?.includes(event.key))   { this.prev(); }
      else if (shortcuts.get('lightbox.next')?.includes(event.key))   { this.next(); }
      else if (shortcuts.get('asset.favourite')?.includes(event.key)) { this.toggleFavourite(); }
      else if (shortcuts.get('asset.delete')?.includes(event.key))    { this.deleteAsset(); }
    };
    this.document.addEventListener('keydown', onKeyDown);
    this.destroyRef.onDestroy(() => this.document.removeEventListener('keydown', onKeyDown));

    const deregister = this.shortcutService.register([
      { key: '←',   description: 'Vorheriges Bild',       context: 'Lightbox' },
      { key: '→',   description: 'Nächstes Bild',         context: 'Lightbox' },
      { key: 'F',   description: 'Favorit setzen/entfernen', context: 'Lightbox' },
      { key: 'Entf', description: 'In Papierkorb legen',  context: 'Lightbox' },
      { key: 'Esc', description: 'Lightbox schließen',    context: 'Lightbox' },
    ]);
    this.destroyRef.onDestroy(deregister);
  }

  protected close(): void {
    this.store.dispatch(galleryActions.closeLightbox());
  }

  protected prev(): void {
    this.store.dispatch(galleryActions.lightboxPrev());
  }

  protected next(): void {
    this.store.dispatch(galleryActions.lightboxNext());
  }

  protected toggleGenMeta(): void {
    this.showGenMeta.update((visible: boolean) => !visible);
  }

  protected toggleFavourite(): void {
    const asset: AssetDto | null = this.asset();
    if (asset != null) {
      this.store.dispatch(galleryActions.toggleFavourite({ id: asset.id, value: !asset.favourite }));
    }
  }

  protected deleteAsset(): void {
    const asset: AssetDto | null = this.asset();
    if (asset != null) {
      this.store.dispatch(galleryActions.deleteAsset({ id: asset.id }));
    }
  }

  protected openRerunDialog(): void {
    this.store.dispatch(presetsActions.loadPresets());
    this.showRerunDialog.set(true);
  }

  protected onRerunConfirm(payload: RerunPayload): void {
    this.showRerunDialog.set(false);
    const asset: AssetDto | null = this.asset();
    if (asset == null) { return; }
    this.classifyService.rerun({
      asset_ids: [asset.id],
      steps: payload.steps,
      ...(payload.captionPresetId != null ? { caption_preset_id: payload.captionPresetId } : {}),
    }).subscribe();
  }

  protected onRerunCancel(): void {
    this.showRerunDialog.set(false);
  }

  // ── Similar assets overlay ────────────────────────────────────────────────

  protected openEditor(): void {
    const asset: AssetDto | null = this.asset();
    if (asset == null) { return; }
    this.store.dispatch(galleryActions.closeLightbox());
    this.router.navigate(['/editor/instance', asset.id]);
  }

  protected similarityPercent(distance: number): number {
    return Math.max(0, Math.round((1 - distance / 64) * 100));
  }

  protected openSimilarOverlay(): void {
    const asset: AssetDto | null = this.asset();
    if (asset == null || !asset.has_phash) { return; }
    this.showSimilarOverlay.set(true);
    this.similarLoading.set(true);
    this.assetService.getSimilarAssets(asset.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (assets: SimilarAsset[]) => {
          this.similarAssets.set(assets);
          this.similarLoading.set(false);
        },
        error: () => { this.similarLoading.set(false); },
      });
  }

  protected closeSimilarOverlay(): void {
    this.showSimilarOverlay.set(false);
    this.selectedSimilarPair.set(null);
  }

  protected openSimilarCompare(similar: SimilarAsset): void {
    const asset: AssetDto | null = this.asset();
    if (asset == null) { return; }
    const assetAsSummary: AssetSummary = {
      id: asset.id,
      width: asset.width,
      height: asset.height,
      format: asset.format,
      source: asset.source,
      file_size: asset.file_size,
      created_at: asset.created_at,
      imported_at: asset.imported_at,
    };
    const pair: DupePair = {
      id: 0,
      asset_a: assetAsSummary,
      asset_b: similar,
      phash_distance: similar.phash_distance,
      created_at: new Date().toISOString(),
    };
    this.selectedSimilarPair.set(pair);
  }

  protected onSimilarResolve(event: { pair: DupePair; resolution: DupeResolution }): void {
    const { pair, resolution } = event;
    if (resolution === 'dismiss') {
      this.selectedSimilarPair.set(null);
      return;
    }
    if (resolution === 'delete_a') {
      this.store.dispatch(galleryActions.deleteAsset({ id: pair.asset_a.id }));
    } else if (resolution === 'delete_b') {
      this.store.dispatch(galleryActions.deleteAsset({ id: pair.asset_b.id }));
    } else if (resolution === 'a_is_original') {
      this.assetService.setAssetOriginal(pair.asset_b.id, pair.asset_a.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe();
    } else if (resolution === 'b_is_original') {
      this.assetService.setAssetOriginal(pair.asset_a.id, pair.asset_b.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe();
    }
    this.selectedSimilarPair.set(null);
    this.showSimilarOverlay.set(false);
  }

  // ── Face matches (person assignment) ──────────────────────────────────────

  protected toggleFaceMatches(face: FaceDto): void {
    if (this.selectedFace()?.id === face.id) {
      this.selectedFace.set(null);
      this.faceMatches.set([]);
      return;
    }
    this.selectedFace.set(face);
    this.faceMatchesLoading.set(true);
    this.faceMatches.set([]);
    this.personService.getFaceMatches(face.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (matches: FaceMatch[]) => {
          this.faceMatches.set(matches);
          this.faceMatchesLoading.set(false);
        },
        error: () => { this.faceMatchesLoading.set(false); },
      });
  }

  protected assignFaceToPerson(faceId: number, personId: number): void {
    this.personService.assignFace(faceId, personId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.selectedFace.set(null);
          this.faceMatches.set([]);
          this.reloadTrigger.update((count: number) => count + 1);
        },
      });
  }

  protected matchScorePercent(score: number): number {
    return Math.round(score * 100);
  }

  // ── Tag editing ───────────────────────────────────────────────────────────

  protected removeTag(tagId: number): void {
    const assetId = this.asset()?.id;
    if (assetId == null) { return; }
    // Optimistic hide
    this.hiddenTagIds.update((ids: number[]) => [...ids, tagId]);
    this.assetService.patchTags(assetId, [], [tagId]).subscribe({
      next: () => { this.reloadTrigger.update((count: number) => count + 1); },
      error: () => {
        // Rollback optimistic hide
        this.hiddenTagIds.update((ids: number[]) => ids.filter((id: number) => id !== tagId));
      },
    });
  }

  protected openAddTag(): void {
    this.addingTag.set(true);
    this.tagInputValue.set('');
  }

  protected confirmAddTag(): void {
    const name = this.tagInputValue().trim();
    const assetId = this.asset()?.id;
    if (!name || assetId == null) {
      this.addingTag.set(false);
      return;
    }
    const normalizedName = name.toLowerCase().replace(/ /g, '_');
    const isDuplicate = this.displayTags().some((tag: TagDto) => tag.name === normalizedName);
    if (isDuplicate) {
      this.addingTag.set(false);
      this.tagInputValue.set('');
      return;
    }
    this.assetService.patchTags(assetId, [name], []).subscribe({
      next: () => { this.reloadTrigger.update((count: number) => count + 1); },
    });
    this.addingTag.set(false);
    this.tagInputValue.set('');
  }

  protected onTagInputKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.confirmAddTag();
    } else if (event.key === 'Escape') {
      this.addingTag.set(false);
      this.tagInputValue.set('');
    }
  }

  protected pickSuggestion(name: string): void {
    this.tagInputValue.set(name);
    this.confirmAddTag();
  }

  // ── Caption editing ───────────────────────────────────────────────────────

  protected startCaptionEdit(): void {
    this.captionDraft.set(this.caption() ?? '');
    this.editingCaption.set(true);
  }

  protected saveCaptionEdit(): void {
    if (!this.editingCaption()) { return; }
    const assetId = this.asset()?.id;
    const draft   = this.captionDraft().trim();
    this.editingCaption.set(false);
    if (assetId == null || draft === (this.caption() ?? '').trim()) { return; }
    this.assetService.patchCaption(assetId, draft).subscribe({
      next: () => { this.reloadTrigger.update((count: number) => count + 1); },
    });
  }

  protected cancelCaptionEdit(): void {
    this.editingCaption.set(false);
  }
}
