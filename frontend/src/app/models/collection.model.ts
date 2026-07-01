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
  person_name: string | null;
  tag_id: number | null;
  tag_name: string | null;
  phrase: string | null;
  negate: boolean;
}

export interface CoverAsset {
  id: number;
  content_hash: string;
}

export interface TrainingSetSettings {
  trigger_word: string | null;
  prefix: string | null;
  suffix: string | null;
  split_ratio: number | null; // Anteil Training (0.0-1.0), Rest = Val
}

export interface Collection {
  id: number;
  name: string;
  kind: CollectionKind;
  match_mode: MatchMode;
  member_count: number;
  cover_assets: CoverAsset[];
  description: string | null;
  cover_asset_id: number | null;
  settings: TrainingSetSettings | null;
}

export interface CollectionDetail extends Collection {
  triggers: Trigger[];
  item_order: number[];  // asset ids, manuelle Reihenfolge (P10 Phase 1)
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
  description?: string | null;
  cover_asset_id?: number | null;
  settings?: TrainingSetSettings | null;
}

export interface CreateTriggerRequest {
  type: TriggerType;
  person_id?: number | null;
  tag_id?: number | null;
  phrase?: string | null;
  negate?: boolean;
}

export interface TrainingSetItemTag {
  id: number;
  name: string;
  kind: string;
  score: number | null;
}

export interface TrainingSetItem {
  id: number;
  content_hash: string;
  width: number | null;
  height: number | null;
  framing: string | null;
  quality: number | null;
  caption: string | null;
  caption_override: string | null;
  effective_caption: string | null;
  tags: TrainingSetItemTag[];
}

export interface DistItem {
  value: string;
  count: number;
}

export interface TagFrequency {
  name: string;
  count: number;
}

export interface HistogramBucket {
  label: string;
  count: number;
}

export interface TrainingSetStats {
  total: number;
  framing: DistItem[];
  tag_frequencies: TagFrequency[];
  quality_histogram: HistogramBucket[];
  ar_buckets: DistItem[];
  near_dupe_rate: number;
}

export const CAPTION_ACTIONS = ['trigger_word', 'prefix', 'suffix', 'find_replace'] as const;
export type CaptionAction = (typeof CAPTION_ACTIONS)[number];

export interface CaptionActionRequest {
  action: CaptionAction;
  params: Record<string, string>;
}

export const DUPE_REVIEW_RESOLUTIONS = ['keep_left', 'keep_right', 'keep_both'] as const;
export type DupeReviewResolution = (typeof DUPE_REVIEW_RESOLUTIONS)[number];

export interface CollectionDupePair {
  asset_a_id: number;
  asset_b_id: number;
  asset_a_content_hash: string;
  asset_b_content_hash: string;
  phash_distance: number;
  similarity_pct: number;
}
