export const SEARCH_MODES = ['tags', 'caption', 'semantic'] as const;
export type SearchMode = (typeof SEARCH_MODES)[number];

export interface TagListItem {
  id: number;
  name: string;
  count: number;
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
}

export interface TagDto {
  id: number;
  name: string;
  kind: string;
  score: number | null;
}

export interface AssetDetailDto extends AssetDto {
  path: string | null;
  tags: TagDto[];
  tagger: string | null;
  caption: string | null;
  captioner: string | null;
  caption_preset_id: number | null;
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
