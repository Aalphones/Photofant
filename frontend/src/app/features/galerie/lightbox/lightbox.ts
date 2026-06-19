import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { DOCUMENT } from '@angular/common';
import { combineLatest, of, switchMap } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { AssetDto, TagDto, TagListItem } from '@photofant/models';
import { AssetService, ClassifyService, TagService } from '@photofant/services';
import { ShortcutService } from '../../../services/shortcut.service';
import { Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';
import { galleryActions, gallerySelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { ZoomStage } from './zoom-stage';

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
  imports: [ZoomStage, Icon, RerunDialog],
  templateUrl: './lightbox.html',
  styleUrl: './lightbox.scss',
})
export class Lightbox {
  private readonly store            = inject(Store);
  private readonly assetService     = inject(AssetService);
  private readonly tagService       = inject(TagService);
  private readonly classifyService  = inject(ClassifyService);
  private readonly shortcutService  = inject(ShortcutService);
  private readonly document        = inject(DOCUMENT);
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
    });

    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      switch (event.key) {
        case 'Escape':     this.close(); break;
        case 'ArrowLeft':  this.prev(); break;
        case 'ArrowRight': this.next(); break;
        case 'f':
        case 'F':          this.toggleFavourite(); break;
        case 'Delete':     this.deleteAsset(); break;
      }
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
