export interface ProcessingConfig {
  autoTag: boolean;
  autoCaption: boolean;
  autoEmbed: boolean;
  minProbability: number;
  maxTags: number;
  blurThreshold: number;
}

export const PROCESSING_CONFIG_DEFAULTS: ProcessingConfig = {
  autoTag: true,
  autoCaption: true,
  autoEmbed: true,
  minProbability: 0.5,
  maxTags: 30,
  blurThreshold: 200.0,
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
