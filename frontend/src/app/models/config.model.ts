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
