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
import { Store } from '@ngrx/store';
import type { AssetDto, CollectionDetail, MatchMode, PersonDto, TagListItem, Trigger, TriggerType } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { collectionsActions, personsActions, personsSelectors, tagsActions, tagsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

type AddTab = TriggerType;

@Component({
  selector: 'pf-album-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './album-settings.html',
  styleUrl: './album-settings.scss',
})
export class AlbumSettings {
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);

  readonly collection = input.required<CollectionDetail>();
  readonly memberCount = input<number>(0);
  readonly members = input<AssetDto[]>([]);

  readonly close = output<void>();

  // Beschreibung — lokaler Entwurf, gespeichert bei Blur (P10 Phase 1)
  protected readonly descriptionDraft = signal('');

  private readonly allTags = this.store.selectSignal(tagsSelectors.selectAll);
  private readonly allPersons = this.store.selectSignal(personsSelectors.selectAll);

  protected readonly addTab = signal<AddTab>('tag');
  protected readonly adding = signal(false);
  protected readonly tagQuery = signal('');
  protected readonly personQuery = signal('');
  protected readonly phrase = signal('');

  protected readonly smartOn = computed((): boolean => this.collection().kind === 'smart_album');
  protected readonly matchMode = computed((): MatchMode => this.collection().match_mode);
  protected readonly triggers = computed((): Trigger[] => this.collection().triggers);

  protected readonly availableTags = computed((): TagListItem[] => {
    const usedTagIds = new Set(
      this.triggers().filter((trigger: Trigger) => trigger.type === 'tag').map((trigger: Trigger) => trigger.tag_id),
    );
    const query = this.tagQuery().toLowerCase().trim();
    return this.allTags()
      .filter((tag: TagListItem) => !usedTagIds.has(tag.id) && tag.alias_of == null)
      .filter((tag: TagListItem) => (query ? tag.name.includes(query) : true))
      .slice(0, 18);
  });

  protected readonly availablePersons = computed((): PersonDto[] => {
    const usedPersonIds = new Set(
      this.triggers().filter((trigger: Trigger) => trigger.type === 'person').map((trigger: Trigger) => trigger.person_id),
    );
    const query = this.personQuery().toLowerCase().trim();
    return this.allPersons()
      .filter((person: PersonDto) => !person.is_unknown && !usedPersonIds.has(person.id))
      .filter((person: PersonDto) => (query ? (person.name ?? '').toLowerCase().includes(query) : true))
      .slice(0, 18);
  });

  constructor() {
    this.store.dispatch(tagsActions.load());
    this.store.dispatch(personsActions.loadPersons());

    // Entwurf mit dem Server-Stand synchron halten, wenn ein anderes Album geöffnet wird.
    effect((): void => {
      this.descriptionDraft.set(this.collection().description ?? '');
    });
  }

  protected toggleSmart(): void {
    this.store.dispatch(collectionsActions.update({
      id: this.collection().id,
      request: { kind: this.smartOn() ? 'album' : 'smart_album' },
    }));
  }

  protected setMode(mode: MatchMode): void {
    if (this.matchMode() === mode) { return; }
    this.store.dispatch(collectionsActions.update({
      id: this.collection().id,
      request: { match_mode: mode },
    }));
  }

  protected setAddTab(tab: AddTab): void {
    this.addTab.set(tab);
  }

  protected addTagTrigger(tagId: number): void {
    this.store.dispatch(collectionsActions.addTrigger({
      collectionId: this.collection().id,
      request: { type: 'tag', tag_id: tagId },
    }));
    this.tagQuery.set('');
    this.adding.set(false);
  }

  protected addCaptionTrigger(): void {
    const phrase = this.phrase().trim();
    if (!phrase) { return; }
    this.store.dispatch(collectionsActions.addTrigger({
      collectionId: this.collection().id,
      request: { type: 'caption', phrase },
    }));
    this.phrase.set('');
    this.adding.set(false);
  }

  protected addPersonTrigger(personId: number): void {
    this.store.dispatch(collectionsActions.addTrigger({
      collectionId: this.collection().id,
      request: { type: 'person', person_id: personId },
    }));
    this.personQuery.set('');
    this.adding.set(false);
  }

  protected onPhraseKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter') { this.addCaptionTrigger(); }
  }

  protected toggleNegate(trigger: Trigger): void {
    this.store.dispatch(collectionsActions.updateTrigger({
      collectionId: this.collection().id,
      triggerId: trigger.id,
      negate: !trigger.negate,
    }));
  }

  protected removeTrigger(trigger: Trigger): void {
    this.store.dispatch(collectionsActions.deleteTrigger({
      collectionId: this.collection().id,
      triggerId: trigger.id,
    }));
  }

  protected triggerLabel(trigger: Trigger): string {
    if (trigger.type === 'tag') { return (trigger.tag_name ?? '').replaceAll('_', ' '); }
    if (trigger.type === 'caption') { return `„${trigger.phrase}"`; }
    if (trigger.type === 'person') { return trigger.person_name ?? 'Unbekannte Person'; }
    return '';
  }

  protected triggerIcon(trigger: Trigger): string {
    if (trigger.type === 'tag') { return 'tag'; }
    if (trigger.type === 'caption') { return 'text'; }
    return 'face';
  }

  protected triggerKind(trigger: Trigger): string {
    if (trigger.type === 'tag') { return 'Tag'; }
    if (trigger.type === 'caption') { return 'Caption'; }
    return 'Person';
  }

  protected onClose(): void {
    this.close.emit();
  }

  // ── Beschreibung, Cover, Reihenfolge (P10 Phase 1 — manuelle Alben) ────────

  protected saveDescription(): void {
    const value = this.descriptionDraft().trim();
    if (value === (this.collection().description ?? '')) { return; }
    this.store.dispatch(collectionsActions.update({
      id: this.collection().id,
      request: { description: value.length > 0 ? value : null },
    }));
  }

  protected thumbnailUrl(asset: AssetDto): string {
    return this.assetService.thumbnailUrl(asset.id, 256, asset.content_hash);
  }

  protected isCover(asset: AssetDto): boolean {
    return this.collection().cover_asset_id === asset.id;
  }

  protected setCover(asset: AssetDto): void {
    const nextCoverId = this.isCover(asset) ? null : asset.id;
    this.store.dispatch(collectionsActions.update({
      id: this.collection().id,
      request: { cover_asset_id: nextCoverId },
    }));
  }

  protected moveMember(index: number, direction: -1 | 1): void {
    const list = [...this.members()];
    const current = list[index];
    const target = list[index + direction];
    if (current == null || target == null) { return; }
    list[index] = target;
    list[index + direction] = current;
    this.store.dispatch(collectionsActions.reorder({
      collectionId: this.collection().id,
      assetIds: list.map((asset: AssetDto) => asset.id),
    }));
  }
}
