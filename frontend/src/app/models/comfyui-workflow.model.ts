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

export interface ComfyUIWorkflow {
  key: string;
  name: string;
  category: string;
  inputs: WorkflowInput[];
  prompt: WorkflowPromptField | null;
  negativePrompt: WorkflowPromptField | null;
  resolution: WorkflowResolution | null;
  mask: WorkflowMask | null;
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
