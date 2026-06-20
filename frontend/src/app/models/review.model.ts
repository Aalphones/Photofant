export interface AssetSummary {
  id: number;
  width: number | null;
  height: number | null;
  format: string | null;
  source: string | null;
  file_size: number | null;
  created_at: string | null;
  imported_at: string | null;
}

export interface DupePair {
  id: number;
  asset_a: AssetSummary;
  asset_b: AssetSummary;
  phash_distance: number;
  created_at: string;
}

export const DUPE_RESOLUTIONS = [
  'a_is_original',
  'b_is_original',
  'delete_a',
  'delete_b',
  'dismiss',
] as const;

export type DupeResolution = (typeof DUPE_RESOLUTIONS)[number];

export interface FaceReviewItem {
  id: number;
  face_id: number;
  suggested_person_id: number | null;
  suggested_person_name: string | null;
  score: number;
  asset_id: number;
  crop_url: string;
}

export const FACE_REVIEW_ACTIONS = ['confirm', 'reject', 'reassign'] as const;

export type FaceReviewAction = (typeof FACE_REVIEW_ACTIONS)[number];

export interface MergeResult {
  faces_moved: number;
  instances_moved: number;
}

export interface SplitResult {
  new_person_id: number | null;
  faces_moved: number;
  instances_created: number;
}
