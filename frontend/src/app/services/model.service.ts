import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type { ModelDto, CapabilitiesDto, VramResponse, RegisterLocalResponse } from '@photofant/models';

interface ConfigResponse {
  data: Record<string, unknown>;
  reboot_required?: boolean | null;
}

interface DownloadResponse {
  job_id: string;
}

interface DeleteResponse {
  deleted: boolean;
  file_removed: boolean;
}

@Injectable({ providedIn: 'root' })
export class ModelService {
  private readonly http = inject(HttpClient);

  loadModels(): Observable<ModelDto[]> {
    return this.http.get<ModelDto[]>('/api/models');
  }

  loadCapabilities(): Observable<CapabilitiesDto> {
    return this.http.get<CapabilitiesDto>('/api/models/capabilities');
  }

  loadConfig(): Observable<ConfigResponse> {
    return this.http.get<ConfigResponse>('/api/config');
  }

  patchConfig(patch: Record<string, unknown>): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: patch });
  }

  updateModelsDir(path: string): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: { models_dir: path } });
  }

  updateDataRoot(path: string): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: { data_root: path } });
  }

  downloadModel(manifestId: string, licenseAck: boolean): Observable<DownloadResponse> {
    return this.http.post<DownloadResponse>(
      `/api/models/${manifestId}/download`,
      { license_ack: licenseAck },
    );
  }

  registerLocal(manifestId: string, path: string): Observable<RegisterLocalResponse> {
    return this.http.post<RegisterLocalResponse>('/api/models/register-local', {
      manifest_id: manifestId,
      path,
    });
  }

  registerLocalComponents(manifestId: string, components: Record<string, string>): Observable<RegisterLocalResponse> {
    return this.http.post<RegisterLocalResponse>('/api/models/register-local', {
      manifest_id: manifestId,
      components,
    });
  }

  loadVram(): Observable<VramResponse> {
    return this.http.get<VramResponse>('/api/models/vram');
  }

  deleteModel(manifestId: string): Observable<DeleteResponse> {
    return this.http.delete<DeleteResponse>(`/api/models/${manifestId}`);
  }

  scanModels(): Observable<unknown> {
    return this.http.post('/api/models/scan', {});
  }
}
