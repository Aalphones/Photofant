import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Store } from '@ngrx/store';
import type { CollectionDetail, MatchMode, TagListItem, Trigger, TriggerType } from '@photofant/models';
import { collectionsActions, tagsActions, tagsSelectors } from '@photofant/store';
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

  readonly collection = input.required<CollectionDetail>();
  readonly memberCount = input<number>(0);

  readonly close = output<void>();

  private readonly allTags = this.store.selectSignal(tagsSelectors.selectAll);

  protected readonly addTab = signal<AddTab>('tag');
  protected readonly adding = signal(false);
  protected readonly tagQuery = signal('');
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

  constructor() {
    this.store.dispatch(tagsActions.load());
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
    return 'Person';
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
}
