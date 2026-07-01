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
import { combineLatest, forkJoin, of, switchMap, catchError, debounceTime, map, type Observable } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { AssetDetailDto, AssetDto, AssetLinkSummary, AssetsPage, AssetSummary, ComfyUIImportResponse, ComfyUIWorkflow, DupePair, DupeResolution, FaceDto, FaceMatch, Framing, PersonDto, SimilarAsset, TagDto, TagListItem, VersionDto } from '@photofant/models';
import { AssetService, ClassifyService, ComfyUIService, PersonService, TagService } from '@photofant/services';
import { ShortcutService } from '../../../services/shortcut.service';
import { ComfyuiImportDialog, Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';
import { comfyuiActions, comfyuiSelectors, galleryActions, gallerySelectors, jobsSelectors, personsActions, personsSelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { ZoomStage } from './zoom-stage';
import { DupeCompare } from '../../review/review-dupes/dupe-compare/dupe-compare';
import { Editor } from '../../editor/editor';

interface GenMetaEntry { key: string; value: string }

type CompareTag = 'current' | 'version' | 'original' | 'edit';

interface CompareItem {
  id: number;
  label: string;
  tag: CompareTag;
  thumbnailUrl: string;
  resolution: string;
  source: string;
  date: string;
}

const COMPARE_TAG_META: Record<CompareTag, { label: string; className: string }> = {
  current:  { label: 'Aktuell',  className: 'vc-tag--cur' },
  version:  { label: 'Version',  className: 'vc-tag--ver' },
  original: { label: 'Original', className: 'vc-tag--orig' },
  edit:     { label: 'Edit',     className: 'vc-tag--edit' },
};

const VERSION_TYPE_LABELS: Record<string, string> = {
  crop: 'Crop',
  rotate: 'Rotiert',
  upscale: 'Upscale',
  comfyui: 'ComfyUI-Edit',
  edit: 'Edit',
};

const FRAMING_LABELS: Record<Framing, string> = {
  close_up: 'Nahaufnahme',
  medium: 'Halbkörper',
  full_body: 'Ganzkörper',
};

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b);
}

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
  imports: [ZoomStage, Icon, RerunDialog, DupeCompare, ComfyuiImportDialog, Editor],
  templateUrl: './lightbox.html',
  styleUrl: './lightbox.scss',
})
export class Lightbox {
  private readonly store              = inject(Store);
  private readonly assetService       = inject(AssetService);
  private readonly tagService         = inject(TagService);
  private readonly classifyService    = inject(ClassifyService);
  private readonly shortcutService    = inject(ShortcutService);
  private readonly comfyuiService     = inject(ComfyUIService);
  private readonly document           = inject(DOCUMENT);
  private readonly personService      = inject(PersonService);
  private readonly destroyRef         = inject(DestroyRef);

  protected readonly showRerunDialog = signal(false);
  protected readonly showComfyuiImportDialog = signal(false);
  protected readonly showEditorModal = signal(false);

  // ── VersionCompare-Modal ──────────────────────────────────────────────────
  protected readonly showVersionCompare = signal(false);
  protected readonly leftIdx  = signal(0);
  protected readonly rightIdx = signal(0);

  protected readonly isUpscaling  = signal(false);
  protected readonly upscaleError = signal<string | null>(null);

  // Job-ID des laufenden Default-Upscale-Jobs; null wenn keiner aktiv.
  private readonly pendingUpscaleJobId = signal<string | null>(null);
  private readonly allJobs = this.store.selectSignal(jobsSelectors.allJobs);

  protected readonly asset    = this.store.selectSignal(gallerySelectors.selectLightboxAsset);
  protected readonly lightboxKind   = this.store.selectSignal(gallerySelectors.selectLightboxKind);
  protected readonly lightboxFaceId = this.store.selectSignal(gallerySelectors.selectLightboxFaceId);
  protected readonly lightboxVersionId = this.store.selectSignal(gallerySelectors.selectLightboxVersionId);
  protected readonly isFaceMode = computed((): boolean => this.lightboxKind() === 'face');
  protected readonly presets  = this.store.selectSignal(presetsSelectors.selectPresets);
  protected readonly comfyuiConfig    = this.store.selectSignal(comfyuiSelectors.selectConfig);
  private readonly activeWorkflows    = this.store.selectSignal(comfyuiSelectors.selectActiveWorkflows);
  private readonly hasPrevAsset = this.store.selectSignal(gallerySelectors.selectLightboxHasPrev);
  private readonly hasNextAsset = this.store.selectSignal(gallerySelectors.selectLightboxHasNext);
  private readonly hasPrevFace  = this.store.selectSignal(gallerySelectors.selectLightboxHasPrevFace);
  private readonly hasNextFace  = this.store.selectSignal(gallerySelectors.selectLightboxHasNextFace);

  protected readonly hasPrev = computed((): boolean =>
    this.isFaceMode() ? this.hasPrevFace() : this.hasPrevAsset()
  );

  protected readonly hasNext = computed((): boolean =>
    this.isFaceMode() ? this.hasNextFace() : this.hasNextAsset()
  );

  protected readonly showGenMeta = signal(false);

  // Reload trigger: bump to force a fresh detail fetch
  private readonly reloadTrigger = signal(0);

  protected readonly detail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]) =>
        asset != null ? this.assetService.getAsset(asset.id) : of(null)
      ),
    ),
  );

  protected readonly faceDetail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxFaceId),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([faceId]) =>
        faceId != null ? this.personService.getFace(faceId) : of(null)
      ),
    ),
  );

  // Verwandte Assets (P10 Phase 1) — Ableitungs-Baum aus version.parent_id/face.source_version_id.
  // Nur im Asset-Modus (Gesichter-Modus hat bereits „Quelle" für den Rückbezug).
  protected readonly lineage = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]) =>
        asset != null ? this.assetService.getLineage(asset.id) : of(null)
      ),
    ),
  );

  // ── Gesichter-Modus: gemeinsame Datenquellen für Stage + Versionen ────────

  protected readonly panelReady = computed((): boolean =>
    this.isFaceMode() ? this.faceDetail() != null : this.asset() != null
  );

  protected readonly activeVersions = computed((): VersionDto[] =>
    this.isFaceMode() ? (this.faceDetail()?.versions ?? []) : (this.detail()?.versions ?? [])
  );

  // P21-Stapel: explizit gewählte initiale Stage-Version (Klick auf eine Stapel-Kachel).
  // Ändert nicht `is_current` — nur, welche Version beim Öffnen zuerst angezeigt wird.
  protected readonly stageVersion = computed((): VersionDto | null => {
    const versionId = this.lightboxVersionId();
    if (versionId == null) { return null; }
    return this.activeVersions().find((version: VersionDto) => version.id === versionId) ?? null;
  });

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

  // ── Face matches (PersonPicker-Modal) ─────────────────────────────────────
  // Nur die faceId wird gebraucht (Zuweisen/Vergleich mit Löschziel) — funktioniert
  // damit gleichermaßen für Asset-Modus-`FaceDto` wie für den Gesichter-Modus.
  protected readonly showPersonPicker   = signal(false);
  protected readonly selectedFaceId     = signal<number | null>(null);
  protected readonly faceMatches        = signal<FaceMatch[]>([]);
  protected readonly faceMatchesLoading = signal(false);
  protected readonly creatingNewPerson  = signal(false);
  protected readonly newPersonName      = signal('');
  protected readonly personSearchQuery  = signal('');

  // ── Beziehungen-Sektion (RelationBrowser-Modal) ───────────────────────────
  protected readonly showRelationBrowser  = signal<'origin' | 'edits' | null>(null);
  protected readonly relationBrowserQuery = signal('');
  protected readonly relationBrowserAssets  = signal<AssetDto[]>([]);
  protected readonly relationBrowserLoading = signal(false);
  protected readonly relationBrowserSelected = signal<number[]>([]);

  // Suche läuft jetzt serverseitig (searchRelationCandidates) — die gesamte Bibliothek ist
  // durchsuchbar, nicht nur die zuletzt geladenen 200 Assets. Hier nur noch das aktuelle
  // Bild selbst aus den Treffern rausfiltern.
  protected readonly relationBrowserList = computed((): AssetDto[] => {
    const currentId = this.asset()?.id;
    return this.relationBrowserAssets().filter((candidate: AssetDto) => candidate.id !== currentId);
  });

  // ── Metadaten (editierbar) ─────────────────────────────────────────────────
  protected readonly sourceDraft  = signal<string | null>(null);
  protected readonly framingDraft = signal<Framing | null>(null);

  // ── Quick-Assign (Gesicht 1, immer sichtbar im Panel) ─────────────────────
  protected readonly quickAssignMatches = signal<FaceMatch[]>([]);

  protected readonly quickMatches = computed((): FaceMatch[] =>
    this.quickAssignMatches().slice(0, 5)
  );

  private readonly allPersons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly personSearchResults = computed((): PersonDto[] => {
    const query = this.personSearchQuery().trim().toLowerCase();
    if (query.length === 0) { return []; }
    return this.allPersons()
      .filter((person: PersonDto) =>
        !person.is_unknown && person.name != null && person.name.toLowerCase().includes(query)
      )
      .slice(0, 15);
  });

  protected readonly personDirectory = computed((): PersonDto[] =>
    this.allPersons().filter((person: PersonDto) => !person.is_unknown && person.name != null)
  );

  // Liste im PersonPicker-Modal: Suchergebnisse bei Query, sonst volles Verzeichnis.
  protected readonly pickerList = computed((): PersonDto[] =>
    this.personSearchQuery().trim().length > 0 ? this.personSearchResults() : this.personDirectory()
  );

  // ── Computed display ─────────────────────────────────────────────────────

  protected readonly displayTags = computed(() =>
    (this.detail()?.tags ?? []).filter((tag: TagDto) => !this.isTagHidden(tag.id))
  );

  protected readonly caption = computed((): string | null => this.detail()?.caption ?? null);

  protected readonly imageUrl = computed((): string => {
    if (this.isFaceMode()) { return this.faceStageUrl(); }
    const stageVersion = this.stageVersion();
    if (stageVersion != null) { return `/api/versions/${stageVersion.id}/file`; }
    const asset = this.asset();
    return asset != null ? this.assetService.fileUrl(asset.id) : '';
  });

  // Stage-Bild im Gesichter-Modus: explizit gewählte Stapel-Version, sonst die aktuelle
  // Face-Version, sonst der ursprüngliche Crop
  private faceStageUrl(): string {
    const face = this.faceDetail();
    if (face == null) { return ''; }
    const selected = this.stageVersion();
    const current = selected ?? face.versions.find((version: VersionDto) => version.is_current);
    return current != null ? `/api/versions/${current.id}/file` : '/api' + face.crop_url;
  }

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
    if (this.isFaceMode()) { return formatDate(this.faceDetail()?.created_at ?? null); }
    const asset = this.asset();
    return formatDate(asset?.created_at ?? asset?.imported_at ?? null);
  });

  protected readonly hashShort = computed((): string => {
    const hash = this.asset()?.content_hash;
    return hash ? hash.slice(0, 8) + '…' : '—';
  });

  protected readonly aspectRatio = computed((): string => {
    const asset = this.asset();
    const width = asset?.width;
    const height = asset?.height;
    if (!width || !height) { return '—'; }
    const divisor = gcd(width, height);
    return `${width / divisor}:${height / divisor}`;
  });

  protected readonly qualityDisplay = computed((): number | null => {
    const quality = this.detail()?.quality;
    return quality != null ? Math.round(quality * 100) : null;
  });

  protected readonly qualityClass = computed((): string => {
    const quality = this.qualityDisplay();
    if (quality == null) { return 'quality--low'; }
    if (quality >= 80) { return 'quality--good'; }
    if (quality >= 60) { return 'quality--warn'; }
    return 'quality--low';
  });

  protected readonly downloadUrl = computed((): string => {
    if (this.isFaceMode()) { return this.faceStageUrl() || '#'; }
    const stageVersion = this.stageVersion();
    if (stageVersion != null) { return `/api/versions/${stageVersion.id}/file`; }
    const asset = this.asset();
    return asset != null ? this.assetService.fileUrl(asset.id) : '#';
  });

  protected readonly isFavourite = computed((): boolean =>
    this.asset()?.favourite ?? false
  );

  protected readonly hasPHash = computed((): boolean =>
    this.asset()?.has_phash ?? false
  );

  // Standard-Upscale-Workflow (nur wenn ComfyUI aktiv + gesetzt + gültig).
  private readonly upscaleWorkflow = computed((): ComfyUIWorkflow | null => {
    const key = this.comfyuiConfig().defaultUpscale;
    if (!key) { return null; }
    return this.activeWorkflows().find((workflow: ComfyUIWorkflow) => workflow.key === key) ?? null;
  });

  protected readonly canUpscale = computed((): boolean =>
    this.comfyuiConfig().enabled && this.upscaleWorkflow() != null
  );

  protected readonly faces = computed((): FaceDto[] => this.detail()?.faces ?? []);

  // ── Panel-Header (Avatar des ersten Gesichts) ─────────────────────────────

  protected readonly firstFace = computed((): FaceDto | null => this.faces()[0] ?? null);

  protected readonly headerAvatarUrl = computed((): string | null => {
    if (this.isFaceMode()) {
      const face = this.faceDetail();
      return face != null ? '/api' + face.crop_url : null;
    }
    const face = this.firstFace();
    return face != null ? '/api' + face.crop_url : null;
  });

  protected readonly firstPersonName = computed((): string => {
    if (this.isFaceMode()) {
      const face = this.faceDetail();
      return face?.person_name ?? '#' + (face?.id ?? '?');
    }
    const face = this.firstFace();
    return face?.person_name ?? '#' + (this.asset()?.id ?? '?');
  });

  protected readonly headerInitial = computed((): string => {
    const name = this.firstPersonName();
    return name.startsWith('#') ? '?' : (name.trim()[0]?.toUpperCase() ?? '?');
  });

  protected faceLabel(face: FaceDto): string {
    return face.person_name ?? 'Unbekannt';
  }

  protected faceScore(face: FaceDto): string {
    if (this.isFaceManual(face)) { return 'manuell'; }
    return face.score != null ? `${Math.round(face.score * 100)}%` : '—';
  }

  protected faceAge(face: FaceDto): string {
    return face.age != null ? `${face.age}J` : '—';
  }

  protected isFaceManual(face: FaceDto): boolean {
    return face.origin === 'manual';
  }

  protected firstName(name: string | null): string {
    return name?.trim().split(' ')[0] ?? '?';
  }

  protected readonly sourceLabel = computed((): string => this.sourceLabelFor(this.asset()?.source ?? null));

  protected sourceLabelFor(source: string | null): string {
    if (!source) return '—';
    const labels: Record<string, string> = {
      original: 'Original',
      flux: 'FLUX',
      sdxl: 'SDXL',
    };
    return labels[source] ?? source;
  }

  protected framingLabel(framing: Framing): string {
    return FRAMING_LABELS[framing];
  }

  // ── VersionCompare: Panel-Items ──────────────────────────────────────────

  protected readonly compareItems = computed((): CompareItem[] => {
    const detail = this.detail();
    const asset  = this.asset();
    if (detail == null || asset == null) { return []; }

    const items: CompareItem[] = [{
      id: asset.id,
      label: 'Aktuell',
      tag: 'current',
      thumbnailUrl: this.assetService.fileUrl(asset.id),
      resolution: this.dimensions(),
      source: this.sourceLabel(),
      date: this.formattedDate(),
    }];

    for (const version of detail.versions ?? []) {
      items.push({
        id: version.id,
        label: this.versionLabel(version),
        tag: 'version',
        thumbnailUrl: version.thumbnail_url,
        resolution: version.res != null ? `${version.res.width} × ${version.res.height}` : '—',
        source: this.sourceLabel(),
        date: formatDate(version.created_at),
      });
    }

    if (detail.original_id != null) {
      items.push({
        id: detail.original_id,
        label: `Original #${detail.original_id}`,
        tag: 'original',
        thumbnailUrl: this.assetService.fileUrl(detail.original_id),
        resolution: '—',
        source: '—',
        date: '—',
      });
    }

    for (const edit of detail.linked_edits ?? []) {
      items.push({
        id: edit.id,
        label: `${this.sourceLabelFor(edit.source)} #${edit.id}`,
        tag: 'edit',
        thumbnailUrl: this.assetService.fileUrl(edit.id),
        resolution: edit.width != null && edit.height != null ? `${edit.width} × ${edit.height}` : '—',
        source: this.sourceLabelFor(edit.source),
        date: formatDate(edit.created_at),
      });
    }

    return items;
  });

  protected readonly leftItem  = computed((): CompareItem | null => this.compareItems()[this.leftIdx()] ?? null);
  protected readonly rightItem = computed((): CompareItem | null => this.compareItems()[this.rightIdx()] ?? null);

  // Optimistic hidden tag IDs (removed but not yet reloaded)
  private readonly hiddenTagIds = signal<number[]>([]);

  private isTagHidden(tagId: number): boolean {
    return this.hiddenTagIds().includes(tagId);
  }

  constructor() {
    // Wenn der Default-Upscale-Job fertig ist, Detail neu laden damit die neue Version sichtbar wird.
    effect((): void => {
      const jobId = this.pendingUpscaleJobId();
      if (jobId == null) { return; }
      const job = this.allJobs().find((runningJob) => runningJob.id === jobId);
      if (job?.state === 'done') {
        this.pendingUpscaleJobId.set(null);
        this.reloadTrigger.update((count: number) => count + 1);
      } else if (job?.state === 'error') {
        this.pendingUpscaleJobId.set(null);
        this.upscaleError.set(job.error ?? 'Upscale fehlgeschlagen');
      }
    });

    effect((): void => {
      const asset: AssetDto | null = this.asset();
      this.lightboxFaceId(); // auch bei Wechsel zwischen/innerhalb Gesichter-Modus zurücksetzen
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
      // Reset PersonPicker-Modal state
      this.showPersonPicker.set(false);
      this.selectedFaceId.set(null);
      this.faceMatches.set([]);
      this.creatingNewPerson.set(false);
      this.newPersonName.set('');
      this.personSearchQuery.set('');
      // Reset version compare stub
      this.showVersionCompare.set(false);
      // Reset RelationBrowser-Modal
      this.showRelationBrowser.set(null);
      this.relationBrowserQuery.set('');
      this.relationBrowserSelected.set([]);
    });

    // Metadaten-Drafts aus `detail()` initialisieren (framing lebt nur dort) —
    // läuft bei jedem Laden/Reload neu, damit Drafts nie den Server-Stand überholen.
    effect((): void => {
      const detail = this.detail();
      if (detail == null) { return; }
      this.sourceDraft.set(detail.source);
      this.framingDraft.set(detail.framing);
    });

    // Quick-Assign: Top-Matches für das erste Gesicht automatisch nachladen,
    // sobald sich das erste Gesicht ändert (Navigation oder Zuweisung).
    let lastQuickAssignFaceId: number | null = null;
    effect((): void => {
      const face = this.firstFace();
      if (face == null) {
        lastQuickAssignFaceId = null;
        this.quickAssignMatches.set([]);
        return;
      }
      if (face.id === lastQuickAssignFaceId) { return; }
      lastQuickAssignFaceId = face.id;
      this.personService.getFaceMatches(face.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (matches: FaceMatch[]) => { this.quickAssignMatches.set(matches); },
          error: () => { this.quickAssignMatches.set([]); },
        });
    });

    // RelationBrowser-Suche: läuft serverseitig statt nur über die zuletzt geladenen
    // 200 Assets zu filtern — sonst sind Bilder außerhalb dieses Fensters (z.B. ältere
    // Originale) nie auffindbar. ID-Suche geht per Direct-Lookup, Text-Suche über
    // Quelle (original/flux/sdxl) oder Caption.
    combineLatest([toObservable(this.showRelationBrowser), toObservable(this.relationBrowserQuery)])
      .pipe(
        debounceTime(200),
        switchMap(([mode, query]: [('origin' | 'edits' | null), string]) => {
          if (mode == null) { return of(null); }
          this.relationBrowserLoading.set(true);
          return this.searchRelationCandidates(query).pipe(
            catchError(() => of([] as AssetDto[])),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((items: AssetDto[] | null) => {
        if (items == null) { return; }
        this.relationBrowserAssets.set(items);
        this.relationBrowserLoading.set(false);
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

  protected revealInExplorer(): void {
    const assetId = this.isFaceMode() ? this.faceDetail()?.source_asset_id ?? null : this.asset()?.id ?? null;
    if (assetId != null) {
      this.assetService.revealAsset(assetId).subscribe();
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
    if (this.isFaceMode()) {
      if (this.lightboxFaceId() == null) { return; }
    } else if (this.asset() == null) {
      return;
    }
    this.showEditorModal.set(true);
  }

  // ── Gesichter-Modus: Navigation zur Quelle ────────────────────────────────

  protected openSourceAsset(assetId: number): void {
    this.store.dispatch(galleryActions.openAssetLightbox({ assetId }));
  }

  protected onEditorClosed(): void {
    this.showEditorModal.set(false);
  }

  // ── Versionen-Sektion ─────────────────────────────────────────────────────

  protected versionLabel(version: VersionDto): string {
    if (version.type == null) { return 'Version'; }
    return VERSION_TYPE_LABELS[version.type] ?? version.type;
  }

  protected versionMeta(version: VersionDto): string {
    const parts: string[] = [];
    if (version.res != null) { parts.push(`${version.res.width} × ${version.res.height}`); }
    parts.push(formatDate(version.created_at));
    const params = version.params;
    const strength = params?.['strength'];
    if (strength != null) { parts.push(`str ${strength}`); }
    const model = params?.['model'];
    if (model != null) { parts.push(String(model)); }
    return parts.join(' · ');
  }

  // ── Metadaten (editierbar) ─────────────────────────────────────────────────

  protected onSourceChange(value: string): void {
    const assetId = this.asset()?.id;
    if (assetId == null) { return; }
    this.sourceDraft.set(value);
    this.assetService.patchAsset(assetId, { source: value })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => { this.reloadTrigger.update((count: number) => count + 1); } });
  }

  protected onFramingChange(value: string): void {
    const assetId = this.asset()?.id;
    if (assetId == null) { return; }
    const framing = value as Framing;
    this.framingDraft.set(framing);
    this.assetService.patchAsset(assetId, { framing })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => { this.reloadTrigger.update((count: number) => count + 1); } });
  }

  // ── Beziehungen-Sektion ────────────────────────────────────────────────────

  protected originalThumbnailUrl(): string {
    const originalId = this.detail()?.original_id;
    return originalId != null ? this.assetService.thumbnailUrl(originalId, 256) : '';
  }

  protected editThumbnailUrl(edit: AssetLinkSummary): string {
    return this.assetService.thumbnailUrl(edit.id, 256);
  }

  protected relationBrowserThumbnailUrl(candidate: AssetDto): string {
    return this.assetService.thumbnailUrl(candidate.id, 256, candidate.content_hash);
  }

  protected removeOriginal(): void {
    const assetId = this.asset()?.id;
    if (assetId == null) { return; }
    this.assetService.patchAsset(assetId, { original_id: null })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => { this.reloadTrigger.update((count: number) => count + 1); } });
  }

  protected removeEditLink(editId: number): void {
    this.assetService.patchAsset(editId, { original_id: null })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: () => { this.reloadTrigger.update((count: number) => count + 1); } });
  }

  protected openRelationBrowser(mode: 'origin' | 'edits'): void {
    this.relationBrowserAssets.set([]);
    this.relationBrowserLoading.set(true);
    this.relationBrowserQuery.set('');
    this.relationBrowserSelected.set(
      mode === 'origin'
        ? (this.detail()?.original_id != null ? [this.detail()!.original_id!] : [])
        : (this.detail()?.linked_edits ?? []).map((edit: AssetLinkSummary) => edit.id)
    );
    // Fetch läuft über die relationBrowserSearch$-Pipeline im Konstruktor, sobald
    // showRelationBrowser gesetzt ist — deswegen erst danach setzen.
    this.showRelationBrowser.set(mode);
  }

  private searchRelationCandidates(query: string): Observable<AssetDto[]> {
    const trimmed = query.trim();

    if (!trimmed) {
      return this.assetService
        .listAssets({ page: 1, page_size: 200, sort: 'date', order: 'desc' })
        .pipe(map((result: AssetsPage): AssetDto[] => result.items));
    }

    const idMatch = trimmed.match(/^#?(\d+)$/);
    if (idMatch) {
      const id = Number(idMatch[1]);
      return this.assetService.getAsset(id).pipe(
        map((detail: AssetDetailDto): AssetDto[] => [detail]),
        catchError(() => of([] as AssetDto[])),
      );
    }

    const sourceMatch = this.matchSourceKeyword(trimmed);
    if (sourceMatch) {
      return this.assetService
        .listAssets({ page: 1, page_size: 200, sort: 'date', order: 'desc', sources: [sourceMatch] })
        .pipe(map((result: AssetsPage): AssetDto[] => result.items));
    }

    return this.assetService
      .listAssets({ page: 1, page_size: 200, sort: 'date', order: 'desc', q: trimmed, qMode: 'caption' })
      .pipe(map((result: AssetsPage): AssetDto[] => result.items));
  }

  private matchSourceKeyword(query: string): string | null {
    const normalized = query.toLowerCase();
    if (normalized.length < 2) { return null; }
    const sources: Record<string, string[]> = {
      original: ['original', 'orig'],
      flux: ['flux'],
      sdxl: ['sdxl'],
    };
    for (const [source, aliases] of Object.entries(sources)) {
      if (aliases.some((alias: string) => alias.startsWith(normalized))) { return source; }
    }
    return null;
  }

  protected closeRelationBrowser(): void {
    this.showRelationBrowser.set(null);
    this.relationBrowserQuery.set('');
    this.relationBrowserSelected.set([]);
  }

  protected isRelationBrowserSelected(id: number): boolean {
    return this.relationBrowserSelected().includes(id);
  }

  protected toggleRelationBrowserSelect(id: number): void {
    const mode = this.showRelationBrowser();
    if (mode === 'origin') {
      this.relationBrowserSelected.update((selected: number[]) =>
        selected.includes(id) ? [] : [id]
      );
      return;
    }
    this.relationBrowserSelected.update((selected: number[]) =>
      selected.includes(id) ? selected.filter((selectedId: number) => selectedId !== id) : [...selected, id]
    );
  }

  protected confirmRelationBrowser(): void {
    const mode = this.showRelationBrowser();
    const asset = this.asset();
    if (mode == null || asset == null) { return; }
    const selected = this.relationBrowserSelected();

    if (mode === 'origin') {
      const originalId = selected[0] ?? null;
      this.assetService.patchAsset(asset.id, { original_id: originalId })
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => {
            this.reloadTrigger.update((count: number) => count + 1);
            this.closeRelationBrowser();
          },
        });
      return;
    }

    const currentEditIds = (this.detail()?.linked_edits ?? []).map((edit: AssetLinkSummary) => edit.id);
    const added   = selected.filter((id: number) => !currentEditIds.includes(id));
    const removed = currentEditIds.filter((id: number) => !selected.includes(id));
    const requests = [
      ...added.map((editId: number) => this.assetService.patchAsset(editId, { original_id: asset.id })),
      ...removed.map((editId: number) => this.assetService.patchAsset(editId, { original_id: null })),
    ];
    if (requests.length === 0) { this.closeRelationBrowser(); return; }
    forkJoin(requests)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.reloadTrigger.update((count: number) => count + 1);
          this.closeRelationBrowser();
        },
      });
  }

  // ── VersionCompare-Modal ──────────────────────────────────────────────────

  protected openVersionCompare(): void {
    const itemCount = this.compareItems().length;
    this.leftIdx.set(0);
    this.rightIdx.set(Math.min(1, Math.max(0, itemCount - 1)));
    this.showVersionCompare.set(true);
  }

  protected closeVersionCompare(): void {
    this.showVersionCompare.set(false);
  }

  protected setLeftIdx(index: number): void {
    this.leftIdx.set(index);
  }

  protected setRightIdx(index: number): void {
    this.rightIdx.set(index);
  }

  protected compareTagLabel(tag: CompareTag): string {
    return COMPARE_TAG_META[tag].label;
  }

  protected compareTagClass(tag: CompareTag): string {
    return `vc-tag ${COMPARE_TAG_META[tag].className}`;
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
      content_hash: asset.content_hash,
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

  // ── Face deletion ─────────────────────────────────────────────────────────

  protected deleteFaceFromAsset(face: FaceDto): void {
    if (this.selectedFaceId() === face.id) { this.closePersonPicker(); }
    this.personService.deleteFace(face.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.store.dispatch(galleryActions.removeFaceItem({ id: face.id }));
          this.reloadTrigger.update((count: number) => count + 1);
        },
        error: (err: unknown) => {
          console.error('[Lightbox] Face deletion failed:', err);
        },
      });
  }

  // Gesichter-Modus: das aktuell geöffnete Face selbst löschen (nicht eines der
  // Gesichter *auf* einem Asset) — danach gibt es nichts mehr anzuzeigen, Lightbox schließt.
  protected deleteFaceInFaceMode(): void {
    const faceId = this.lightboxFaceId();
    if (faceId == null) { return; }
    if (this.selectedFaceId() === faceId) { this.closePersonPicker(); }
    this.personService.deleteFace(faceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.store.dispatch(galleryActions.removeFaceItem({ id: faceId }));
          this.close();
        },
        error: (err: unknown) => {
          console.error('[Lightbox] Face deletion failed:', err);
        },
      });
  }

  // ── PersonPicker-Modal ─────────────────────────────────────────────────────

  protected openPersonPicker(face: FaceDto): void {
    this.openPersonPickerFor(face.id);
  }

  // Gesichter-Modus: Person für das aktuell geöffnete Face zuweisen
  protected openFacePersonPicker(): void {
    const faceId = this.lightboxFaceId();
    if (faceId != null) { this.openPersonPickerFor(faceId); }
  }

  private openPersonPickerFor(faceId: number): void {
    this.selectedFaceId.set(faceId);
    this.showPersonPicker.set(true);
    this.personSearchQuery.set('');
    this.creatingNewPerson.set(false);
    this.faceMatchesLoading.set(true);
    this.faceMatches.set([]);
    this.store.dispatch(personsActions.loadPersons());
    this.personService.getFaceMatches(faceId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (matches: FaceMatch[]) => {
          this.faceMatches.set(matches);
          this.faceMatchesLoading.set(false);
        },
        error: () => { this.faceMatchesLoading.set(false); },
      });
  }

  protected closePersonPicker(): void {
    this.showPersonPicker.set(false);
    this.selectedFaceId.set(null);
    this.faceMatches.set([]);
    this.creatingNewPerson.set(false);
    this.newPersonName.set('');
    this.personSearchQuery.set('');
  }

  protected assignFaceToPerson(faceId: number, personId: number): void {
    this.personService.assignFace(faceId, personId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closePersonPicker();
          this.reloadTrigger.update((count: number) => count + 1);
        },
        error: (err: unknown) => {
          console.error('[Lightbox] Face assignment failed:', err);
          this.faceMatchesLoading.set(false);
        },
      });
  }

  protected matchScorePercent(score: number): number {
    return Math.round(score * 100);
  }

  protected startCreatePerson(): void {
    this.creatingNewPerson.set(true);
    this.newPersonName.set('');
  }

  protected cancelCreatePerson(): void {
    this.creatingNewPerson.set(false);
    this.newPersonName.set('');
  }

  protected confirmCreatePerson(): void {
    const name = this.newPersonName().trim();
    const faceId = this.selectedFaceId();
    if (!name || faceId == null) {
      this.cancelCreatePerson();
      return;
    }
    this.personService.createPerson(name)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (person: PersonDto) => {
          this.creatingNewPerson.set(false);
          this.newPersonName.set('');
          this.assignFaceToPerson(faceId, person.id);
        },
        error: () => {
          this.creatingNewPerson.set(false);
        },
      });
  }

  protected onNewPersonKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.confirmCreatePerson();
    } else if (event.key === 'Escape') {
      this.cancelCreatePerson();
    }
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

  // ── ComfyUI Import ────────────────────────────────────────────────────────

  protected openComfyuiImportDialog(): void {
    this.store.dispatch(comfyuiActions.loadConfig());
    this.showComfyuiImportDialog.set(true);
  }

  protected onComfyuiImported(_result: ComfyUIImportResponse): void {
    this.showComfyuiImportDialog.set(false);
    this.reloadTrigger.update((count: number) => count + 1);
  }

  protected closeComfyuiImportDialog(): void {
    this.showComfyuiImportDialog.set(false);
  }

  // ── Upscale ───────────────────────────────────────────────────────────────

  protected triggerUpscale(): void {
    const asset: AssetDto | null = this.asset();
    const workflow = this.upscaleWorkflow();
    if (asset == null || workflow == null || this.isUpscaling()) { return; }
    const imageSlot = workflow.inputs.find((input) => input.kind === 'image');
    if (imageSlot == null) { return; }

    this.isUpscaling.set(true);
    this.upscaleError.set(null);

    // Default-Pfad: Backend importiert Ergebnis automatisch als neue Version am Asset.
    this.comfyuiService.runDefaultWorkflow('upscale', {
      target_asset_ids: [asset.id],
      inputs: { [imageSlot.key]: asset.id },
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: { jobs: { job_id: string }[] }) => {
          this.isUpscaling.set(false);
          const jobId = response.jobs[0]?.job_id ?? null;
          if (jobId != null) {
            // Sobald der Job done ist, Detail neu laden → neue Version sichtbar.
            this.pendingUpscaleJobId.set(jobId);
          }
        },
        error: (err: unknown) => {
          this.isUpscaling.set(false);
          const message = err instanceof Error ? err.message : 'Upscale fehlgeschlagen';
          this.upscaleError.set(message);
        },
      });
  }
}
