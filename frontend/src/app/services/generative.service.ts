import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import type { Observable } from 'rxjs';

export interface GenerativeStatus {
  available: boolean;
  status: string;
  loaded_model: string | null;
}

export interface UpscaleRequest {
  model_id?: string | null;
  params?: Record<string, unknown>;
}

export interface UpscaleStarted {
  job_id: string;
}

export interface BulkUpscaleRequest {
  asset_ids: number[];
  model_id?: string | null;
  params?: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class GenerativeService {
  private readonly http = inject(HttpClient);

  getStatus(): Observable<GenerativeStatus> {
    return this.http.get<GenerativeStatus>('/api/generative/status');
  }

  upscaleAsset(assetId: number, request: UpscaleRequest = {}): Observable<UpscaleStarted> {
    return this.http.post<UpscaleStarted>(`/api/assets/${assetId}/upscale`, request);
  }

  bulkUpscale(request: BulkUpscaleRequest): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/assets/bulk-upscale', request);
  }

  installGenerative(): Observable<{ job_id: string; already_installed: boolean; message: string }> {
    return this.http.post<{ job_id: string; already_installed: boolean; message: string }>(
      '/api/generative/install',
      {},
    );
  }

  unloadGenerative(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>('/api/generative/unload', {});
  }
}
