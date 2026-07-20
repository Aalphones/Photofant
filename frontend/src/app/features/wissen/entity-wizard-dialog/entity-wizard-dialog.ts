import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, debounceTime, distinctUntilChanged, of, Subject, switchMap } from 'rxjs';
import type {
  AiAutonomyMode,
  CreateEntityRequest,
  DomainDto,
  EntityDto,
  EntityType,
  ImportSuggestionRequest,
  KnowledgeImportResult,
  Relationship,
  UpdateEntityRequest,
} from '@photofant/models';
import { KnowledgeService } from '@photofant/services';
import { Icon } from '../../../ui/icon/icon';

@Component({
  selector: 'pf-entity-wizard-dialog',
  imports: [Icon],
  templateUrl: './entity-wizard-dialog.html',
  styleUrl: './entity-wizard-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntityWizardDialog {
  readonly domains = input.required<DomainDto[]>();
  readonly isSaving = input<boolean>(false);
  readonly saveError = input<string | null>(null);
  readonly prefill = input<Partial<CreateEntityRequest>>({});
  // Gesetzt -> Wizard bearbeitet eine bestehende Entity statt eine neue anzulegen
  // (z.B. aus der Aufgabe "Entity noch ohne Inhalt"). Typ/Domäne sind dann gesperrt,
  // das Backend lehnt eine Änderung dieser Felder ohnehin ab (`_apply_patch`).
  readonly editEntity = input<EntityDto | null>(null);
  // P27 Phase 2 — KI-Vorschlag. `off` blendet die Aktion aus; `ask`/`auto` bieten sie an.
  readonly importAutonomy = input<AiAutonomyMode>('off');
  readonly suggestionLoading = input<boolean>(false);
  readonly suggestionResult = input<KnowledgeImportResult | null>(null);
  readonly suggestionError = input<string | null>(null);

  readonly close = output<void>();
  readonly save = output<CreateEntityRequest>();
  readonly update = output<{ entityId: string; patch: UpdateEntityRequest }>();
  readonly requestSuggestion = output<ImportSuggestionRequest>();

  private readonly knowledgeService = inject(KnowledgeService);

  protected readonly selectedDomain = signal('');
  protected readonly selectedType = signal('');
  protected readonly title = signal('');
  protected readonly titleTouched = signal(false);
  protected readonly detailsOpen = signal(false);

  protected readonly aliasInput = signal('');
  protected readonly aliases = signal<string[]>([]);
  protected readonly description = signal('');

  protected readonly relationshipType = signal('');
  protected readonly relationshipQuery = signal('');
  protected readonly relationships = signal<Relationship[]>([]);
  private readonly relationshipQuery$ = new Subject<string>();

  protected readonly entityTypes = computed<EntityType[]>(() =>
    this.domains().find((domain: DomainDto) => domain.name === this.selectedDomain())?.entity_types ?? []
  );

  protected readonly relationshipTypes = computed<string[]>(() =>
    this.domains().find((domain: DomainDto) => domain.name === this.selectedDomain())?.relationship_types ?? []
  );

  protected readonly relationshipSuggestions = toSignal(
    this.relationshipQuery$.pipe(
      debounceTime(200),
      distinctUntilChanged(),
      switchMap((query: string) => {
        if (query.trim().length < 2) {
          return of([] as EntityDto[]);
        }
        return this.knowledgeService.searchEntities(query, undefined, this.selectedDomain()).pipe(
          catchError(() => of([] as EntityDto[])),
        );
      }),
    ),
    { initialValue: [] as EntityDto[] },
  );

  protected readonly titleError = computed((): string | null =>
    this.titleTouched() && this.title().trim().length === 0 ? 'Titel darf nicht leer sein.' : null
  );

  protected readonly isEditMode = computed((): boolean => this.editEntity() !== null);

  // KI-Vorschlag nur beim Anlegen (nicht beim Bearbeiten) und nur wenn die Funktion nicht
  // abgeschaltet ist — Import läuft ausschließlich über öffentliche Domänen (AK Phase 2).
  protected readonly showSuggestionButton = computed((): boolean =>
    !this.isEditMode() && this.importAutonomy() !== 'off'
  );

  protected readonly canRequestSuggestion = computed((): boolean =>
    this.showSuggestionButton() &&
    this.title().trim().length > 0 &&
    this.selectedType().trim().length > 0 &&
    !this.suggestionLoading()
  );

  // Der zuletzt bereits eingearbeitete Vorschlag — verhindert, dass derselbe Ergebnis-
  // Effekt die (evtl. schon vom Nutzer geänderten) Felder erneut überschreibt.
  private appliedResult: KnowledgeImportResult | null = null;

  protected readonly canSave = computed((): boolean =>
    this.title().trim().length > 0 &&
    this.selectedType().trim().length > 0 &&
    this.selectedDomain().trim().length > 0 &&
    !this.isSaving()
  );

  constructor() {
    // Domäne/Typ vorbelegen, sobald die Domänen-Liste (asynchron geladen) oder ein
    // Prefill (Phase 3: Wizard aus einer Aufgabe geöffnet) verfügbar ist. Eine zu
    // bearbeitende Entity (`editEntity`) gewinnt gegenüber dem reinen Anlage-Prefill —
    // sie bringt bereits alle Felder mit, nicht nur Titel/Typ.
    effect(() => {
      const domains = this.domains();
      if (domains.length === 0 || this.selectedDomain() !== '') { return; }
      const edit = this.editEntity();
      if (edit !== null) {
        this.selectedDomain.set(edit.domain);
        this.selectedType.set(edit.type);
        this.title.set(edit.title);
        this.aliases.set([...edit.aliases]);
        this.description.set(edit.body);
        this.relationships.set([...edit.relationships]);
        this.detailsOpen.set(true);
        return;
      }
      const prefill = this.prefill();
      const initialDomain = domains.find((domain: DomainDto) => domain.name === prefill.domain) ?? domains[0];
      if (initialDomain === undefined) { return; }
      this.selectedDomain.set(initialDomain.name);
      this.selectedType.set(prefill.type ?? initialDomain.entity_types[0]?.name ?? '');
      this.title.set(prefill.title ?? '');
    });

    // Trifft ein KI-Vorschlag ein, die Felder als bestätigungspflichtige Vorbelegung setzen
    // (nur die inhaltlichen — Typ/Domäne/Titel bleiben die Nutzer-Wahl). Jeder Vorschlag ist
    // ein neues Objekt aus dem Store, deshalb reicht die Referenz-Prüfung gegen Doppel-Anwenden.
    effect(() => {
      const result = this.suggestionResult();
      if (result === null || result === this.appliedResult) { return; }
      this.appliedResult = result;
      const suggestion = result.suggestion;
      if (suggestion === null) { return; }
      this.description.set(suggestion.body);
      this.aliases.set([...suggestion.aliases]);
      this.relationships.set([...suggestion.relationships]);
      this.detailsOpen.set(true);
    });
  }

  protected confidencePercent(confidence: number): number {
    return Math.round(confidence * 100);
  }

  protected onRequestSuggestion(): void {
    if (!this.canRequestSuggestion()) { return; }
    const request: ImportSuggestionRequest = {
      title: this.title().trim(),
      domain: this.selectedDomain(),
      type: this.selectedType(),
    };
    this.requestSuggestion.emit(request);
  }

  protected onDomainChange(domainName: string): void {
    this.selectedDomain.set(domainName);
    this.selectedType.set(this.entityTypes()[0]?.name ?? '');
    this.relationshipType.set('');
    this.relationships.set([]);
  }

  protected toggleDetails(): void {
    this.detailsOpen.update((open: boolean) => !open);
  }

  protected onAliasInputKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter' && event.key !== ',') { return; }
    event.preventDefault();
    this.commitAliasInput();
  }

  protected onAliasInputBlur(): void {
    this.commitAliasInput();
  }

  private commitAliasInput(): void {
    const value = this.aliasInput().trim();
    this.aliasInput.set('');
    if (!value || this.aliases().includes(value)) { return; }
    this.aliases.update((current: string[]) => [...current, value]);
  }

  protected removeAlias(alias: string): void {
    this.aliases.update((current: string[]) => current.filter((entry: string) => entry !== alias));
  }

  protected onRelationshipQueryInput(value: string): void {
    this.relationshipQuery.set(value);
    this.relationshipQuery$.next(value);
  }

  protected addRelationship(target: EntityDto): void {
    const type = this.relationshipType();
    if (!type) { return; }
    if (this.relationships().some((rel: Relationship) => rel.type === type && rel.target === target.id)) {
      return;
    }
    this.relationships.update((current: Relationship[]) => [...current, { type, target: target.id }]);
    this.relationshipQuery.set('');
    this.relationshipQuery$.next('');
  }

  protected removeRelationship(relationship: Relationship): void {
    this.relationships.update((current: Relationship[]) =>
      current.filter((entry: Relationship) => !(entry.type === relationship.type && entry.target === relationship.target))
    );
  }

  protected relationshipLabel(target: string): string {
    const [, slug] = target.split('/');
    return slug ?? target;
  }

  protected onConfirm(): void {
    this.titleTouched.set(true);
    if (!this.canSave()) { return; }

    const edit = this.editEntity();
    if (edit !== null) {
      const patch: UpdateEntityRequest = {
        title: this.title().trim(),
        aliases: this.aliases(),
        relationships: this.relationships(),
        body: this.description().trim(),
      };
      this.update.emit({ entityId: edit.id, patch });
      return;
    }

    const domain = this.selectedDomain();
    const type = this.selectedType();
    const folder = this.entityTypes().find((entityType: EntityType) => entityType.name === type)?.folder ?? type.toLowerCase();
    const request: CreateEntityRequest = {
      id: `${folder}/${this.slugify(this.title())}`,
      type,
      title: this.title().trim(),
      domain,
      aliases: this.aliases(),
      relationships: this.relationships(),
      body: this.description().trim(),
    };
    this.save.emit(request);
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('ew-scrim')) {
      this.close.emit();
    }
  }

  private slugify(value: string): string {
    return value
      .toLowerCase()
      .normalize('NFKD')
      .replace(/\p{Diacritic}/gu, '')
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }
}
