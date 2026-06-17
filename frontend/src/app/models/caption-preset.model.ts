export type CapabilityFieldType = 'dropdown' | 'number' | 'slider' | 'textarea' | 'checkbox';

export interface CapabilityFieldOption {
  value: string;
  label: string;
}

export interface CapabilityField {
  key: string;
  type: CapabilityFieldType;
  label: string;
  desc: string;
  default: string | number | boolean;
  options?: CapabilityFieldOption[];
  min?: number;
  max?: number;
}

export interface CapabilityDescriptor {
  info?: string;
  fields: CapabilityField[];
}

export interface CaptionPresetDto {
  id: number;
  name: string;
  model_id: number | null;
  config: Record<string, unknown>;
  is_default: boolean;
}

export interface CaptionPresetCreate {
  name: string;
  model_id?: number | null;
  config: Record<string, unknown>;
  is_default?: boolean;
}

export interface CaptionPresetUpdate {
  name?: string;
  config?: Record<string, unknown>;
  is_default?: boolean;
}
