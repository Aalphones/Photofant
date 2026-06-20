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
