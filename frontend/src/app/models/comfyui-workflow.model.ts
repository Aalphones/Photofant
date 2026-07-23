export interface WorkflowInput {
  key: string;
  label: string;
  node_id: string;
  field: string;
  kind: 'image' | 'mask';
}

/** Erkannter Prompt-/Negativ-Prompt-Node: nur vorhanden, wenn der Workflow ihn exponiert. */
export interface WorkflowPromptField {
  node_id: string;
  field: string;
}

/** Erkannter ResolutionSelector. `aspectDefault` ist die einzige sichere Aspect-Option. */
export interface WorkflowResolution {
  node_id: string;
  megapixelsField: string;
  aspectField: string;
  aspectDefault: string;
}

/** Erkannter Masken-Pfad. `alpha` = gemalte Maske wird ins Upload-PNG eingebettet. */
export interface WorkflowMask {
  mode: 'alpha' | 'loader';
  image_node_id: string;
}

/** Erkannter Switch-Node (z.B. ComfySwitchNode) — Boolean-Widget, Label kommt vom Node-Titel. */
export interface WorkflowToggle {
  key: string;
  label: string;
  node_id: string;
  field: string;
  default: boolean;
}

export interface ComfyUIWorkflow {
  key: string;
  name: string;
  category: string;
  inputs: WorkflowInput[];
  prompt: WorkflowPromptField | null;
  negativePrompt: WorkflowPromptField | null;
  resolution: WorkflowResolution | null;
  mask: WorkflowMask | null;
  toggles: WorkflowToggle[];
  isValid: boolean;
  errors: string[];
}

/** Run-Request-Auflösung: was der Nutzer wählt, nicht die Node-Felder. */
export interface ResolutionRun {
  megapixels: number;
  aspect_ratio: string;
}

export interface NodeInfo {
  node_id: string;
  class_type: string;
  title: string;
  inputs: Record<string, unknown>;
}

export interface InputSuggestion {
  key: string;
  label: string;
  node_title: string;
  node_id: string;
  field: string;
  kind: string;
  required: boolean;
  lockable: boolean;
}

export interface IntrospectionResult {
  nodes: NodeInfo[];
  input_suggestions: InputSuggestion[];
  has_save_image: boolean;
  is_api_format: boolean;
  errors: string[];
}

export const WORKFLOW_CATEGORIES = ['upscale', 'img2img', 'inpaint', 'generic'] as const;
export type WorkflowCategory = (typeof WORKFLOW_CATEGORIES)[number];

export interface ComfyUIResultItem {
  filename: string;
  subfolder: string;
  source: 'history' | 'output_dir';
  preview_url: string;
}

export interface ComfyUIResultsResponse {
  items: ComfyUIResultItem[];
}

export interface ComfyUIImportResponse {
  version_id: number;
  type: string;
  path: string;
  is_current: boolean;
  params: Record<string, unknown> | null;
  thumbnail_url: string;
}

/** Task-Typ für den kuratieren Default-Run-Endpunkt. */
export type DefaultRunTask = 'upscale' | 'edit' | 'inpaint';

/** Request-Body für POST /api/comfyui/defaults/{task}/run */
export interface DefaultRunRequest {
  target_asset_ids?: number[];
  target_face_ids?: number[];
  inputs: Record<string, number | number[]>;
  face_inputs?: Record<string, number | number[]>;
  prompt?: string | null;
  negative_prompt?: string | null;
  resolution?: ResolutionRun | null;
  mask?: { asset_id: number; mask_data_url: string } | null;
  toggles?: Record<string, boolean>;
}
