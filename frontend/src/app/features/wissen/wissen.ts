import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import type {
  AiAutonomyMode,
  CreateEntityRequest,
  DomainDto,
  EntityDto,
  ImportSuggestionRequest,
  InterviewSynthesizeRequest,
  PersonDto,
  TaskDto,
  UpdateEntityRequest,
} from '@photofant/models';
import { PersonService } from '@photofant/services';
import { galleryActions, gallerySelectors, knowledgeActions, knowledgeSelectors, personsActions, personsSelectors } from '@photofant/store';
import { Icon, LinkEntityDialog } from '@photofant/ui';
import { Lightbox } from '../galerie/lightbox/lightbox';
import { EntityWizardDialog } from './entity-wizard-dialog/entity-wizard-dialog';
import { InterviewDialog, type WizardTarget } from './interview-dialog/interview-dialog';
import { KnowledgeDetailDialog } from './knowledge-detail-dialog/knowledge-detail-dialog';
import { PersonKnowledgeCard } from './person-knowledge-card/person-knowledge-card';
import { WebSearchDialog } from './web-search-dialog/web-search-dialog';
import { WorkQueue } from './work-queue/work-queue';

const TOAST_DURATION_MS = 2800;

@Component({
  selector: 'pf-wissen',
  imports: [
    Icon,
    EntityWizardDialog,
    InterviewDialog,
    WebSearchDialog,
    WorkQueue,
    PersonKnowledgeCard,
    LinkEntityDialog,
    KnowledgeDetailDialog,
    Lightbox,
  ],
  templateUrl: './wissen.html',
  styleUrl: './wissen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Wissen {
  private readonly store = inject(Store);
  private readonly personService = inject(PersonService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);

  // Lightbox-Guard (wie Galerie/Favoriten/Alben): ohne dieses Signal rendert `<pf-lightbox />`
  // immer, auch ohne ausgewähltes Bild — die Lightbox hat keinen eigenen Leer-Zustand und
  // legt dann einen leeren Scrim über die ganze Seite.
  protected readonly lightboxId = this.store.selectSignal(gallerySelectors.selectLightboxId);

  protected readonly domains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly domainsLoading = this.store.selectSignal(knowledgeSelectors.selectDomainsLoading);
  protected readonly isSaving = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly saveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  protected readonly lastCreatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);
  protected readonly lastUpdatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastUpdatedEntity);

  protected readonly entities = this.store.selectSignal(knowledgeSelectors.selectAllEntities);
  protected readonly entitiesLoading = this.store.selectSignal(knowledgeSelectors.selectEntitiesLoading);
  private readonly entitiesById = this.store.selectSignal(knowledgeSelectors.selectEntityDictionary);

  protected readonly tasks = this.store.selectSignal(knowledgeSelectors.selectAllTasks);
  protected readonly tasksLoading = this.store.selectSignal(knowledgeSelectors.selectTasksLoading);
  protected readonly tasksError = this.store.selectSignal(knowledgeSelectors.selectTasksError);

  // P38 Phase 5 — Personen-Grid der Übersicht.
  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly personsLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly knownPersons = computed((): PersonDto[] =>
    this.persons().filter((person: PersonDto) => !person.is_unknown)
  );

  // EntityRefDto (person.linked_entity) trägt keine Domäne — über die vollständige
  // Entity-Liste auflösen, die für die Übersicht ohnehin schon geladen ist.
  protected readonly entityDomainById = computed((): Record<string, string> => {
    const map: Record<string, string> = {};
    for (const entity of this.entities()) {
      map[entity.id] = entity.domain;
    }
    return map;
  });

  // P38 Phase 7 — Umkehrung von `person.linked_entity.id`, damit eine Aufgabe, die nur eine
  // `entity_id` im Kontext trägt (missing_field/low_completeness), trotzdem eine Person für
  // den Wizard-Preset auflösen kann, falls die Entity an eine Person verknüpft ist.
  protected readonly personIdByEntityId = computed((): Record<string, number> => {
    const map: Record<string, number> = {};
    for (const person of this.persons()) {
      if (person.linked_entity !== null) {
        map[person.linked_entity.id] = person.id;
      }
    }
    return map;
  });

  // P38 Phase 5 — Sektion "Nicht verknüpfte Notizen": private Entities ohne Personen-Link.
  protected readonly unlinkedEntities = computed((): EntityDto[] => {
    const privateDomainNames = new Set(
      this.domains()
        .filter((domain: DomainDto) => domain.private)
        .map((domain: DomainDto) => domain.name)
    );
    return this.entities().filter(
      (entity: EntityDto) => privateDomainNames.has(entity.domain) && entity.media_links.persons.length === 0
    );
  });

  // P27 Phase 2 — KI-Vorschlag im Wizard. Protected (statt private): Phase 6 reicht das
  // volle DTO unverändert an das Detail-Modal durch (Web-Suche-/KI-Banner-Gating dort).
  protected readonly aiAutonomy = this.store.selectSignal(knowledgeSelectors.selectAiAutonomy);
  protected readonly importAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.knowledge_import ?? 'off');
  protected readonly suggestionLoading = this.store.selectSignal(knowledgeSelectors.selectSuggestionLoading);
  protected readonly suggestionResult = this.store.selectSignal(knowledgeSelectors.selectSuggestionResult);
  protected readonly suggestionError = this.store.selectSignal(knowledgeSelectors.selectSuggestionError);

  // P27 Phase 4 — Interview-Mode für private Personen. Nur angeboten, wenn die Funktion
  // nicht abgeschaltet ist UND eine private Domäne existiert (Konzept-ADR-009).
  protected readonly interviewAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.interview ?? 'off');
  protected readonly hasPrivateDomain = computed((): boolean =>
    this.domains().some((domain: DomainDto) => domain.private)
  );
  protected readonly showInterviewButton = computed((): boolean =>
    this.interviewAutonomy() !== 'off' && this.hasPrivateDomain()
  );
  protected readonly interviewLoading = this.store.selectSignal(knowledgeSelectors.selectInterviewLoading);
  protected readonly interviewResult = this.store.selectSignal(knowledgeSelectors.selectInterviewResult);
  protected readonly interviewError = this.store.selectSignal(knowledgeSelectors.selectInterviewError);
  protected readonly showInterview = signal(false);

  // P38 Phase 5 — "Web-Suche"-Knopf, gleicher Schalter wie der Backend-Guard.
  protected readonly discoveryAutonomy = computed((): AiAutonomyMode => this.aiAutonomy()?.discovery ?? 'off');
  protected readonly showWebSearchButton = computed((): boolean => this.discoveryAutonomy() === 'auto');
  protected readonly showWebSearchWizard = signal(false);

  // P38 Phase 7 — Vorbelegung für beide Wizards (Aufgabe 4, gemeinsames Signal). `entityId`
  // ist eine Erweiterung über die Plan-Basisform hinaus (siehe `WizardTarget`, Report-Back):
  // deckt Web-Suche auf einer unverknüpften, nicht-privaten Notiz ohne Personen-Bezug ab.
  protected readonly wizardTarget = signal<WizardTarget | null>(null);

  protected readonly showWizard = signal(false);
  // Gesetzt, wenn der Wizard eine bestehende Entity bearbeitet (z.B. aus der Aufgabe
  // "Entity noch ohne Inhalt") statt eine neue anzulegen.
  protected readonly editingEntity = signal<EntityDto | null>(null);
  // Wizard aus einer Aufgabe geöffnet? -> nach Erfolg diese Aufgabe auflösen statt nur zu schließen.
  private readonly activeTask = signal<TaskDto | null>(null);

  // P38 Phase 6 — Wissen-Detail-Modal: genau eines der beiden ist gesetzt (Person aus dem
  // Grid, Entity aus der Notizen-Sektion).
  protected readonly detailPersonId = signal<number | null>(null);
  protected readonly detailEntityId = signal<string | null>(null);
  // Nach einer Verknüpfung/Trennung hochgezählt — stößt im Modal einen frischen Lore-Read an.
  protected readonly detailRefreshKey = signal(0);

  // Leerer Detail-Zustand -> "Web-Recherche starten": merkt sich, für welche Person gerade
  // eine Entity nur zu dem Zweck angelegt wird, sie danach in den Web-Suche-Wizard zu
  // überführen (Aufgabe des Users: Nutzer bemerkte, dass es sonst außer "Interview" keinen
  // Weg für öffentliche Personen ohne bestehende Notiz gab).
  protected readonly discoverySetupPersonId = signal<number | null>(null);
  // Discovery darf nie auf einer privaten Domäne laufen (Backend lehnt das ohnehin ab,
  // `_is_private_domain`-Guard) — der Wizard bekommt in diesem Modus nur die Auswahl, die
  // hinterher nicht in eine Sackgasse läuft.
  protected readonly discoverySetupDomains = computed((): DomainDto[] =>
    this.domains().filter((domain: DomainDto) => !domain.private)
  );

  // P38 Phase 5 — "Verknüpfen" auf einer unverknüpften Notiz: Personen-Suche öffnen.
  protected readonly linkingEntity = signal<EntityDto | null>(null);
  // P38 Phase 6 — umgekehrte Richtung: aus dem leeren Detail-Zustand eine bestehende Notiz
  // für eine feste Person suchen ("Bestehende Notiz verknüpfen").
  protected readonly linkingPersonForEntity = signal<PersonDto | null>(null);

  // P38 Phase 5 — Toast statt der beiden statischen Bestätigungs-Blöcke.
  protected readonly toastMessage = signal<string | null>(null);
  private toastTimeoutId: ReturnType<typeof setTimeout> | null = null;

  protected readonly wizardPrefill = computed((): Partial<CreateEntityRequest> => {
    const discoveryPersonId = this.discoverySetupPersonId();
    if (discoveryPersonId !== null) {
      const person = this.knownPersons().find((candidate: PersonDto) => candidate.id === discoveryPersonId) ?? null;
      return person?.name ? { title: person.name } : {};
    }
    const task = this.activeTask();
    if (task === null) { return {}; }
    const title = task.context['title'];
    if (typeof title === 'string' && title.length > 0) {
      return { title };
    }
    const ref = task.context['ref'];
    if (typeof ref === 'string' && ref.length > 0) {
      return { title: ref };
    }
    return {};
  });

  constructor() {
    this.store.dispatch(knowledgeActions.loadDomains());
    this.store.dispatch(knowledgeActions.loadTasks());
    this.store.dispatch(knowledgeActions.loadEntities());
    this.store.dispatch(knowledgeActions.loadAiAutonomy());
    this.store.dispatch(personsActions.loadPersons());

    // Wizard schließt sich selbst, sobald Anlegen ODER Bearbeiten erfolgreich war; kam
    // er aus einer Aufgabe, wird die Aufgabe im selben Zug aufgelöst.
    effect(() => {
      const created = this.lastCreatedEntity();
      const updated = this.lastUpdatedEntity();
      if (created === null && updated === null) { return; }
      this.showWizard.set(false);
      this.showInterview.set(false);
      this.editingEntity.set(null);
      const task = this.activeTask();
      if (task !== null) {
        this.store.dispatch(knowledgeActions.resolveTask({ taskId: task.id }));
        this.activeTask.set(null);
      }

      // "Web-Recherche starten" aus dem leeren Detail-Zustand: die Entity war nur das
      // Vehikel für die Domäne/Typ-Wahl — sobald sie steht, sofort in den Web-Suche-Wizard
      // weiterreichen statt hier mit einem Zwischen-Toast zu unterbrechen (der kommt, sobald
      // die Recherche selbst etwas übernimmt, siehe `onWebSearchApplied`).
      const discoveryPersonId = this.discoverySetupPersonId();
      if (created !== null && discoveryPersonId !== null) {
        this.discoverySetupPersonId.set(null);
        this.detailRefreshKey.update((tick: number): number => tick + 1);
        this.wizardTarget.set({ personId: discoveryPersonId, entityId: created.id, name: created.title });
        this.showWebSearchWizard.set(true);
        return;
      }

      if (created !== null) {
        this.showToast(`„${created.title}" (${created.type}) angelegt.`);
      } else if (updated !== null) {
        this.showToast(`„${updated.title}" aktualisiert.`);
      }
    });

    // P38 Phase 8 — Deep-Link von Personen-Karte/Lightbox: `?person=<id>` öffnet das
    // Detail-Modal, `?entity=<id>` das für eine Notiz; `&open=interview`/`&open=discovery`
    // öffnet stattdessen direkt den jeweiligen Wizard (Recherchieren/Interview starten aus dem
    // Lore-Panel). Wartet auf den ersten Personen-/Entities-Ladevorgang, damit der
    // Wizard-Titel/das Modal sofort einen Namen zeigt statt kurz leer aufzublitzen — feuert
    // nur einmal pro Seitenaufruf (`deepLinkHandled`-Guard), sonst würde jeder Persons-/
    // Entities-Reload danach den Deep-Link erneut auslösen.
    const deepLinkHandled = signal(false);
    effect(() => {
      if (deepLinkHandled()) { return; }
      const params = this.route.snapshot.queryParamMap;
      const personParam = params.get('person');
      const entityParam = params.get('entity');
      if (personParam === null && entityParam === null) {
        deepLinkHandled.set(true);
        return;
      }
      if (personParam !== null && this.personsLoading()) { return; }
      if (entityParam !== null && this.entitiesLoading()) { return; }
      deepLinkHandled.set(true);

      const openParam = params.get('open');
      if (personParam !== null) {
        const personId = Number(personParam);
        if (openParam === 'interview') {
          const person = this.knownPersons().find((candidate: PersonDto) => candidate.id === personId) ?? null;
          this.wizardTarget.set({ personId, entityId: null, name: person?.name ?? null });
          this.showInterview.set(true);
        } else {
          this.openPersonDetail(personId);
        }
        return;
      }
      if (entityParam !== null) {
        if (openParam === 'discovery') {
          const entity = this.entitiesById()[entityParam] ?? null;
          this.wizardTarget.set({ personId: null, entityId: entityParam, name: entity?.title ?? null });
          this.showWebSearchWizard.set(true);
        } else {
          this.detailEntityId.set(entityParam);
          this.detailPersonId.set(null);
        }
      }
    });

    this.destroyRef.onDestroy(() => {
      if (this.toastTimeoutId !== null) {
        clearTimeout(this.toastTimeoutId);
      }
    });
  }

  private showToast(message: string): void {
    this.toastMessage.set(message);
    if (this.toastTimeoutId !== null) {
      clearTimeout(this.toastTimeoutId);
    }
    this.toastTimeoutId = setTimeout(() => this.toastMessage.set(null), TOAST_DURATION_MS);
  }

  protected openInterview(): void {
    this.wizardTarget.set(null);
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetInterview());
    this.showInterview.set(true);
  }

  // Aus dem Detail-Kopf (Phase 6) — die dort offene Person/Notiz wird zum Preset.
  protected openInterviewForDetail(): void {
    this.wizardTarget.set(this.currentDetailTarget());
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetInterview());
    this.showInterview.set(true);
  }

  protected closeInterview(): void {
    this.store.dispatch(knowledgeActions.resetInterview());
    this.showInterview.set(false);
  }

  protected onRequestInterview(request: InterviewSynthesizeRequest): void {
    this.store.dispatch(knowledgeActions.requestInterview({ request }));
  }

  protected openWebSearchWizard(): void {
    this.wizardTarget.set(null);
    this.showWebSearchWizard.set(true);
  }

  // Aus dem Detail-Kopf (Phase 6) — nur sichtbar, wenn `canRequestWebSearch` dort bereits
  // gilt (nicht-private Domäne, Autonomie an); die aktuell offene Entity wird zum Preset.
  protected openWebSearchForDetail(): void {
    this.wizardTarget.set(this.currentDetailTarget());
    this.showWebSearchWizard.set(true);
  }

  protected closeWebSearchWizard(): void {
    this.showWebSearchWizard.set(false);
  }

  // Preset aus dem gerade offenen Detail-Modal ableiten — Person, falls über `detailPersonId`
  // geöffnet, sonst die Entity selbst (unverknüpfte Notiz).
  private currentDetailTarget(): WizardTarget {
    const personId = this.detailPersonId();
    if (personId !== null) {
      const person = this.knownPersons().find((candidate: PersonDto) => candidate.id === personId) ?? null;
      return { personId, entityId: null, name: person?.name ?? null };
    }
    const entityId = this.detailEntityId();
    const entity = entityId !== null ? this.entitiesById()[entityId] ?? null : null;
    return { personId: null, entityId, name: entity?.title ?? null };
  }

  // Web-Suche-Wizard hat geschrieben — Entities/Aufgaben neu laden (Vollständigkeit/„Feld
  // fehlt"-Aufgaben ändern sich), Toast wie bei den anderen Übernahme-Wegen.
  protected onWebSearchApplied(event: { writtenCount: number }): void {
    this.store.dispatch(knowledgeActions.loadEntities());
    this.store.dispatch(knowledgeActions.loadTasks());
    this.detailRefreshKey.update((tick: number): number => tick + 1);
    this.showToast(event.writtenCount > 0 ? `${event.writtenCount} Merkmale übernommen.` : 'Übernahme abgeschlossen.');
  }

  protected openWizard(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(null);
    this.editingEntity.set(null);
    this.discoverySetupPersonId.set(null);
    this.showWizard.set(true);
  }

  protected closeWizard(): void {
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.showWizard.set(false);
    this.activeTask.set(null);
    this.editingEntity.set(null);
    this.discoverySetupPersonId.set(null);
  }

  // Leerer Detail-Zustand -> "Web-Recherche starten" (Nutzer-Fund: ohne bestehende Notiz gab
  // es außer "Interview" keinen Weg für öffentliche Personen). Öffnet denselben Entity-Wizard
  // wie der normale "+"-Knopf, aber mit Namen vorbelegt und auf nicht-private Domänen
  // eingeschränkt — die Anlage selbst ist nur der Zwischenschritt, siehe Effekt oben.
  protected openDiscoverySetup(): void {
    const personId = this.detailPersonId();
    if (personId === null) { return; }
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(null);
    this.editingEntity.set(null);
    this.discoverySetupPersonId.set(personId);
    this.showWizard.set(true);
  }

  protected onRequestSuggestion(request: ImportSuggestionRequest): void {
    this.store.dispatch(knowledgeActions.requestImportSuggestion({ request }));
  }

  protected onSave(request: CreateEntityRequest): void {
    this.store.dispatch(knowledgeActions.createEntity({ request }));
  }

  protected onUpdate(event: { entityId: string; patch: UpdateEntityRequest }): void {
    this.store.dispatch(knowledgeActions.updateEntity(event));
  }

  // Klick auf eine Personen-Karte -> Detail öffnen.
  protected openPersonDetail(personId: number): void {
    this.detailPersonId.set(personId);
    this.detailEntityId.set(null);
  }

  // Klick auf eine unverknüpfte Notiz-Karte -> dasselbe Modal, andere Datenquelle.
  protected openEntityDetail(entity: EntityDto): void {
    this.detailEntityId.set(entity.id);
    this.detailPersonId.set(null);
  }

  protected closeDetail(): void {
    this.detailPersonId.set(null);
    this.detailEntityId.set(null);
  }

  protected openLinkPicker(entity: EntityDto): void {
    this.linkingEntity.set(entity);
  }

  protected closeLinkPicker(): void {
    this.linkingEntity.set(null);
  }

  protected onLinkNoteToPerson(person: PersonDto): void {
    const entity = this.linkingEntity();
    if (entity === null) { return; }
    this.personService.linkEntity(person.id, entity.id).subscribe(() => {
      this.linkingEntity.set(null);
      this.store.dispatch(knowledgeActions.loadEntities());
      this.store.dispatch(personsActions.loadPersons());
      this.store.dispatch(knowledgeActions.loadTasks());
      this.showToast(`„${entity.title}" mit ${person.name ?? 'Unbenannt'} verknüpft.`);
    });
  }

  // P38 Phase 6 — leerer Detail-Zustand: "Bestehende Notiz verknüpfen" sucht eine Entity für
  // die feste, gerade offene Person (Gegenrichtung zu `openLinkPicker` oben).
  protected onDetailLinkRequested(): void {
    const personId = this.detailPersonId();
    if (personId === null) { return; }
    const person = this.knownPersons().find((candidate: PersonDto) => candidate.id === personId) ?? null;
    this.linkingPersonForEntity.set(person);
  }

  protected closeLinkEntityPicker(): void {
    this.linkingPersonForEntity.set(null);
  }

  protected onLinkEntityToPerson(entity: EntityDto): void {
    const person = this.linkingPersonForEntity();
    if (person === null) { return; }
    this.personService.linkEntity(person.id, entity.id).subscribe(() => {
      this.linkingPersonForEntity.set(null);
      this.store.dispatch(knowledgeActions.loadEntities());
      this.store.dispatch(personsActions.loadPersons());
      this.store.dispatch(knowledgeActions.loadTasks());
      this.detailRefreshKey.update((tick: number): number => tick + 1);
      this.showToast(`„${entity.title}" mit ${person.name ?? 'Unbenannt'} verknüpft.`);
    });
  }

  // "Verknüpfung lösen" im Detail-Kopf — trennt die Zuordnung, die Notiz bleibt erhalten und
  // taucht danach unter "Nicht verknüpfte Notizen" auf (kein Datenverlust, AK dieser Phase).
  protected onDetailUnlinkRequested(entityId: string): void {
    const personId = this.detailPersonId();
    if (personId === null) { return; }
    this.personService.unlinkEntity(personId, entityId).subscribe(() => {
      this.store.dispatch(knowledgeActions.loadEntities());
      this.store.dispatch(personsActions.loadPersons());
      this.store.dispatch(knowledgeActions.loadTasks());
      this.detailRefreshKey.update((tick: number): number => tick + 1);
      this.showToast('Verknüpfung gelöst — die Notiz bleibt erhalten.');
    });
  }

  protected onOpenLightboxFromDetail(assetId: number): void {
    this.store.dispatch(galleryActions.openAssetLightbox({ assetId }));
  }

  // Kein `updated_at` im EntityDto-Kontrakt (P38 Phase 2/3 fixiert) — die Meta-Zeile zeigt
  // deshalb nur den Prozentwert, kein "geändert am {Datum}" wie im Design-Mock (dort mit
  // erfundenen Mock-Daten belegt). Siehe Report-Back.
  protected unlinkedPercent(entity: EntityDto): number {
    return Math.round(entity.completeness * 100);
  }

  // P38 Phase 7 — "Feld fehlt"/"Kaum ausgefüllt" zielen auf eine bestehende Entity und lassen
  // sich nur über die Web-Suche wirklich beheben (der Entity-Wizard unten kennt keine
  // Merkmale) — andere Aufgaben-Arten öffnen unverändert den Entity-Wizard.
  protected resolveTask(task: TaskDto): void {
    if (task.kind === 'missing_field' || task.kind === 'low_completeness') {
      const entityId = task.context['entity_id'];
      if (typeof entityId === 'string') {
        const title = task.context['title'];
        const personId = this.personIdByEntityId()[entityId] ?? null;
        this.wizardTarget.set({
          personId,
          entityId,
          name: typeof title === 'string' && title.length > 0 ? title : null,
        });
        this.showWebSearchWizard.set(true);
        return;
      }
    }
    this.resolveTaskViaWizard(task);
  }

  private resolveTaskViaWizard(task: TaskDto): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeTask.set(task);
    this.discoverySetupPersonId.set(null);
    // "Entity noch ohne Inhalt" verweist auf eine bestehende Entity (`entity_id` im
    // Task-Kontext) -> Wizard im Edit-Modus öffnen statt eine neue anzulegen.
    if (task.kind === 'incomplete_entity') {
      const entityId = task.context['entity_id'];
      this.editingEntity.set(typeof entityId === 'string' ? this.entitiesById()[entityId] ?? null : null);
    } else {
      this.editingEntity.set(null);
    }
    this.showWizard.set(true);
  }

  protected dismissTask(taskId: number): void {
    this.store.dispatch(knowledgeActions.dismissTask({ taskId }));
  }
}
