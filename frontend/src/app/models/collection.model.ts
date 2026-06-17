export const COLLECTION_KINDS = ['album', 'smart_album', 'training_set'] as const;
export type CollectionKind = (typeof COLLECTION_KINDS)[number];

export const MATCH_MODES = ['any', 'all'] as const;
export type MatchMode = (typeof MATCH_MODES)[number];

export const TRIGGER_TYPES = ['person', 'tag', 'caption'] as const;
export type TriggerType = (typeof TRIGGER_TYPES)[number];

export interface Trigger {
  id: number;
  type: TriggerType;
  person_id: number | null;
  tag_id: number | null;
  tag_name: string | null;
  phrase: string | null;
  negate: boolean;
}

export interface Collection {
  id: number;
  name: string;
  kind: CollectionKind;
  match_mode: MatchMode;
  member_count: number;
  cover_asset_ids: number[];
}

export interface CollectionDetail extends Collection {
  triggers: Trigger[];
}

export interface CreateCollectionRequest {
  name: string;
  kind?: CollectionKind;
  match_mode?: MatchMode;
}

export interface UpdateCollectionRequest {
  name?: string;
  kind?: CollectionKind;
  match_mode?: MatchMode;
}

export interface CreateTriggerRequest {
  type: TriggerType;
  person_id?: number | null;
  tag_id?: number | null;
  phrase?: string | null;
  negate?: boolean;
}
