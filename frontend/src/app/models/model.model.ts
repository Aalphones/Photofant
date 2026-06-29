import type { CapabilityDescriptor } from './caption-preset.model';

export type ModelStatus = 'active' | 'available' | 'missing' | 'inplace';
export type ModelTier = 'core' | 'optional' | 'generativ';

export interface ModelDto {
  id: string;
  role: string;
  name: string;
  variant: string | null;
  format: string;
  path: string | null;
  components: Record<string, string> | null;
  sha256: string | null;
  managed: boolean;
  enabled: boolean;
  is_default: boolean;
  status: ModelStatus;
  size_bytes: number | null;
  license_note: string | null;
  caption_mode: string | null;
  capabilities: CapabilityDescriptor | null;
}

export interface ModelView extends ModelDto {
  tier: ModelTier;
  desc: string;
  licenseNc: boolean;
}

export interface CapabilitiesDto {
  faces: boolean;
  tagging: boolean;
  captioning: boolean;
  semantic_search: boolean;
  rembg: boolean;
  heavy_caption: boolean;
}

export interface GpuInfoDto {
  name: string | null;
  vram_gb: number | null;
  vram_bytes: number | null;
}

export interface VramRecommendation {
  model_id: string;
  recommended_variant: string | null;
}

export interface VramResponse {
  gpu: GpuInfoDto;
  recommendations: VramRecommendation[];
}

export interface ComponentSpec {
  label: string;
  required: boolean;
  formats?: string[];
}

export interface VariantSpec {
  name: string;
  size_gb: number | null;
  vram_gb: number | null;
}

export interface RegisterLocalResponse {
  model: ModelDto;
  warnings: string[];
}

export interface ModelBindError {
  manifestId: string;
  code: string;
  message: string;
}

export const MODEL_ENRICHMENT: Record<string, { tier: ModelTier; desc: string; licenseNc: boolean }> = {
  'buffalo_l': {
    tier: 'core',
    desc: 'Face-Detection + Embedding-Extraktion. Wird für jedes Gesicht in der Sammlung benötigt.',
    licenseNc: false,
  },
  'wd-swinv2-v3': {
    tier: 'core',
    desc: 'Booru-Tag-Klassifikator. Schnell, speicherschonend, sehr gute Abdeckung.',
    licenseNc: false,
  },
  'florence-2-base': {
    tier: 'core',
    desc: 'Schneller, MIT-lizenzierter Captioner. Deterministische Beam-Search, kein freier Prompt.',
    licenseNc: false,
  },
  'clip-vit-l-14': {
    tier: 'core',
    desc: 'Semantische Bild-Einbettungen für die thematische Suche.',
    licenseNc: false,
  },
  'rembg-u2net': {
    tier: 'core',
    desc: 'Hintergrundentfernung. Benötigt für Freisteller und saubere Gesichtsextraktion.',
    licenseNc: false,
  },
  'flux2-klein-9b': {
    tier: 'generativ',
    desc: 'Generatives Editing & Inpainting. Komponenten-Modell: Transformer, Text-Encoder und VAE einzeln wählbar.',
    licenseNc: true,
  },
  'seedvr2-3b': {
    tier: 'generativ',
    desc: 'Upscaler (3B). Schnell, moderater VRAM-Bedarf. Ideal für fp8/GGUF auf Consumer-GPUs.',
    licenseNc: false,
  },
  'seedvr2-7b': {
    tier: 'generativ',
    desc: 'Upscaler (7B). Bessere Qualität, höherer VRAM-Bedarf. fp8-Variante empfohlen.',
    licenseNc: false,
  },
};

export const ROLE_META: Record<string, { icon: string; label: string }> = {
  face:             { icon: 'face',    label: 'Face-Analyse' },
  tagger:           { icon: 'tag',     label: 'Tagger' },
  captioner:        { icon: 'text',    label: 'Captioner' },
  semantic_search:  { icon: 'search',  label: 'Semantische Suche' },
  rembg:            { icon: 'layers',  label: 'Hintergrund' },
  upscaler:         { icon: 'refresh', label: 'Upscale' },
  editor:           { icon: 'pencil',  label: 'Generatives Editing' },
  heavy_captioner:  { icon: 'text',    label: 'Schwerer Captioner' },
};

export const STATUS_META: Record<ModelStatus, { label: string; dot: boolean }> = {
  active:    { label: 'Aktiv',              dot: true },
  available: { label: 'Nicht installiert',  dot: true },
  missing:   { label: 'Nicht konfiguriert', dot: true },
  inplace:   { label: 'In-Place',           dot: true },
};

export const TIER_META: Record<ModelTier, { label: string; desc: string }> = {
  core:      { label: 'Core',             desc: 'Immer aktiv · ONNX Runtime · läuft auch auf CPU' },
  optional:  { label: 'Optional / Heavy', desc: 'Torch · nur bei Bedarf laden · empfohlen für bessere Qualität' },
  generativ: { label: 'Generativ',        desc: 'Flux2, SeedVR2 · GPU + zweistellige GB VRAM + Disk' },
};

export const MODEL_TIERS: ModelTier[] = ['core', 'optional', 'generativ'];

export const ERROR_CODE_MESSAGES: Record<string, string> = {
  MODEL_NOT_FOUND:    'Modell nicht im Manifest gefunden — ID prüfen.',
  MODEL_WRONG_FORMAT: 'Falsches Format — Dateiendung oder Struktur passt nicht zur Rolle.',
  MODEL_WRONG_ROLE:   'Diese Datei passt zur falschen Rolle. Slot oder Datei korrigieren.',
  MODEL_INCOMPLETE:   'Modell unvollständig — alle Pflicht-Komponenten müssen gesetzt sein.',
  MODEL_LOAD_FAILED:  'Datei ließ sich nicht laden (beschädigt oder inkompatibles Format).',
  MODEL_HASH_MISMATCH:'Prüfsumme weicht vom Manifest ab — Download evtl. unvollständig.',
  MODEL_COMPONENT_MISMATCH: 'Komponente passt nicht zur erwarteten Familie — Output kann fehlerhaft sein.',
  MODEL_VRAM_EXCEEDED: 'Variante übersteigt den erkannten VRAM — eine kleinere Variante empfohlen.',
  LICENSE_ACK_REQUIRED: 'Bitte die Lizenzbedingungen bestätigen, bevor der Download gestartet werden kann.',
};

export function formatModelSize(bytes: number | null): string {
  if (bytes === null) {
    return '–';
  }
  if (bytes >= 1_073_741_824) {
    return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  }
  return `${Math.round(bytes / 1_048_576)} MB`;
}
