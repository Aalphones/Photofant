export type EditorTargetKind = 'instance' | 'face' | 'version';

export type CropRatio = 'free' | '1:1' | '4:3' | '3:4' | '16:9' | '3:2' | '2:3';

export interface CropRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface EditorStep {
  seq: number;
  op: string;
  params: Record<string, unknown>;
  label: string;
  previewUrl: string;
}

export interface CreateSessionResponse {
  session_key: string;
  original_preview_url: string;
}

export interface ApplyStepResponse {
  seq: number;
  preview_url: string;
}

export interface RollbackResponse {
  seq: number;
}
