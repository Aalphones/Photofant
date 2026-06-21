import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import type { Observable } from 'rxjs';
import type { ComfyUIConfig } from '@photofant/models';
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

function fromApi(raw: ComfyUIConfigApi): ComfyUIConfig {
  return {
    enabled: Boolean(raw.enabled ?? COMFYUI_CONFIG_DEFAULTS.enabled),
    baseUrl: String(raw.base_url ?? COMFYUI_CONFIG_DEFAULTS.baseUrl),
    clientId: String(raw.client_id ?? COMFYUI_CONFIG_DEFAULTS.clientId),
    outputDir: String(raw.output_dir ?? COMFYUI_CONFIG_DEFAULTS.outputDir),
    timeout: Number(raw.timeout ?? COMFYUI_CONFIG_DEFAULTS.timeout),
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
}
