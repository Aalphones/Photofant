import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import type { Observable } from 'rxjs';
import type { ComfyUIConfig, ComfyUIImportResponse, ComfyUIResultsResponse, ComfyUIWorkflow, WorkflowParam } from '@photofant/models';
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
  default_upscale: string;
  default_edit: string;
  default_inpaint: string;
}

interface WorkflowApi {
  key: string;
  name: string;
  category: string;
  inputs: Array<{
    key: string;
    label: string;
    node_title?: string;
    node_id: string;
    field: string;
    kind: string;
    required?: boolean;
    lockable?: boolean;
  }>;
  params?: WorkflowParam[];
  is_valid: boolean;
  errors: string[];
}

function fromApi(raw: ComfyUIConfigApi): ComfyUIConfig {
  return {
    enabled: Boolean(raw.enabled ?? COMFYUI_CONFIG_DEFAULTS.enabled),
    baseUrl: String(raw.base_url ?? COMFYUI_CONFIG_DEFAULTS.baseUrl),
    clientId: String(raw.client_id ?? COMFYUI_CONFIG_DEFAULTS.clientId),
    outputDir: String(raw.output_dir ?? COMFYUI_CONFIG_DEFAULTS.outputDir),
    timeout: Number(raw.timeout ?? COMFYUI_CONFIG_DEFAULTS.timeout),
    defaultUpscale: String(raw.default_upscale ?? ''),
    defaultEdit: String(raw.default_edit ?? ''),
    defaultInpaint: String(raw.default_inpaint ?? ''),
  };
}

function workflowFromApi(raw: WorkflowApi): ComfyUIWorkflow {
  return {
    key: raw.key,
    name: raw.name,
    category: raw.category,
    inputs: (raw.inputs ?? []).map((inp) => ({
      key: inp.key,
      label: inp.label,
      node_title: inp.node_title ?? '',
      node_id: inp.node_id,
      field: inp.field,
      kind: inp.kind as 'image' | 'mask',
      required: inp.required ?? false,
      lockable: inp.lockable ?? false,
    })),
    params: raw.params ?? [],
    isValid: raw.is_valid,
    errors: raw.errors ?? [],
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
      default_upscale: config.defaultUpscale,
      default_edit: config.defaultEdit,
      default_inpaint: config.defaultInpaint,
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

  runWorkflow(
    workflowKey: string,
    inputs: Record<string, number | number[]>,
    faceInputs: Record<string, number | number[]> = {},
    params: Record<string, unknown> = {},
  ): Observable<{ jobs: { job_id: string }[] }> {
    return this.http.post<{ jobs: { job_id: string }[] }>(
      `/api/comfyui/workflows/${workflowKey}/run`,
      { inputs, face_inputs: faceInputs, params },
    );
  }

  listResults(promptId?: string): Observable<ComfyUIResultsResponse> {
    const params = promptId ? { prompt_id: promptId } : {};
    return this.http.get<ComfyUIResultsResponse>('/api/comfyui/results', { params });
  }

  getResultViewUrl(filename: string, subfolder: string): string {
    const encoded = encodeURIComponent(filename);
    const sub = encodeURIComponent(subfolder);
    return `/api/comfyui/results/view?filename=${encoded}&subfolder=${sub}`;
  }

  importResult(assetId: number, filename: string, subfolder: string): Observable<ComfyUIImportResponse> {
    return this.http.post<ComfyUIImportResponse>('/api/comfyui/results/import', {
      asset_id: assetId,
      filename,
      subfolder,
    });
  }
}
