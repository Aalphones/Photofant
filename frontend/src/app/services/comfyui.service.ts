import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import type { Observable } from 'rxjs';
import type { ComfyUIConfig, ComfyUIWorkflow, IntrospectionResult, WorkflowInput, WorkflowParam } from '@photofant/models';
import { COMFYUI_CONFIG_DEFAULTS } from '@photofant/models';

export interface TestConnectionResponse {
  ok: boolean;
  detail: string;
}

interface ComfyUIConfigApi {
  enabled: boolean;
  base_url: string;
  client_id: string;
  output_dir: string;
  timeout: number;
}

interface WorkflowApi {
  id: number;
  name: string;
  category: string;
  template_path: string;
  inputs: WorkflowInput[];
  params: WorkflowParam[];
  is_active: boolean;
  is_valid: boolean;
  validation_errors: Array<{ code: string; message: string; expected: string; found: string; next_step: string }> | null;
  created_at: string | null;
  updated_at: string | null;
}

function fromApi(raw: ComfyUIConfigApi): ComfyUIConfig {
  return {
    enabled: Boolean(raw.enabled ?? COMFYUI_CONFIG_DEFAULTS.enabled),
    baseUrl: String(raw.base_url ?? COMFYUI_CONFIG_DEFAULTS.baseUrl),
    clientId: String(raw.client_id ?? COMFYUI_CONFIG_DEFAULTS.clientId),
    outputDir: String(raw.output_dir ?? COMFYUI_CONFIG_DEFAULTS.outputDir),
    timeout: Number(raw.timeout ?? COMFYUI_CONFIG_DEFAULTS.timeout),
  };
}

function workflowFromApi(raw: WorkflowApi): ComfyUIWorkflow {
  return {
    id: raw.id,
    name: raw.name,
    category: raw.category,
    templatePath: raw.template_path,
    inputs: raw.inputs ?? [],
    params: raw.params ?? [],
    isActive: raw.is_active,
    isValid: raw.is_valid,
    validationErrors: raw.validation_errors ?? null,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

@Injectable({ providedIn: 'root' })
export class ComfyUIService {
  private readonly http = inject(HttpClient);

  loadConfig(): Observable<ComfyUIConfig> {
    return this.http.get<ComfyUIConfigApi>('/api/settings/comfyui').pipe(
      map((raw: ComfyUIConfigApi) => fromApi(raw))
    );
  }

  saveConfig(config: ComfyUIConfig): Observable<ComfyUIConfig> {
    const body: ComfyUIConfigApi = {
      enabled: config.enabled,
      base_url: config.baseUrl,
      client_id: config.clientId,
      output_dir: config.outputDir,
      timeout: config.timeout,
    };
    return this.http.put<ComfyUIConfigApi>('/api/settings/comfyui', body).pipe(
      map((raw: ComfyUIConfigApi) => fromApi(raw))
    );
  }

  testConnection(): Observable<TestConnectionResponse> {
    return this.http.post<TestConnectionResponse>('/api/comfyui/test-connection', {});
  }

  listWorkflows(): Observable<ComfyUIWorkflow[]> {
    return this.http.get<WorkflowApi[]>('/api/comfyui/workflows').pipe(
      map((list: WorkflowApi[]) => list.map((raw: WorkflowApi) => workflowFromApi(raw)))
    );
  }

  createWorkflow(file: File, name: string, category: string): Observable<ComfyUIWorkflow> {
    const formData = new FormData();
    formData.append('template', file);
    formData.append('name', name);
    formData.append('category', category);
    return this.http.post<WorkflowApi>('/api/comfyui/workflows', formData).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }

  updateWorkflow(
    workflowId: number,
    patch: { name?: string; category?: string; inputs?: WorkflowInput[]; params?: WorkflowParam[] },
  ): Observable<ComfyUIWorkflow> {
    return this.http.patch<WorkflowApi>(`/api/comfyui/workflows/${workflowId}`, patch).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }

  deleteWorkflow(workflowId: number): Observable<void> {
    return this.http.delete<void>(`/api/comfyui/workflows/${workflowId}`);
  }

  activateWorkflow(workflowId: number): Observable<ComfyUIWorkflow> {
    return this.http.post<WorkflowApi>(`/api/comfyui/workflows/${workflowId}/activate`, {}).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }

  deactivateWorkflow(workflowId: number): Observable<ComfyUIWorkflow> {
    return this.http.post<WorkflowApi>(`/api/comfyui/workflows/${workflowId}/deactivate`, {}).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }

  duplicateWorkflow(workflowId: number): Observable<ComfyUIWorkflow> {
    return this.http.post<WorkflowApi>(`/api/comfyui/workflows/${workflowId}/duplicate`, {}).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }

  introspectTemplate(file: File): Observable<IntrospectionResult> {
    const formData = new FormData();
    formData.append('template', file);
    return this.http.post<IntrospectionResult>('/api/comfyui/workflows/introspect', formData);
  }

  revalidateWorkflow(workflowId: number): Observable<ComfyUIWorkflow> {
    return this.http.post<WorkflowApi>(`/api/comfyui/workflows/${workflowId}/revalidate`, {}).pipe(
      map((raw: WorkflowApi) => workflowFromApi(raw))
    );
  }
}
