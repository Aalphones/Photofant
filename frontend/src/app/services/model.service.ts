import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type { ModelDto, CapabilitiesDto } from '@photofant/models';

interface ConfigResponse {
  data: Record<string, string | null>;
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

  updateModelsDir(path: string): Observable<ConfigResponse> {
    return this.http.patch<ConfigResponse>('/api/config', { data: { models_dir: path } });
  }

  downloadModel(manifestId: string, licenseAck: boolean): Observable<DownloadResponse> {
    return this.http.post<DownloadResponse>(
      `/api/models/${manifestId}/download`,
      { license_ack: licenseAck },
    );
  }

  registerLocal(manifestId: string, path: string): Observable<ModelDto> {
    return this.http.post<ModelDto>('/api/models/register-local', {
      manifest_id: manifestId,
      path,
    });
  }

  deleteModel(manifestId: string): Observable<DeleteResponse> {
    return this.http.delete<DeleteResponse>(`/api/models/${manifestId}`);
  }

  scanModels(): Observable<unknown> {
    return this.http.post('/api/models/scan', {});
  }
}
