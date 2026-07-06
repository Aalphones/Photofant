export interface ComfyUIConfig {
  enabled: boolean;
  baseUrl: string;
  clientId: string;
  outputDir: string;
  timeout: number;
  defaultUpscale: string;
  defaultEdit: string;
  defaultInpaint: string;
}

export const COMFYUI_CONFIG_DEFAULTS: ComfyUIConfig = {
  enabled: false,
  baseUrl: 'http://127.0.0.1:8188',
  clientId: 'photofant',
  outputDir: '',
  timeout: 10,
  defaultUpscale: '',
  defaultEdit: '',
  defaultInpaint: '',
};

export interface McpConfig {
  enabled: boolean;
  returnImages: boolean;
  maxSearchResults: number;
  thumbnailSize: number;
  requireConfirm: boolean;
}

export const MCP_CONFIG_DEFAULTS: McpConfig = {
  enabled: false,
  returnImages: true,
  maxSearchResults: 50,
  thumbnailSize: 256,
  requireConfirm: true,
};

export interface ProcessingConfig {
  autoTag: boolean;
  autoCaption: boolean;
  autoEmbed: boolean;
  activeCaptioner: string;
  minProbability: number;
  maxTags: number;
  blurThreshold: number;
  dupeClipEnabled: boolean;
  dupeClipThreshold: number;
  faceDetConfThreshold: number;
  faceDetIouThreshold: number;
  faceCropPadding: number;
  faceAutoThreshold: number;
  faceReviewThreshold: number;
  faceMinClusterSize: number;
  taggingWorkers: number;
  captioningWorkers: number;
}

export const PROCESSING_CONFIG_DEFAULTS: ProcessingConfig = {
  autoTag: true,
  autoCaption: true,
  autoEmbed: true,
  activeCaptioner: 'florence-2-base',
  minProbability: 0.5,
  maxTags: 30,
  blurThreshold: 200.0,
  dupeClipEnabled: true,
  dupeClipThreshold: 0.03,
  faceDetConfThreshold: 0.5,
  faceDetIouThreshold: 0.45,
  faceCropPadding: 40,
  faceAutoThreshold: 0.6,
  faceReviewThreshold: 0.45,
  faceMinClusterSize: 3,
  taggingWorkers: 1,
  captioningWorkers: 1,
};

export interface ShortcutBinding {
  action: string;
  keys: string[];
}

export interface ShortcutConfig {
  version: number;
  shortcuts: ShortcutBinding[];
}

export const SHORTCUT_DEFAULTS: ShortcutConfig = {
  version: 1,
  shortcuts: [
    { action: 'lightbox.prev',   keys: ['ArrowLeft'] },
    { action: 'lightbox.next',   keys: ['ArrowRight'] },
    { action: 'lightbox.close',  keys: ['Escape'] },
    { action: 'asset.favourite', keys: ['f', 'F'] },
    { action: 'asset.delete',    keys: ['Delete'] },
  ],
};
