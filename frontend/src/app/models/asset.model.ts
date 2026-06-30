export const SEARCH_MODES = ['tags', 'caption', 'semantic'] as const;
export type SearchMode = (typeof SEARCH_MODES)[number];

export const MEDIA_TYPES = ['all', 'photos', 'faces'] as const;
export type MediaType = (typeof MEDIA_TYPES)[number];

export interface TagListItem {
  id: number;
  name: string;
  count: number;
  alias_of: number | null;
  aliases: string[];  // names of tags that are aliases of this one
}

export const DENSITIES = ['sm', 'md', 'lg'] as const;
export type Density = (typeof DENSITIES)[number];

export const SORT_KEYS = ['date', 'size'] as const;
export type SortKey = (typeof SORT_KEYS)[number];

export const SORT_ORDERS = ['asc', 'desc'] as const;
export type SortOrder = (typeof SORT_ORDERS)[number];

export const GROUP_KEYS = ['month', 'person', 'source'] as const;
export type GroupKey = (typeof GROUP_KEYS)[number];

export const BASE_HEIGHTS: Record<Density, number> = { sm: 150, md: 196, lg: 250 };

export const DENSITY_THUMB_SIZE: Record<Density, 256 | 512 | 1024> = { sm: 256, md: 512, lg: 1024 };

export interface FacetItem {
  value: string;
  count: number;
}

export interface TagFacetItem {
  id: number;
  name: string;
  count: number;
}

export interface Facets {
  sources: FacetItem[];
  tags_top: TagFacetItem[];
  framings?: FacetItem[];
}

export interface VersionDto {
  id: number;
  type: string | null;
  parent_id: number | null;
  path: string;
  is_current: boolean;
  params: Record<string, unknown> | null;
  created_at: string | null;
  thumbnail_url: string;
  res: { width: number; height: number } | null;
}

export interface AssetDto {
  id: number;
  content_hash: string;
  width: number | null;
  height: number | null;
  file_size: number | null;
  format: string | null;
  source: string | null;
  created_at: string | null;
  imported_at: string | null;
  favourite: boolean;
  version_count: number;
  generation_meta: Record<string, unknown> | null;
  has_phash: boolean;
}

export interface SimilarAsset {
  id: number;
  content_hash: string;
  width: number | null;
  height: number | null;
  format: string | null;
  source: string | null;
  file_size: number | null;
  created_at: string | null;
  imported_at: string | null;
  phash_distance: number;
}

export interface TagDto {
  id: number;
  name: string;
  kind: string;
  score: number | null;
}

export interface FaceDto {
  id: number;
  asset_id: number | null;
  person_id: number | null;
  person_name: string | null;
  crop_url: string;
  score: number | null;
  age: number | null;
  bbox: Record<string, number> | null;
  origin: string | null;
  is_upscaled: boolean;
}

export interface AssetDetailDto extends AssetDto {
  path: string | null;
  tags: TagDto[];
  tagger: string | null;
  caption: string | null;
  captioner: string | null;
  caption_preset_id: number | null;
  faces: FaceDto[];
  versions?: VersionDto[];
}

export interface AssetsPage {
  items: AssetDto[];
  total: number;
  page: number;
  page_size: number;
  facets: Facets;
}

export interface AssetGroup {
  label: string;
  assets: AssetDto[];
}

export interface FaceGalleryItemDto {
  id: number;
  asset_id: number | null;
  person_id: number | null;
  person_name: string | null;
  thumbnail_url: string;
  score: number | null;
  age: number | null;
  is_upscaled: boolean;
  origin: string | null;
  created_at: string | null;
}

export interface FacesPage {
  items: FaceGalleryItemDto[];
  total: number;
  page: number;
  page_size: number;
}
