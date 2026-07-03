export type EditorTargetKind = 'instance' | 'face' | 'version';

export type SaveMode = 'overwrite' | 'new_copy';

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

// Antwort auf /save für reine Orientierungs-Sessions (rotate/mirror) — das Backend
// überschreibt die Quelle statt eine Version anzulegen, also existiert kein VersionDto.
export interface OrientationOverwriteResponse {
  kind: 'face' | 'instance';
  target_id: number;
  width: number;
  height: number;
  thumbnail_url: string;
}
