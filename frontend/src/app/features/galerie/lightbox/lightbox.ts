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
import { switchMap, of } from 'rxjs';
import { Store } from '@ngrx/store';
import type { AssetDto, TagDto } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { ShortcutService } from '../../../services/shortcut.service';
import { Icon } from '@photofant/ui';
import { galleryActions, gallerySelectors } from '@photofant/store';
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
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(1) + ' MB';
  if (bytes >= 1_024) return Math.round(bytes / 1_024) + ' KB';
  return bytes + ' B';
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
  imports: [ZoomStage, Icon],
  templateUrl: './lightbox.html',
  styleUrl: './lightbox.scss',
})
export class Lightbox {
  private readonly store           = inject(Store);
  private readonly assetService    = inject(AssetService);
  private readonly shortcutService = inject(ShortcutService);
  private readonly document        = inject(DOCUMENT);
  private readonly destroyRef      = inject(DestroyRef);

  protected readonly asset = this.store.selectSignal(gallerySelectors.selectLightboxAsset);
  protected readonly hasPrev = this.store.selectSignal(gallerySelectors.selectLightboxHasPrev);
  protected readonly hasNext = this.store.selectSignal(gallerySelectors.selectLightboxHasNext);

  protected readonly showGenMeta = signal(false);

  private readonly detail = toSignal(
    this.store.select(gallerySelectors.selectLightboxAsset).pipe(
      switchMap((asset: AssetDto | null) =>
        asset != null ? this.assetService.getAsset(asset.id) : of(null)
      ),
    ),
  );

  protected readonly displayTags = computed(() =>
    (this.detail()?.tags ?? []).map((tag: TagDto) => ({
      id: tag.id,
      displayName: tag.name.replace(/_/g, ' '),
    }))
  );

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
    return `${asset.width} × ${asset.height}`;
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

  constructor() {
    effect((): void => {
      const asset: AssetDto | null = this.asset();
      this.showGenMeta.set(asset?.source != null && asset.source !== 'original');
    });

    const onKeyDown = (event: KeyboardEvent): void => {
      if ((event.target as HTMLElement).tagName === 'INPUT') return;
      if ((event.target as HTMLElement).tagName === 'TEXTAREA') return;
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
}
