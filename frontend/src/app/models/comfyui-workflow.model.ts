export interface WorkflowInput {
  key: string;
  label: string;
  node_title: string;
  node_id: string;
  field: string;
  kind: 'image' | 'mask';
  required: boolean;
  lockable: boolean;
}

export interface WorkflowParam {
  key: string;
  label: string;
  node_title: string;
  node_id: string;
  field: string;
  type: 'float' | 'int' | 'string' | 'enum';
  default: unknown;
  min: number | null;
  max: number | null;
  step: number | null;
  options: string[] | null;
}

export interface ComfyUIWorkflow {
  id: number;
  name: string;
  category: string;
  templatePath: string;
  inputs: WorkflowInput[];
  params: WorkflowParam[];
  isActive: boolean;
  isValid: boolean;
  validationErrors: ValidationError[] | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface ValidationError {
  code: string;
  message: string;
  expected: string;
  found: string;
  next_step: string;
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
