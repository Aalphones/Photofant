import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  HostListener,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import {
  catchError,
  combineLatest,
  filter,
  map,
  of,
  startWith,
  switchMap,
  take,
  type Observable,
} from 'rxjs';
import type {
  AiAutonomyDto,
  CollectionDetail,
  DomainDto,
  EntityDto,
  EntityFieldDefDto,
  EntityType,
  Job,
  KnowledgeUpdateResult,
  LoreDto,
  MediaRefDto,
  Owner,
  PersonDto,
  ResolvedRelationshipDto,
  UpdateSuggestionResponse,
} from '@photofant/models';
import { CollectionService, JobsService, KnowledgeService, PersonService } from '@photofant/services';
import { CompletenessRing, Icon } from '@photofant/ui';

type LoreLoadStatus = 'loading' | 'ready' | 'empty';

interface LoreLoadState {
  status: LoreLoadStatus;
  lore: LoreDto | null;
}

interface UpdateSuggestionState {
  pending: boolean;
  result: KnowledgeUpdateResult | null;
  error: boolean;
}

interface FieldRow {
  key: string;
  label: string;
  value: string | null;
  owner: Owner | null;
}

const IDLE_SUGGESTION_STATE: UpdateSuggestionState = { pending: false, result: null, error: false };

// P38 Phase 6 — Wissen-Detail-Modal. Zeigt Merkmale (Phase 2), Beziehungen, Quellen und
// verknüpfte Fotos zu einer Person ODER einer unverknüpften Notiz — genau eines der beiden
// Eingänge ist gesetzt. Lädt seine Daten selbst (wie `LorePanel`), bekommt Domänen/Personen/
// Autonomie aber vom Elternteil gereicht statt eigene Store-Selektoren zu ziehen, weil
// `Wissen` diese Listen ohnehin schon geladen hat (kein zweiter Request für dieselben Daten).
@Component({
  selector: 'pf-knowledge-detail-dialog',
  imports: [Icon, CompletenessRing],
  templateUrl: './knowledge-detail-dialog.html',
  styleUrl: './knowledge-detail-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgeDetailDialog {
  private readonly knowledgeService = inject(KnowledgeService);
  private readonly personService = inject(PersonService);
  private readonly jobsService = inject(JobsService);
  private readonly collectionService = inject(CollectionService);

  // Genau einer der beiden ist beim Öffnen gesetzt (Person aus dem Grid, Entity aus der
  // Notizen-Sektion). Ein Klick auf eine Beziehungs-Chip navigiert intern weiter (siehe
  // `activePersonId`/`activeEntityId` unten) — die Inputs selbst ändern sich dabei nicht.
  readonly personId = input<number | null>(null);
  readonly entityId = input<string | null>(null);
  readonly domains = input<DomainDto[]>([]);
  readonly persons = input<PersonDto[]>([]);
  readonly autonomy = input<AiAutonomyDto | null>(null);
  readonly hasUnlinkedNotes = input<boolean>(false);
  // Vom Elternteil hochgezählt, nachdem eine Verknüpfung/Trennung diese Entity betroffen hat
  // (die Aktion selbst läuft über die Outputs unten) — löst einen frischen `getLore`-Read aus.
  readonly refreshKey = input<number>(0);

  readonly close = output<void>();
  readonly openInterview = output<void>();
  readonly openWebSearch = output<void>();
  readonly openDiscoverySetup = output<void>();
  readonly openLightbox = output<number>();
  readonly linkRequested = output<void>();
  readonly unlinkRequested = output<string>();

  // Innerer Navigations-Zustand — startet bei den Inputs, wandert aber weiter, wenn der
  // Nutzer auf eine Beziehungs-Chip klickt ("Modal lädt neu", Aufgabe 4). Wird bei jedem
  // Wechsel der Inputs (neues Öffnen von außen) zurückgesetzt.
  protected readonly activePersonId = signal<number | null>(null);
  protected readonly activeEntityId = signal<string | null>(null);
  // Intern hochgezählt, nachdem eine Übernahme (KI-Banner) den Body dieser Entity geändert
  // hat — löst denselben frischen Lore-Read aus wie das vom Elternteil gereichte `refreshKey`,
  // ohne dass das Modal dafür erst schließen/neu öffnen müsste.
  private readonly localRefreshTick = signal(0);

  constructor() {
    effect(() => {
      this.activePersonId.set(this.personId());
      this.activeEntityId.set(this.entityId());
    });

    // Wechselt die Entity (Beziehungs-Chip-Navigation), verliert ein noch offener
    // KI-Vorschlag seine Gültigkeit — sonst zeigt der Banner den Vorschlag der vorigen
    // Entity unter dem neuen Namen weiter an (gleiches Muster wie `LorePanel`s Reset-Effekt).
    // Reagiert bewusst nur auf einen ID-Wechsel, nicht auf jeden Lore-Reload — sonst würde
    // der eigene `localRefreshTick` nach "Übernehmen" den gerade gesetzten `done`-Zustand
    // sofort wieder zurücksetzen.
    effect(() => {
      const id = this.entity()?.id ?? null;
      if (id === this.lastResetEntityId) { return; }
      this.lastResetEntityId = id;
      this.updateSuggestionRequested.set(false);
      this.updateAccepted.set(false);
      this.albumFormOpen.set(false);
      this.albumTitle.set('');
      this.albumPending.set(false);
      this.albumCreatedTitle.set(null);
      this.albumError.set(null);
    });
  }

  private lastResetEntityId: string | null = null;

  private readonly loreState = toSignal(
    combineLatest([
      toObservable(this.activePersonId),
      toObservable(this.activeEntityId),
      toObservable(this.refreshKey),
      toObservable(this.localRefreshTick),
    ]).pipe(
      switchMap(([personId, entityId]: [number | null, string | null, number, number]): Observable<LoreLoadState> => {
        if (personId != null) {
          return this.knowledgeService.getLore({ personId }).pipe(
            map((lores: LoreDto[]): LoreLoadState => ({
              status: lores.length > 0 ? 'ready' : 'empty',
              lore: lores[0] ?? null,
            })),
            startWith({ status: 'loading', lore: null } as LoreLoadState),
            catchError((): Observable<LoreLoadState> => of({ status: 'empty', lore: null })),
          );
        }
        if (entityId != null) {
          return this.knowledgeService.getEntityLore(entityId).pipe(
            map((lore: LoreDto): LoreLoadState => ({ status: 'ready', lore })),
            startWith({ status: 'loading', lore: null } as LoreLoadState),
            catchError((): Observable<LoreLoadState> => of({ status: 'empty', lore: null })),
          );
        }
        return of({ status: 'empty', lore: null } as LoreLoadState);
      }),
    ),
    { initialValue: { status: 'loading', lore: null } as LoreLoadState },
  );

  protected readonly status = computed((): LoreLoadStatus => this.loreState().status);
  protected readonly lore = computed((): LoreDto | null => this.loreState().lore);
  protected readonly entity = computed((): EntityDto | null => this.lore()?.entity ?? null);

  // Leerer Zustand gilt nur im Personen-Modus — eine per `entityId` geöffnete Notiz ist per
  // Definition bereits eine bestehende Entity.
  protected readonly isEmptyState = computed((): boolean =>
    this.status() === 'empty' && this.activePersonId() !== null
  );

  protected readonly person = computed((): PersonDto | null => {
    const id = this.activePersonId();
    if (id === null) { return null; }
    return this.persons().find((candidate: PersonDto) => candidate.id === id) ?? null;
  });

  protected readonly avatarUrl = computed((): string | null => {
    const faceId = this.person()?.portrait_face_id;
    return faceId != null ? this.personService.portraitUrl(faceId) : null;
  });

  protected readonly displayName = computed((): string =>
    this.person()?.name ?? this.entity()?.title ?? 'Unbenannt'
  );

  protected readonly percent = computed((): number => Math.round((this.entity()?.completeness ?? 0) * 100));

  // P39 Phase 5 — `null` sowohl bei fehlendem Zeitstempel (Datei nicht auflösbar) als auch
  // bei unparsebarem Wert; die Kopfzeile blendet die Angabe dann komplett aus (AK 5).
  protected readonly updatedLabel = computed((): string | null => {
    const raw = this.entity()?.updated_at ?? null;
    if (raw === null) { return null; }
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) { return null; }
    return new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'short', year: 'numeric' }).format(parsed);
  });

  private readonly domain = computed((): DomainDto | null =>
    this.domains().find((candidate: DomainDto) => candidate.name === this.entity()?.domain) ?? null
  );

  private readonly entityType = computed((): EntityType | null =>
    this.domain()?.entity_types.find((candidate: EntityType) => candidate.name === this.entity()?.type) ?? null
  );

  // Eine Zeile je definiertem Merkmal des Typs, nicht nur je gesetztem — fehlende Merkmale
  // sind der Punkt der Anzeige (Aufgabe 4, Sektion "Merkmale").
  protected readonly fieldRows = computed((): FieldRow[] => {
    const entity = this.entity();
    const type = this.entityType();
    if (entity === null || type === null) { return []; }
    return type.fields.map((field: EntityFieldDefDto): FieldRow => {
      const attribute = entity.attributes[field.key];
      return { key: field.key, label: field.label, value: attribute?.value ?? null, owner: attribute?.owner ?? null };
    });
  });

  protected ownerLabel(owner: Owner | null): string {
    switch (owner) {
      case 'user':
      case 'manual': return 'Manuell';
      case 'web': return 'Web';
      case 'inferred': return 'KI-Schätzung';
      default: return 'fehlt';
    }
  }

  protected ownerClass(owner: Owner | null): string {
    switch (owner) {
      case 'user':
      case 'manual': return 'kd-owner--manual';
      case 'web': return 'kd-owner--web';
      case 'inferred': return 'kd-owner--inferred';
      default: return 'kd-owner--empty';
    }
  }

  protected readonly relationships = computed((): ResolvedRelationshipDto[] => this.lore()?.relationships ?? []);

  protected readonly relatedPhotos = computed((): MediaRefDto[] =>
    (this.lore()?.related_media ?? []).filter((media: MediaRefDto) => media.kind === 'asset')
  );

  protected readonly sources = computed((): string[] => this.lore()?.sources ?? []);

  // ── Album aus den verknüpften Fotos (P39 Phase 6) ────────────────────────────────────────
  // Bewusst kein erfundener KI-Titelvorschlag (Mockup-Attrappe) — die ehrliche Variante:
  // Anzahl nennen, Titel abfragen, echtes Album über `createCollection` + `addItems` anlegen
  // (der Kontrakt trägt keine Asset-Ids direkt, s. `backend/photofant/api/collections.py:89`).
  protected readonly albumFormOpen = signal(false);
  protected readonly albumTitle = signal('');
  protected readonly albumPending = signal(false);
  protected readonly albumCreatedTitle = signal<string | null>(null);
  protected readonly albumError = signal<string | null>(null);

  protected openAlbumForm(): void {
    this.albumTitle.set(this.displayName());
    this.albumError.set(null);
    this.albumFormOpen.set(true);
  }

  protected cancelAlbumForm(): void {
    this.albumFormOpen.set(false);
    this.albumError.set(null);
  }

  protected createAlbum(): void {
    const title = this.albumTitle().trim();
    const assetIds = this.relatedPhotos().map((photo: MediaRefDto) => photo.id);
    if (title.length === 0 || assetIds.length === 0) { return; }

    this.albumPending.set(true);
    this.albumError.set(null);
    this.collectionService
      .createCollection({ name: title, kind: 'album' })
      .pipe(
        switchMap((detail: CollectionDetail): Observable<CollectionDetail> =>
          this.collectionService.addItems(detail.id, assetIds).pipe(map((): CollectionDetail => detail)),
        ),
      )
      .subscribe({
        next: (detail: CollectionDetail): void => {
          this.albumPending.set(false);
          this.albumFormOpen.set(false);
          this.albumCreatedTitle.set(detail.name);
        },
        error: (): void => {
          this.albumPending.set(false);
          this.albumError.set('Album konnte nicht angelegt werden.');
        },
      });
  }

  protected relationTypeLabel(type: string): string {
    return type.replaceAll('_', ' ');
  }

  // Springt innerhalb desselben Modals auf die Ziel-Entity (Aufgabe 4) — kein Schließen/
  // Neuöffnen von außen nötig, `loreState` reagiert auf die geänderten internen Signale.
  protected openRelationTarget(entityRefId: string): void {
    this.activePersonId.set(null);
    this.activeEntityId.set(entityRefId);
  }

  protected isUrl(source: string): boolean {
    return source.startsWith('http://') || source.startsWith('https://');
  }

  // `entity.sources` trägt laut Backend-Kontrakt nur URLs (Web-Recherche schreibt die
  // einzigen strukturierten Einträge, s. `api/knowledge_ai.py`). Interview/manuelle Einträge
  // hinterlassen keinen eigenen Quellen-Eintrag — die Dreiteilung aus dem Design wird daher
  // heuristisch aus dem String abgeleitet, nicht aus einem echten Herkunfts-Feld.
  protected sourceIcon(source: string): string {
    if (this.isUrl(source)) { return 'globe'; }
    if (source.toLowerCase().includes('interview')) { return 'sparkle'; }
    return 'pencil';
  }

  protected sourceLabel(source: string): string {
    if (!this.isUrl(source)) { return source; }
    try {
      return new URL(source).hostname.replace(/^www\./, '');
    } catch {
      return source;
    }
  }

  // "Verknüpfung lösen" ist nur sinnvoll, solange wir tatsächlich über eine Person auf diese
  // Entity gekommen sind — eine über `entityId` geöffnete unverknüpfte Notiz hat keine Bindung
  // zu lösen (Aufgabe 2).
  protected readonly canUnlink = computed((): boolean =>
    this.activePersonId() !== null && this.entity() !== null
  );

  protected readonly canRequestWebSearch = computed((): boolean => {
    const entity = this.entity();
    if (entity === null) { return false; }
    if (this.autonomy()?.discovery !== 'auto') { return false; }
    return this.domain()?.private === false;
  });

  // Leerer Zustand: es gibt noch keine Entity und damit keine Domäne, gegen die
  // `canRequestWebSearch` prüfen könnte — hier reicht die Existenz mindestens einer
  // nicht-privaten Domäne, die Wahl der konkreten Domäne trifft der Entity-Wizard, den
  // `openDiscoverySetup` öffnet (Elternteil verdrahtet das).
  protected readonly canRequestDiscoverySetup = computed((): boolean => {
    if (this.autonomy()?.discovery !== 'auto') { return false; }
    return this.domains().some((candidate: DomainDto) => !candidate.private);
  });

  // ── KI-Ergänzungsvorschlag (P27, hier als Banner statt Inline-Aktion) ────────────────────
  // Bewusst kein Auto-Trigger beim Öffnen: das ganze P38-Vorhaben ist strikt Opt-in für
  // KI-Aktionen (siehe README "Vorgeschichte" #1) — ein echter Gemma-Lauf startet daher erst
  // auf Klick, genau wie das bestehende "Ergänzen (KI)" im Lore-Panel.
  protected readonly canOfferUpdateSuggestion = computed((): boolean => {
    const entity = this.entity();
    if (entity === null || entity.owner === 'user') { return false; }
    return this.autonomy()?.knowledge_update !== 'off';
  });

  protected readonly updateSuggestionRequested = signal(false);
  private readonly updateSuggestionState = toSignal(
    toObservable(this.updateSuggestionRequested).pipe(
      switchMap((requested: boolean): Observable<UpdateSuggestionState> => {
        const entity = this.entity();
        if (!requested || entity === null) { return of(IDLE_SUGGESTION_STATE); }
        return this.knowledgeService.requestUpdateSuggestion({ entity_id: entity.id }).pipe(
          switchMap((response: UpdateSuggestionResponse): Observable<Job> =>
            this.jobsService.streamJobs().pipe(
              filter((job: Job): boolean =>
                job.id === response.job_id && (job.state === 'done' || job.state === 'error'),
              ),
              take(1),
            ),
          ),
          map((job: Job): UpdateSuggestionState => ({
            pending: false,
            error: job.state === 'error' || job.result == null,
            result: job.state === 'done' ? (job.result as unknown as KnowledgeUpdateResult) : null,
          })),
          startWith({ pending: true, result: null, error: false } as UpdateSuggestionState),
          catchError((): Observable<UpdateSuggestionState> => of({ pending: false, result: null, error: true })),
        );
      }),
    ),
    { initialValue: IDLE_SUGGESTION_STATE },
  );

  protected readonly updateSuggestionPending = computed((): boolean => this.updateSuggestionState().pending);
  protected readonly updateSuggestionResult = computed((): KnowledgeUpdateResult | null => this.updateSuggestionState().result);
  protected readonly updateSuggestionError = computed((): boolean => this.updateSuggestionState().error);
  protected readonly updateAccepted = signal(false);
  protected readonly updateAcceptPending = signal(false);

  protected requestUpdateSuggestion(): void {
    this.updateAccepted.set(false);
    this.updateSuggestionRequested.set(true);
  }

  protected dismissUpdateSuggestion(): void {
    this.updateSuggestionRequested.set(false);
    this.updateAccepted.set(false);
  }

  protected acceptUpdateSuggestion(): void {
    const entity = this.entity();
    const result = this.updateSuggestionResult();
    const proposal = result?.proposal ?? null;
    if (entity === null || result === null || proposal === null) { return; }

    this.updateAcceptPending.set(true);
    this.knowledgeService
      .acceptUpdateSuggestion({ entity_id: entity.id, body: proposal.body, reason: result.explainability.reason })
      .pipe(
        switchMap((): Observable<Job> =>
          this.jobsService.streamJobs().pipe(
            filter((job: Job): boolean => job.state === 'done' || job.state === 'error'),
            take(1),
          ),
        ),
      )
      .subscribe({
        next: (): void => {
          this.updateAcceptPending.set(false);
          this.updateAccepted.set(true);
          this.localRefreshTick.update((tick: number): number => tick + 1);
        },
        error: (): void => {
          this.updateAcceptPending.set(false);
        },
      });
  }

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('kd-scrim')) {
      this.close.emit();
    }
  }

  @HostListener('document:keydown', ['$event'])
  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.close.emit();
    }
  }
}
