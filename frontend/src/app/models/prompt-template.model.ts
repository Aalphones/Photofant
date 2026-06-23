export interface PromptTemplateDto {
  id: number;
  name: string;
  prompt: string;
  params: PromptTemplateParams | null;
  created_at: string | null;
}

export interface PromptTemplateParams {
  strength?: number;
  steps?: number;
  guidance?: number;
  seed?: number;
}

export interface CreatePromptTemplateRequest {
  name: string;
  prompt: string;
  params?: PromptTemplateParams | null;
}

export interface UpdatePromptTemplateRequest {
  name?: string;
  prompt?: string;
  params?: PromptTemplateParams | null;
}
