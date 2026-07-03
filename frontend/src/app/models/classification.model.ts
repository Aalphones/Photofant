export const CLASSIFICATION_MODES = ['single', 'multi'] as const;
export type ClassificationMode = typeof CLASSIFICATION_MODES[number];

export interface ClassificationLabel {
  id: number;
  category_id: number;
  name: string;
  position: number;
  clip_prompts: string[] | null;
  wd14_tags: string[] | null;
}

export interface ClassificationCategory {
  id: number;
  name: string;
  mode: ClassificationMode;
  position: number;
  enabled: boolean;
  builtin: boolean;
  min_confidence: number | null;
  labels: ClassificationLabel[];
}

export interface AssetClassification {
  category_id: number;
  category_name: string;
  label_id: number;
  label_name: string;
  confidence: number;
}

export interface CategoryCreateRequest {
  name: string;
  mode: ClassificationMode;
  position?: number;
}

export interface CategoryPatchRequest {
  name?: string;
  mode?: ClassificationMode;
  position?: number;
  enabled?: boolean;
  min_confidence?: number | null;
}

export interface LabelCreateRequest {
  name: string;
  clip_prompts?: string[] | null;
  wd14_tags?: string[] | null;
}

export interface LabelPatchRequest {
  name?: string;
  clip_prompts?: string[] | null;
  wd14_tags?: string[] | null;
  position?: number;
}
