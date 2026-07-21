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
import { Router } from '@angular/router';
import { combineLatest, forkJoin, of, switchMap, catchError, debounceTime, map, startWith, type Observable } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { AssetClassification, AssetDetailDto, AssetDto, AssetLinkSummary, AssetsPage, ComfyUIImportResponse, ComfyUIWorkflow, CreateEntityRequest, EntityDto, EntityRefDto, ExplainabilityPayload, FaceDto, FaceMatch, Framing, PersonDto, RecommendationDto, RecommendationsResponse, RecommendationStatus, RelatedRailItem, SemanticSearchResponse, TagDto, TagListItem, VersionDto } from '@photofant/models';
import { recommendationReasonLabel } from '@photofant/models';
import { AssetService, ClassifyService, ComfyUIService, extractApiErrorMessage, PersonService, RecommendationService, SearchService, TagService } from '@photofant/services';
import { ShortcutService } from '../../../services/shortcut.service';
import { ComfyuiImportDialog, Icon, RerunDialog } from '@photofant/ui';
import type { RerunPayload } from '@photofant/ui';
import { comfyuiActions, comfyuiSelectors, filtersActions, galleryActions, gallerySelectors, jobsSelectors, knowledgeActions, knowledgeSelectors, personsActions, personsSelectors, presetsActions, presetsSelectors } from '@photofant/store';
import { ZoomStage } from './zoom-stage';
import { RelatedRail } from './related-rail/related-rail';
import { LorePanel } from './lore-panel/lore-panel';
import { Editor } from '../../editor/editor';
import { EntityWizardDialog } from '../../wissen/entity-wizard-dialog/entity-wizard-dialog';

// Anzahl Vorschläge in der Lightbox-Rail — spiegelt `reverseSearch.similarLimit` (Default
// 10, `backend/photofant/settings.py`). Kein Frontend-Config-Read nötig: der „mehr"-Sprung
// nutzt bewusst den größeren Server-Default (`SemanticSearchRequest.limit` = 24), die Rail
// bleibt kompakt.
const RELATED_RAIL_LIMIT = 10;

interface RelatedRailData {
  items: RelatedRailItem[];
  loading: boolean;
  emptyMessage: string | null;
}

interface RecommendationsData {
  status: RecommendationStatus;
  items: RelatedRailItem[];
  // Rohe DTOs neben der Rail-Projektion — das „Warum?"-Popover (P26 Phase 3) braucht Score/
  // Reason-Detail, die beim Mappen auf `RelatedRailItem.reasons: {label}[]` verloren gehen.
  raw: RecommendationDto[];
}

interface GenMetaEntry { key: string; value: string }

interface ClassificationGroup {
  category_id: number;
  category_name: string;
  items: AssetClassification[];
}

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
  imports: [ZoomStage, Icon, RerunDialog, RelatedRail, LorePanel, ComfyuiImportDialog, Editor, EntityWizardDialog],
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
  private readonly searchService      = inject(SearchService);
  private readonly recommendationService = inject(RecommendationService);
  private readonly router             = inject(Router);
  private readonly destroyRef         = inject(DestroyRef);

  protected readonly showRerunDialog = signal(false);
  protected readonly showComfyuiImportDialog = signal(false);
  protected readonly showEditorModal = signal(false);

  // ── Wissen anlegen (P25 Lore-Panel „anlegen") ─────────────────────────────
  // Öffnet den Entity-Wizard inline in der Lightbox statt zu `/wissen` zu navigieren —
  // die alte Navigation hing unter der Guard-Leerpfad-Route und landete bei einer
  // Guard-Re-Prüfung riskant auf /entsperren statt auf dem Formular.
  protected readonly showKnowledgeWizard = signal(false);
  protected readonly knowledgeDomains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly isSavingKnowledgeEntity = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly knowledgeSaveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  private readonly lastCreatedKnowledgeEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);
  private readonly pendingKnowledgeCreate = signal(false);
  private readonly knowledgeCreateTargetPersonId = signal<number | null>(null);
  // Bump nach erfolgreicher Verknüpfung -> Lore-Panel lädt neu (dessen eigene Inputs
  // assetId/personId ändern sich sonst nicht, ein reines reloadTrigger-Bump reicht nicht).
  protected readonly loreRefreshKey = signal(0);

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

  // Mobile: Aktions-Fußzeile hinter Burger-Toggle eingeklappt (siehe lightbox.scss
  // Breakpoint 640px) — verhindert, dass die fixe Fußzeile bei wenig Höhe den
  // gesamten Scrollbereich der Tabs überdeckt. Auf Desktop wirkungslos (Toggle
  // per CSS ausgeblendet, Inhalt immer sichtbar).
  protected readonly mobileActionsOpen = signal(false);

  protected toggleMobileActions(): void {
    this.mobileActionsOpen.update((open: boolean) => !open);
  }

  // Panel-Tabs (Übersicht/Wissen/Gesichter/Versionen) — Gesichter-Tab existiert nur im
  // Asset-Modus. „Wissen" bündelt Lore-Panel + Empfehlungen (vorher Teil von Übersicht).
  protected readonly activeTab = signal<'overview' | 'knowledge' | 'people' | 'versions'>('overview');

  // Reload trigger: bump to force a fresh detail fetch
  private readonly reloadTrigger = signal(0);

  // catchError ist hier Pflicht: toSignal() wirft bei jedem Lesen des Signals erneut,
  // sobald die Quell-Observable einmal fehlerhaft terminiert hat — ohne Fangnetz bleibt
  // das Panel nach einem einzigen fehlgeschlagenen Request für den Rest der Session tot
  // (Angular bricht das Rendern an der ersten defekten Signal-Lesung ab, alles danach im
  // Template friert ein). Siehe Lightbox-Bug: „nach Personen-Zuweisung + Pfeiltaste
  // rendert nichts mehr unterhalb der Gesichter-Sektion".
  protected readonly detail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]) =>
        asset != null
          ? this.assetService.getAsset(asset.id).pipe(
              catchError((err: unknown) => {
                console.error('[Lightbox] Asset-Detail konnte nicht geladen werden:', err);
                return of(null);
              }),
            )
          : of(null)
      ),
    ),
  );

  protected readonly faceDetail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxFaceId),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([faceId]) =>
        faceId != null
          ? this.personService.getFace(faceId).pipe(
              catchError((err: unknown) => {
                console.error('[Lightbox] Face-Detail konnte nicht geladen werden:', err);
                return of(null);
              }),
            )
          : of(null)
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

  // ── „Ähnliche Bilder" (P36) — seit dem Merge nur noch Datenquelle, kein eigener
  // Rail-Abschnitt mehr im Template: reine CLIP-Nachbarschaft ergänzt die Graph-Empfehlungen
  // um Bilder, die visuell ähnlich sind, aber (noch) kein Graph-Signal haben (z.B. andere
  // Person, gleiche Szene) — sonst zeigt „Empfehlungen" nur Treffer derselben Person.
  // Läuft an derselben Reload-Pipeline wie `detail`; im Gesichter-Modus liefert
  // `selectLightboxAsset` null (lightboxId ist dort null), die Liste bleibt entsprechend leer.
  protected readonly relatedRail = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]: [AssetDto | null, number]) => this.loadRelatedRail(asset)),
    ),
    { initialValue: { items: [], loading: false, emptyMessage: null } as RelatedRailData },
  );

  // ── Empfehlungen (P26 Phase 2) — dockt unter dem Lore-Panel an ────────────
  // Läuft an derselben Reload-Pipeline wie `detail`/`relatedRail`. Im
  // Gesichter-Modus liefert `selectLightboxAsset` null, Empfehlungen bleiben entsprechend leer.
  protected readonly recommendations = toSignal(
    combineLatest([
      this.store.select(gallerySelectors.selectLightboxAsset),
      toObservable(this.reloadTrigger),
    ]).pipe(
      switchMap(([asset]: [AssetDto | null, number]) => this.loadRecommendations(asset)),
    ),
    { initialValue: { status: 'ready', items: [], raw: [] } as RecommendationsData },
  );

  // Merge Graph-Empfehlungen + reine CLIP-Nachbarschaft in eine Liste (dedupliziert nach
  // assetId, Empfehlungen zuerst — sie tragen die reichere Begründungskette). Ersetzt die
  // frühere zweite Sektion „Ähnliche Bilder", die dieselben Bilder oft nochmal zeigte.
  protected readonly mergedRecommendationItems = computed((): RelatedRailItem[] => {
    const recommended = this.recommendations().items;
    const seen = new Set(recommended.map((item: RelatedRailItem) => item.assetId));
    const extraSimilar = this.relatedRail().items.filter(
      (item: RelatedRailItem) => !seen.has(item.assetId),
    );
    return [...recommended, ...extraSimilar];
  });

  // „Keine Empfehlungen" -> Bereich entfällt komplett (AK); „computing"/Laden zeigt die
  // Sektion dezent mit Lade-Text, sobald aus KEINER der beiden Quellen schon etwas da ist.
  protected readonly showRecommendations = computed((): boolean => {
    const recommendationsData = this.recommendations();
    return recommendationsData.status === 'computing'
      || this.relatedRail().loading
      || this.mergedRecommendationItems().length > 0;
  });

  // Job-Ids, für die bereits ein Reload angestoßen wurde — verhindert, dass ein einmal
  // fertiger Recommendation-Job bei jedem weiteren Signal-Read erneut einen Reload auslöst.
  private readonly handledRecommendationJobIds = new Set<string>();

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

  // ── Quick-Assign (per Klick wählbares Gesicht, Default = erstes Gesicht) ───
  protected readonly quickAssignMatches = signal<FaceMatch[]>([]);
  private readonly selectedQuickAssignFaceId = signal<number | null>(null);

  // Welches Gesicht die Schnellzuweisung gerade zeigt — explizit angeklicktes Gesicht,
  // sonst Fallback auf das erste. Fällt auch zurück, wenn das gewählte Gesicht
  // (z.B. durch Löschen) nicht mehr existiert.
  protected readonly quickAssignFace = computed((): FaceDto | null => {
    const selectedId = this.selectedQuickAssignFaceId();
    if (selectedId != null) {
      const selected = this.faces().find((face: FaceDto) => face.id === selectedId);
      if (selected != null) { return selected; }
    }
    return this.firstFace();
  });

  protected readonly quickMatches = computed((): FaceMatch[] =>
    this.quickAssignMatches().slice(0, 5)
  );

  protected selectQuickAssignFace(face: FaceDto): void {
    this.selectedQuickAssignFaceId.set(face.id);
  }

  private readonly allPersons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly unknownPerson = computed((): PersonDto | null =>
    this.allPersons().find((person: PersonDto) => person.is_unknown) ?? null
  );

  // ── Empty-State: kein Gesicht extrahiert ──────────────────────────────────
  protected readonly retryingFaceExtraction = signal(false);

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

  // ── Klassifizierung (P18 Phase 5) ─────────────────────────────────────────

  protected readonly classificationsByCategory = computed((): ClassificationGroup[] => {
    const groups = new Map<number, ClassificationGroup>();
    for (const item of this.detail()?.classifications ?? []) {
      const group = groups.get(item.category_id);
      if (group != null) {
        group.items.push(item);
      } else {
        groups.set(item.category_id, {
          category_id: item.category_id,
          category_name: item.category_name,
          items: [item],
        });
      }
    }
    return [...groups.values()];
  });

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

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

  protected readonly hasEmbedding = computed((): boolean =>
    this.asset()?.has_embedding ?? false
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

    // Empfehlungen (P26): der GET-Endpoint liefert bei Cache-Miss `status:"computing"`
    // ohne Job-Id (der Job läuft bereits serverseitig) — anders als beim Korrektur-Flow
    // kann hier also nicht auf eine bestimmte Job-Id gefiltert werden. Stattdessen: sobald
    // irgendein `recommendation`-Job durchläuft, während wir noch auf „computing" stehen,
    // neu laden (idempotent — steht der Cache für dieses Bild noch nicht, liefert der
    // nächste Reload wieder „computing" und wartet auf den nächsten Job weiter).
    effect((): void => {
      if (this.recommendations().status !== 'computing') { return; }
      const finishedJob = this.allJobs().find((job) =>
        job.kind === 'recommendation' &&
        (job.state === 'done' || job.state === 'error') &&
        !this.handledRecommendationJobIds.has(job.id)
      );
      if (finishedJob == null) { return; }
      this.handledRecommendationJobIds.add(finishedJob.id);
      this.reloadTrigger.update((count: number) => count + 1);
    });

    effect((): void => {
      const asset: AssetDto | null = this.asset();
      this.lightboxFaceId(); // auch bei Wechsel zwischen/innerhalb Gesichter-Modus zurücksetzen
      this.showGenMeta.set(asset?.source != null && asset.source !== 'original');
      this.activeTab.set('overview');
      this.mobileActionsOpen.set(false);
      this.selectedQuickAssignFaceId.set(null);
      // Reset editing state when navigating
      this.addingTag.set(false);
      this.tagInputValue.set('');
      this.editingCaption.set(false);
      this.hiddenTagIds.set([]);
      // Reset PersonPicker-Modal state
      this.showPersonPicker.set(false);
      this.selectedFaceId.set(null);
      this.faceMatches.set([]);
      this.creatingNewPerson.set(false);
      this.newPersonName.set('');
      this.personSearchQuery.set('');
      this.retryingFaceExtraction.set(false);
      // Reset version compare stub
      this.showVersionCompare.set(false);
      // Reset RelationBrowser-Modal
      this.showRelationBrowser.set(null);
      this.relationBrowserQuery.set('');
      this.relationBrowserSelected.set([]);
      // Reset Explainability-Popover (P26 Phase 3) — Payload ist pro Quellbild gültig
      this.recommendationExplainOpenId.set(null);
    });

    // Metadaten-Drafts aus `detail()` initialisieren (framing lebt nur dort) —
    // läuft bei jedem Laden/Reload neu, damit Drafts nie den Server-Stand überholen.
    effect((): void => {
      const detail = this.detail();
      if (detail == null) { return; }
      this.sourceDraft.set(detail.source);
      this.framingDraft.set(detail.framing);
    });

    // Quick-Assign: Top-Matches für das gewählte Gesicht automatisch nachladen,
    // sobald sich die Auswahl ändert (Klick auf ein Gesicht, Navigation oder Zuweisung).
    let lastQuickAssignFaceId: number | null = null;
    effect((): void => {
      const face = this.quickAssignFace();
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

    // P25 Lore-Panel „anlegen": sobald die im Wizard angelegte Entity im Store landet,
    // mit der Zielperson verknüpfen (Face-Modus: das offene Face; Asset-Modus: die Person
    // des ersten Gesichts) und den Wizard schließen. `pendingKnowledgeCreate` verhindert,
    // dass eine bereits verarbeitete Entity (z.B. aus der Personen-Seite) hier erneut greift.
    effect((): void => {
      const entity: EntityDto | null = this.lastCreatedKnowledgeEntity();
      if (entity == null || !this.pendingKnowledgeCreate()) { return; }
      this.pendingKnowledgeCreate.set(false);
      this.showKnowledgeWizard.set(false);
      const personId = this.knowledgeCreateTargetPersonId();
      this.knowledgeCreateTargetPersonId.set(null);
      if (personId == null) { return; }
      this.personService.linkEntity(personId, entity.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: () => { this.loreRefreshKey.update((count: number) => count + 1); },
          error: (err: unknown) => {
            console.error('[Lightbox] Neue Entity konnte nicht mit der Person verknüpft werden:', err);
          },
        });
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

  // ── Navigation zu einem verknüpften Asset (Quelle im Gesichter-Modus,
  // Original/Edit in der Beziehungen-Sektion) ──────────────────────────────
  // Lädt das Ziel-Asset bei Bedarf nach (es kann außerhalb der aktuell geladenen
  // Galerie-Seite liegen) und öffnet es in derselben Lightbox.

  protected openSourceAsset(assetId: number): void {
    this.store.dispatch(galleryActions.openAssetLightbox({ assetId }));
  }

  // P24 Phase 3: verknüpfte Entity anklicken -> Wissens-Sicht. Lightbox schließt vorher,
  // sonst bleibt sie als Overlay über der Navigation hängen (kein eigener Zurück-Weg).
  protected openLinkedEntity(entity: EntityRefDto): void {
    this.close();
    this.router.navigate(['/wissen'], { queryParams: { entity: entity.id } });
  }

  // P25 Lore-Panel: „anlegen" im Leer-Zustand -> Wizard inline öffnen (siehe Effect oben).
  // Zielperson für die spätere Verknüpfung wird hier festgehalten, weil sie beim
  // Wizard-Schließen (Face-/Asset-Modus-Wechsel möglich) sonst nicht mehr verfügbar wäre.
  protected openKnowledgeCreate(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.loadDomains());
    this.knowledgeCreateTargetPersonId.set(
      this.isFaceMode() ? (this.faceDetail()?.person_id ?? null) : (this.firstFace()?.person_id ?? null)
    );
    this.pendingKnowledgeCreate.set(false);
    this.showKnowledgeWizard.set(true);
  }

  protected onCloseKnowledgeWizard(): void {
    this.showKnowledgeWizard.set(false);
    this.pendingKnowledgeCreate.set(false);
    this.knowledgeCreateTargetPersonId.set(null);
  }

  protected onSaveKnowledgeEntity(request: CreateEntityRequest): void {
    this.pendingKnowledgeCreate.set(true);
    this.store.dispatch(knowledgeActions.createEntity({ request }));
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

  // ── Related-Rail „Ähnliche Bilder" (P36) ──────────────────────────────────

  private loadRelatedRail(asset: AssetDto | null): Observable<RelatedRailData> {
    if (asset == null) {
      return of({ items: [], loading: false, emptyMessage: null });
    }
    if (!asset.has_embedding) {
      return of({ items: [], loading: false, emptyMessage: 'Für dieses Bild liegt noch kein Embedding vor.' });
    }
    return this.searchService.semanticByAsset(asset.id, RELATED_RAIL_LIMIT).pipe(
      map((response: SemanticSearchResponse): RelatedRailData => ({
        items: response.hits.map((hit): RelatedRailItem => ({ assetId: hit.asset_id, score: hit.score, reasons: null })),
        loading: false,
        emptyMessage: response.hits.length === 0 ? 'Keine ähnlichen Bilder gefunden.' : null,
      })),
      startWith({ items: [], loading: true, emptyMessage: null } as RelatedRailData),
      catchError((err: unknown) => {
        console.error('[Lightbox] Ähnliche Bilder konnten nicht geladen werden:', err);
        return of({
          items: [],
          loading: false,
          emptyMessage: extractApiErrorMessage(err, 'Ähnliche Bilder konnten nicht geladen werden.'),
        });
      }),
    );
  }

  protected openRelatedAsset(assetId: number): void {
    this.openSourceAsset(assetId);
  }

  // ── Empfehlungen (P26 Phase 2) ─────────────────────────────────────────────

  private loadRecommendations(asset: AssetDto | null): Observable<RecommendationsData> {
    if (asset == null) {
      return of({ status: 'ready', items: [], raw: [] });
    }
    return this.recommendationService.getRecommendations(asset.id).pipe(
      map((response: RecommendationsResponse): RecommendationsData => ({
        status: response.status,
        items: response.recommendations.map((recommendation: RecommendationDto): RelatedRailItem => ({
          assetId: recommendation.asset_id,
          score: recommendation.score,
          reasons: recommendation.reasons.map((reason) => ({ label: recommendationReasonLabel(reason) })),
        })),
        raw: response.recommendations,
      })),
      catchError((err: unknown) => {
        console.error('[Lightbox] Empfehlungen konnten nicht geladen werden:', err);
        return of({ status: 'ready', items: [], raw: [] } as RecommendationsData);
      }),
    );
  }

  // ── Explainability „Warum?" (P26 Phase 3) ─────────────────────────────────
  // Score/Reasons liegen für Graph-Empfehlungen schon lokal vor (aus `recommendations()`),
  // kein Request nötig. Für die gemergten reinen CLIP-Treffer (kein `RecommendationDto`, da
  // sie nur aus der Ähnlichkeitssuche kommen) gibt es einen schlankeren Fallback aus dem
  // schon vorhandenen Score. „Warum nicht?" ist mit dem Merge entfallen — es gibt keine
  // separate „nicht empfohlen"-Liste mehr, an der die Frage noch Sinn ergäbe; der Backend-
  // Endpoint (`RecommendationService.whyNot`) bleibt für spätere/andere Konsumenten bestehen.

  protected readonly recommendationExplainOpenId = signal<number | null>(null);

  protected readonly recommendationExplainPayload = computed((): ExplainabilityPayload | null => {
    const assetId = this.recommendationExplainOpenId();
    if (assetId == null) { return null; }
    const raw = this.recommendations().raw.find((item: RecommendationDto) => item.asset_id === assetId);
    if (raw != null) {
      return {
        title: 'Warum empfohlen?',
        confidencePercent: Math.round(raw.score * 100),
        reasons: raw.reasons.map(recommendationReasonLabel),
        missing: [],
        meta: [],
      };
    }
    const similarItem = this.relatedRail().items.find((item: RelatedRailItem) => item.assetId === assetId);
    if (similarItem != null) {
      return {
        title: 'Ähnliches Bild',
        confidencePercent: Math.round(similarItem.score * 100),
        reasons: ['✓ CLIP-Ähnlichkeit'],
        missing: [],
        meta: [],
      };
    }
    return null;
  });

  protected onRecommendationExplainOpen(assetId: number): void {
    this.recommendationExplainOpenId.set(assetId);
  }

  protected onRecommendationExplainClose(): void {
    this.recommendationExplainOpenId.set(null);
  }

  // „mehr" — öffnet die Galerie im Reverse-Modus (Phase 2) zu genau diesem Bild. Nutzt
  // dieselbe Semantik-Suche wie die Rail, aber ohne Limit (Server-Default 24 statt 10),
  // damit die Reverse-Galerie mehr als die Rail-Vorschau zeigt.
  protected openMoreSimilar(): void {
    const asset: AssetDto | null = this.asset();
    if (asset == null) { return; }
    this.searchService.semanticByAsset(asset.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: SemanticSearchResponse) => {
          const similarIds = response.hits.map((hit) => hit.asset_id);
          if (similarIds.length === 0) { return; }
          this.store.dispatch(filtersActions.setReverseSearch({
            reverseSearch: { thumbnailDataUrl: this.assetService.thumbnailUrl(asset.id, 256), similarIds },
          }));
          this.close();
        },
        error: (err: unknown) => {
          console.error('[Lightbox] Reverse-Suche (mehr) fehlgeschlagen:', err);
        },
      });
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

  // Asset-Modus: kein Gesicht im Kontext (leerer Gesichter-Zustand) — Picker ohne
  // Top-Treffer-Spalte, `selectedFaceId` bleibt null und steuert damit in
  // `assignPersonFromPicker()` den Zuweisungs-Pfad.
  protected openPersonPickerAssetMode(): void {
    this.selectedFaceId.set(null);
    this.showPersonPicker.set(true);
    this.personSearchQuery.set('');
    this.creatingNewPerson.set(false);
    this.faceMatchesLoading.set(false);
    this.faceMatches.set([]);
    this.store.dispatch(personsActions.loadPersons());
  }

  // „Extrahieren nochmal probieren" — stößt Face-Klassifizierung nur für dieses eine
  // Bild neu an, kein Preset-Auswahl-Dialog dazwischen. Job läuft asynchron weiter;
  // das neu extrahierte Gesicht taucht nach Abschluss beim nächsten Laden auf.
  protected retryFaceExtraction(): void {
    const assetId = this.asset()?.id;
    if (assetId == null || this.retryingFaceExtraction()) { return; }
    this.retryingFaceExtraction.set(true);
    this.classifyService.rerun({ asset_ids: [assetId], steps: ['faces'] })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.retryingFaceExtraction.set(false); },
        error: (err: unknown) => {
          console.error('[Lightbox] Face-Extraktion (Rerun) fehlgeschlagen:', err);
          this.retryingFaceExtraction.set(false);
        },
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

  // Vereinheitlichter Zuweisungs-Pfad für den Picker: Face-Reassign, wenn ein Gesicht
  // im Kontext ist (Face-Modus / Gesichter-Sektion), sonst Asset-Modus-Zuweisung ohne
  // Gesicht (P30). Ersetzt die drei Template-Stellen mit `assignFaceToPerson(selectedFaceId()!, …)`.
  protected assignPersonFromPicker(personId: number): void {
    const faceId = this.selectedFaceId();
    if (faceId != null) {
      this.assignFaceToPerson(faceId, personId);
      return;
    }
    const assetId = this.asset()?.id;
    if (assetId == null) { return; }
    this.personService.assignPersonToAsset(assetId, personId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.closePersonPicker();
          this.reloadTrigger.update((count: number) => count + 1);
        },
        error: (err: unknown) => {
          console.error('[Lightbox] Personen-Zuweisung fehlgeschlagen:', err);
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
    if (!name) {
      this.cancelCreatePerson();
      return;
    }
    this.personService.createPerson(name)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (person: PersonDto) => {
          this.creatingNewPerson.set(false);
          this.newPersonName.set('');
          this.assignPersonFromPicker(person.id);
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
