import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import type {
  CreateEntityRequest,
  Density,
  DomainDto,
  EntityDto,
  EntityRefDto,
  InterviewSynthesizeRequest,
  PersonDto,
  TaskDto,
} from '@photofant/models';
import { PersonService } from '@photofant/services';
import {
  galleryActions,
  gallerySelectors,
  knowledgeActions,
  knowledgeSelectors,
  personsActions,
  personsSelectors,
} from '@photofant/store';
import { Icon, LinkEntityDialog } from '@photofant/ui';
import { Lightbox } from '../galerie/lightbox/lightbox';
import { EntityWizardDialog } from '../wissen/entity-wizard-dialog/entity-wizard-dialog';
import { InterviewDialog, type WizardTarget } from '../wissen/interview-dialog/interview-dialog';
import { KnowledgeDetailDialog } from '../wissen/knowledge-detail-dialog/knowledge-detail-dialog';
import { WebSearchDialog } from '../wissen/web-search-dialog/web-search-dialog';
import { AlphabetRail } from './alphabet-rail/alphabet-rail';
import { CreatePersonDialog } from './create-person-dialog/create-person-dialog';
import { DeletePersonDialog } from './delete-person-dialog/delete-person-dialog';
import { DupeCheckDialog } from './dupe-check-dialog/dupe-check-dialog';
import { groupColor } from './group-color.util';
import { MergeDialog } from './merge-dialog/merge-dialog';
import { PersonCard } from './person-card/person-card';
import { SplitDialog } from './split-dialog/split-dialog';

type PersonSortKey = 'group' | 'created' | 'name' | 'unnamed' | 'count';
type PersonViewMode = 'single' | 'grid4' | 'face';

const NO_GROUP = 'Ohne Gruppe';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    PersonCard,
    MergeDialog,
    SplitDialog,
    DupeCheckDialog,
    CreatePersonDialog,
    DeletePersonDialog,
    AlphabetRail,
    Icon,
    EntityWizardDialog,
    LinkEntityDialog,
    KnowledgeDetailDialog,
    InterviewDialog,
    WebSearchDialog,
    Lightbox,
  ],
  templateUrl: './personen.html',
  styleUrl: './personen.scss',
})
export class Personen implements OnInit {
  private readonly store = inject(Store);
  private readonly personService = inject(PersonService);

  protected readonly groupColor = groupColor;

  private readonly SORT_CYCLE: PersonSortKey[] = ['group', 'created', 'name', 'unnamed', 'count'];
  private readonly SORT_LABELS: Record<PersonSortKey, string> = {
    group: 'Gruppe', created: 'Erstellungsdatum', name: 'Name',
    unnamed: 'Unbenannt zuerst', count: 'Anzahl Fotos',
  };

  protected readonly persons = this.store.selectSignal(personsSelectors.selectAll);
  protected readonly isLoading = this.store.selectSignal(personsSelectors.selectIsLoading);
  protected readonly isClustering = this.store.selectSignal(personsSelectors.selectIsClustering);

  // P24 Phase 2: "🆕 Neue Person"-Affordance auf der Personen-Karte, gespeist aus den
  // offenen Wissens-Aufgaben (store/knowledge) — nicht aus der Review-Faces-Queue, die
  // ist transient (bestätigen → nächstes Gesicht), die Person-Karte ist der dauerhafte Ort.
  protected readonly knowledgeDomains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly knowledgeDomainsLoading = this.store.selectSignal(knowledgeSelectors.selectDomainsLoading);
  protected readonly isSavingEntity = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly entitySaveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  private readonly lastCreatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);
  private readonly openTasks = this.store.selectSignal(knowledgeSelectors.selectAllTasks);

  // "Später" ist session-lokal (wie work-queue.ts) — ändert den Task-Status nicht,
  // blendet ihn nur bis zum nächsten Neuladen aus.
  private readonly snoozedTaskIds = signal<Set<number>>(new Set());

  protected readonly newPersonTaskByPersonId = computed((): Map<number, TaskDto> => {
    const snoozed = this.snoozedTaskIds();
    const map = new Map<number, TaskDto>();
    for (const task of this.openTasks()) {
      if (task.kind !== 'new_person' || snoozed.has(task.id)) { continue; }
      const personId = task.context['person_id'];
      if (typeof personId === 'number') {
        map.set(personId, task);
      }
    }
    return map;
  });

  protected readonly showKnowledgeWizard = signal(false);
  private readonly activeNewPersonTask = signal<TaskDto | null>(null);

  // P38 Phase 8 — zweiter Einstieg in denselben Wizard: "Web-Recherche starten" aus dem leeren
  // Detail-Modal (kein Wissen zur Person, keine bestehende Notiz). Die Entity ist hier nur das
  // Vehikel für Domäne/Typ — sobald sie steht, geht's im Effekt unten direkt in den
  // Web-Suche-Wizard weiter (gleiches Muster wie `wissen.ts`).
  protected readonly discoverySetupPersonId = signal<number | null>(null);
  protected readonly discoverySetupDomains = computed((): DomainDto[] =>
    this.knowledgeDomains().filter((domain: DomainDto) => !domain.private)
  );

  protected readonly knowledgeWizardPrefill = computed((): Partial<CreateEntityRequest> => {
    const discoveryPersonId = this.discoverySetupPersonId();
    if (discoveryPersonId !== null) {
      const person = this.persons().find((candidate: PersonDto) => candidate.id === discoveryPersonId) ?? null;
      return person?.name ? { title: person.name } : {};
    }
    const task = this.activeNewPersonTask();
    if (task === null) { return {}; }
    const ref = task.context['ref'];
    return typeof ref === 'string' && ref.length > 0 ? { title: ref } : {};
  });

  // P38 Phase 8 — Wissens-Detail-Modal direkt auf der Personen-Seite (Chip/Nudge auf der
  // Karte), damit der Nutzer für einen Blick aufs eigene Wissen nicht mehr nach `/wissen`
  // wegnavigiert werden muss. Nur `detailPersonId` — anders als `wissen.ts` gibt es hier keine
  // "Nicht verknüpfte Notizen"-Sektion, die eine zweite, entity-basierte Öffnung bräuchte.
  protected readonly detailPersonId = signal<number | null>(null);
  protected readonly detailRefreshKey = signal(0);

  protected readonly aiAutonomy = this.store.selectSignal(knowledgeSelectors.selectAiAutonomy);
  protected readonly interviewLoading = this.store.selectSignal(knowledgeSelectors.selectInterviewLoading);
  protected readonly interviewResult = this.store.selectSignal(knowledgeSelectors.selectInterviewResult);
  protected readonly interviewError = this.store.selectSignal(knowledgeSelectors.selectInterviewError);
  protected readonly showInterview = signal(false);
  protected readonly showWebSearchWizard = signal(false);
  protected readonly wizardTarget = signal<WizardTarget | null>(null);

  protected readonly knownPersons = computed((): PersonDto[] =>
    this.persons().filter((person: PersonDto) => !person.is_unknown)
  );

  protected readonly lightboxId = this.store.selectSignal(gallerySelectors.selectLightboxId);

  protected readonly showMergeDialog = signal(false);
  protected readonly mergePreselectedFrom = signal<PersonDto | null>(null);
  protected readonly showCreateDialog = signal(false);
  protected readonly linkEntityPerson = signal<PersonDto | null>(null);
  protected readonly splitPerson = signal<PersonDto | null>(null);
  protected readonly dupeCheckPerson = signal<PersonDto | null>(null);
  protected readonly deletePersonTarget = signal<PersonDto | null>(null);

  protected readonly searchQuery = signal('');
  protected readonly sortKey = signal<PersonSortKey>('group');
  protected readonly groupFilter = signal<Set<string>>(new Set());
  protected readonly viewMode = signal<PersonViewMode>('face');
  protected readonly cardSize = signal<Density>('md');

  protected readonly SIZES: { key: Density; iconSize: number }[] = [
    { key: 'sm', iconSize: 13 },
    { key: 'md', iconSize: 15 },
    { key: 'lg', iconSize: 17 },
  ];

  private readonly CARD_WIDTHS: Record<Density, number> = { sm: 150, md: 200, lg: 270 };

  protected readonly cardWidth = computed((): number => this.CARD_WIDTHS[this.cardSize()]);

  protected readonly NO_GROUP = NO_GROUP;

  protected readonly availableGroups = computed((): string[] => {
    const names = new Set<string>();
    for (const person of this.persons()) {
      if (person.group_name) { names.add(person.group_name); }
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  });

  protected readonly hasUngroupedPersons = computed((): boolean =>
    this.persons().some((person: PersonDto) => !person.group_name),
  );

  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.searchQuery().trim().toLowerCase();
    const groups = this.groupFilter();
    return this.persons().filter((person: PersonDto) => {
      if (query) {
        const label = (person.is_unknown ? 'unbekannt' : (person.name ?? '')).toLowerCase();
        if (!label.includes(query)) { return false; }
      }
      if (groups.size > 0) {
        const groupKey = person.group_name ?? NO_GROUP;
        if (!groups.has(groupKey)) { return false; }
      }
      return true;
    });
  });

  protected readonly sortedPersons = computed((): PersonDto[] => {
    const list = [...this.filteredPersons()];
    if (this.sortKey() === 'name') {
      return list.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
    }
    if (this.sortKey() === 'created') {
      return list.sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bTime - aTime; // neueste zuerst, NULL (=0) landet am Ende
      });
    }
    if (this.sortKey() === 'unnamed') {
      return list.sort((a, b) => {
        const aUnnamed = a.is_unknown || !a.name;
        const bUnnamed = b.is_unknown || !b.name;
        if (aUnnamed !== bUnnamed) { return aUnnamed ? -1 : 1; }
        return (a.name ?? '').localeCompare(b.name ?? '');
      });
    }
    if (this.sortKey() === 'count') {
      return list.sort((a, b) => b.count - a.count);
    }
    return list; // 'group' — Gruppierung übernimmt die Sortierung in personGroups()
  });

  protected readonly personGroups = computed((): { label: string; persons: PersonDto[] }[] => {
    if (this.sortKey() !== 'group') { return []; }
    const buckets = new Map<string, PersonDto[]>();
    for (const person of this.sortedPersons()) {
      const key = person.group_name ?? NO_GROUP;
      const bucket = buckets.get(key) ?? [];
      bucket.push(person);
      buckets.set(key, bucket);
    }
    const entries = [...buckets.entries()].sort(([a], [b]) => {
      if (a === NO_GROUP) { return 1; }
      if (b === NO_GROUP) { return -1; }
      return a.localeCompare(b);
    });
    return entries.map(([label, persons]) => ({ label, persons }));
  });

  constructor() {
    // Entity angelegt, während der Wizard offen war — drei mögliche Herkünfte, die sich
    // gegenseitig ausschließen (immer nur eine der beiden Ziel-Signale ist gesetzt):
    // (a) "🆕 Neue Person"-Karte -> Person↔Entity verknüpfen + Aufgabe auflösen,
    // (b) "Web-Recherche starten" aus dem leeren Detail-Modal -> direkt in den
    // Web-Suche-Wizard weiterreichen (P38 Phase 8, Muster wie `wissen.ts`).
    effect(() => {
      const entity = this.lastCreatedEntity();
      if (entity === null) { return; }
      this.showKnowledgeWizard.set(false);
      this.showInterview.set(false);

      const discoveryPersonId = this.discoverySetupPersonId();
      if (discoveryPersonId !== null) {
        this.discoverySetupPersonId.set(null);
        this.detailRefreshKey.update((tick: number): number => tick + 1);
        this.wizardTarget.set({ personId: discoveryPersonId, entityId: entity.id, name: entity.title });
        this.showWebSearchWizard.set(true);
        return;
      }

      const task = this.activeNewPersonTask();
      if (task !== null) {
        this.activeNewPersonTask.set(null);
        const personId = task.context['person_id'];
        if (typeof personId === 'number') {
          this.personService.linkEntity(personId, entity.id).subscribe(() => {
            this.store.dispatch(knowledgeActions.resolveTask({ taskId: task.id }));
          });
        }
        return;
      }

      // Übrig: Interview aus dem Detail-Modal — `interview-dialog.ts::onConfirm` hat die
      // Entity bereits per `media_links.persons` mit der Person verknüpft, nur Personen/Detail
      // neu laden, damit Chip-Prozentwert und Modal den frischen Stand zeigen.
      this.store.dispatch(personsActions.loadPersons());
      this.detailRefreshKey.update((tick: number): number => tick + 1);
    });
  }

  ngOnInit(): void {
    this.store.dispatch(personsActions.loadPersons());
    this.store.dispatch(knowledgeActions.loadDomains());
    this.store.dispatch(knowledgeActions.loadTasks());
    this.store.dispatch(knowledgeActions.loadAiAutonomy());
  }

  protected onCreateKnowledge(task: TaskDto): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.activeNewPersonTask.set(task);
    this.showKnowledgeWizard.set(true);
  }

  protected onSnoozeNewPersonTask(taskId: number): void {
    this.snoozedTaskIds.update((current: Set<number>) => new Set(current).add(taskId));
  }

  protected onDismissNewPersonTask(taskId: number): void {
    this.store.dispatch(knowledgeActions.dismissTask({ taskId }));
  }

  protected onCloseKnowledgeWizard(): void {
    this.showKnowledgeWizard.set(false);
    this.activeNewPersonTask.set(null);
    this.discoverySetupPersonId.set(null);
  }

  protected onSaveKnowledgeEntity(request: CreateEntityRequest): void {
    this.store.dispatch(knowledgeActions.createEntity({ request }));
  }

  // P38 Phase 8 — Chip/Nudge auf der Personen-Karte öffnen das Detail-Modal direkt hier.
  protected openPersonDetail(personId: number): void {
    this.detailPersonId.set(personId);
  }

  protected closeDetail(): void {
    this.detailPersonId.set(null);
  }

  protected openInterviewForDetail(): void {
    const personId = this.detailPersonId();
    const person = personId !== null ? this.persons().find((candidate: PersonDto) => candidate.id === personId) ?? null : null;
    this.wizardTarget.set({ personId, entityId: null, name: person?.name ?? null });
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

  protected openWebSearchForDetail(): void {
    const personId = this.detailPersonId();
    const person = personId !== null ? this.persons().find((candidate: PersonDto) => candidate.id === personId) ?? null : null;
    this.wizardTarget.set({ personId, entityId: null, name: person?.name ?? null });
    this.showWebSearchWizard.set(true);
  }

  protected closeWebSearchWizard(): void {
    this.showWebSearchWizard.set(false);
  }

  protected onWebSearchApplied(): void {
    this.store.dispatch(knowledgeActions.loadTasks());
    this.store.dispatch(personsActions.loadPersons());
    this.detailRefreshKey.update((tick: number): number => tick + 1);
  }

  // Leerer Detail-Zustand -> "Web-Recherche starten" (analog `wissen.ts`): legt eine Entity nur
  // als Vehikel für Domäne/Typ an, der Effekt oben reicht danach in den Web-Suche-Wizard weiter.
  protected openDiscoverySetupForDetail(): void {
    const personId = this.detailPersonId();
    if (personId === null) { return; }
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.store.dispatch(knowledgeActions.resetImportSuggestion());
    this.activeNewPersonTask.set(null);
    this.discoverySetupPersonId.set(personId);
    this.showKnowledgeWizard.set(true);
  }

  protected onDetailLinkRequested(): void {
    const personId = this.detailPersonId();
    const person = personId !== null ? this.persons().find((candidate: PersonDto) => candidate.id === personId) ?? null : null;
    if (person !== null) { this.linkEntityPerson.set(person); }
  }

  protected onDetailUnlinkRequested(entityId: string): void {
    const personId = this.detailPersonId();
    if (personId === null) { return; }
    this.store.dispatch(personsActions.unlinkPersonEntity({ personId, entityId }));
    this.detailRefreshKey.update((tick: number): number => tick + 1);
  }

  protected onOpenLightboxFromDetail(assetId: number): void {
    this.store.dispatch(galleryActions.openAssetLightbox({ assetId }));
  }

  protected onRename(event: { id: number; name: string }): void {
    this.store.dispatch(personsActions.renamePerson(event));
  }

  protected onSetGroup(event: { id: number; groupName: string }): void {
    this.store.dispatch(personsActions.setPersonGroup({ id: event.id, groupName: event.groupName || null }));
  }

  protected onImportFiles(event: { personId: number; files: File[] }): void {
    this.personService.importToPersonFolder(event.personId, event.files).subscribe();
  }

  protected onDupeCheck(person: PersonDto): void {
    this.dupeCheckPerson.set(person);
  }

  protected onRevealInFileBrowser(person: PersonDto): void {
    this.personService.revealPersonFolder(person.id).subscribe();
  }

  protected onMergeClick(person: PersonDto): void {
    this.mergePreselectedFrom.set(person);
    this.showMergeDialog.set(true);
  }

  protected onMerge(event: { fromId: number; intoId: number }): void {
    this.store.dispatch(personsActions.mergePersons(event));
    this.closeMergeDialog();
  }

  protected closeMergeDialog(): void {
    this.showMergeDialog.set(false);
    this.mergePreselectedFrom.set(null);
  }

  protected onSplitClick(person: PersonDto): void {
    this.splitPerson.set(person);
  }

  protected onSplit(event: { personId: number; faceIds: number[] }): void {
    this.store.dispatch(personsActions.splitPerson(event));
    this.splitPerson.set(null);
  }

  protected onDeleteClick(person: PersonDto): void {
    this.deletePersonTarget.set(person);
  }

  protected onConfirmDelete(personId: number): void {
    this.store.dispatch(personsActions.deletePerson({ id: personId }));
    this.deletePersonTarget.set(null);
  }

  protected onLinkEntityClick(person: PersonDto): void {
    this.linkEntityPerson.set(person);
  }

  protected onLinkEntitySelect(entity: EntityDto): void {
    const person = this.linkEntityPerson();
    if (person === null) { return; }
    this.store.dispatch(personsActions.linkPersonEntity({ personId: person.id, entityId: entity.id }));
    this.linkEntityPerson.set(null);
  }

  protected onUnlinkEntity(person: PersonDto, entity: EntityRefDto): void {
    this.store.dispatch(personsActions.unlinkPersonEntity({ personId: person.id, entityId: entity.id }));
  }

  protected onCreatePerson(name: string): void {
    this.store.dispatch(personsActions.createPerson({ name }));
    this.showCreateDialog.set(false);
  }

  protected cycleSortKey(): void {
    const currentIndex = this.SORT_CYCLE.indexOf(this.sortKey());
    const next = this.SORT_CYCLE[(currentIndex + 1) % this.SORT_CYCLE.length] ?? 'group';
    this.sortKey.set(next);
  }

  protected sortLabel(): string {
    return this.SORT_LABELS[this.sortKey()];
  }

  protected toggleGroupFilter(groupName: string): void {
    const next = new Set(this.groupFilter());
    if (next.has(groupName)) { next.delete(groupName); } else { next.add(groupName); }
    this.groupFilter.set(next);
  }

  protected setViewMode(mode: PersonViewMode): void {
    this.viewMode.set(mode);
  }

  protected setCardSize(size: Density): void {
    this.cardSize.set(size);
  }

  protected triggerClustering(): void {
    this.store.dispatch(personsActions.triggerClustering());
  }

  protected onAlphabetJump(personId: number): void {
    document.getElementById(`person-${personId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
