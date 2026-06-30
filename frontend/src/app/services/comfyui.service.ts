import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import type { Observable } from 'rxjs';
import type { ComfyUIConfig, ComfyUIImportResponse, ComfyUIResultsResponse, ComfyUIWorkflow, DefaultRunRequest, DefaultRunTask, ResolutionRun } from '@photofant/models';
import { COMFYUI_CONFIG_DEFAULTS } from '@photofant/models';

/** Optionale Run-Parameter, die der Workflow erkannt hat (Prompt/Auflösung/Maske). */
export interface RunExtras {
  prompt?: string | null;
  negativePrompt?: string | null;
  resolution?: ResolutionRun | null;
  mask?: { asset_id: number; mask_data_url: string } | null;
}

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
    node_id: string;
    field: string;
    kind: string;
  }>;
  prompt: { node_id: string; field: string } | null;
  negative_prompt: { node_id: string; field: string } | null;
  resolution: {
    node_id: string;
    megapixels_field: string;
    aspect_field: string;
    aspect_default: string;
  } | null;
  mask: { mode: string; image_node_id: string } | null;
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
      node_id: inp.node_id,
      field: inp.field,
      kind: inp.kind as 'image' | 'mask',
    })),
    prompt: raw.prompt ? { node_id: raw.prompt.node_id, field: raw.prompt.field } : null,
    negativePrompt: raw.negative_prompt
      ? { node_id: raw.negative_prompt.node_id, field: raw.negative_prompt.field }
      : null,
    resolution: raw.resolution
      ? {
          node_id: raw.resolution.node_id,
          megapixelsField: raw.resolution.megapixels_field,
          aspectField: raw.resolution.aspect_field,
          aspectDefault: raw.resolution.aspect_default,
        }
      : null,
    mask: raw.mask
      ? { mode: raw.mask.mode as 'alpha' | 'loader', image_node_id: raw.mask.image_node_id }
      : null,
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
    extras: RunExtras = {},
    versionInputs: Record<string, number | number[]> = {},
  ): Observable<{ jobs: { job_id: string }[] }> {
    return this.http.post<{ jobs: { job_id: string }[] }>(
      `/api/comfyui/workflows/${workflowKey}/run`,
      {
        inputs,
        face_inputs: faceInputs,
        version_inputs: versionInputs,
        prompt: extras.prompt ?? null,
        negative_prompt: extras.negativePrompt ?? null,
        resolution: extras.resolution ?? null,
        mask: extras.mask ?? null,
      },
    );
  }

  /** Ruft den kuratierten Default-Endpunkt auf — importiert das Ergebnis automatisch als Version. */
  runDefaultWorkflow(
    task: DefaultRunTask,
    payload: DefaultRunRequest,
  ): Observable<{ jobs: { job_id: string }[] }> {
    return this.http.post<{ jobs: { job_id: string }[] }>(
      `/api/comfyui/defaults/${task}/run`,
      {
        target_asset_ids: payload.target_asset_ids,
        inputs: payload.inputs,
        face_inputs: payload.face_inputs ?? {},
        prompt: payload.prompt ?? null,
        negative_prompt: payload.negative_prompt ?? null,
        resolution: payload.resolution ?? null,
        mask: payload.mask ?? null,
      },
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
