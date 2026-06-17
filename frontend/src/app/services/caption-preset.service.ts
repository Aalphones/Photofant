import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { CaptionPresetDto, CaptionPresetCreate, CaptionPresetUpdate } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class CaptionPresetService {
  private readonly http = inject(HttpClient);

  list(modelId?: number): Observable<CaptionPresetDto[]> {
    const params = modelId != null ? { model_id: String(modelId) } : {};
    return this.http.get<CaptionPresetDto[]>('/api/caption-presets', { params });
  }

  create(body: CaptionPresetCreate): Observable<CaptionPresetDto> {
    return this.http.post<CaptionPresetDto>('/api/caption-presets', body);
  }

  update(id: number, body: CaptionPresetUpdate): Observable<CaptionPresetDto> {
    return this.http.patch<CaptionPresetDto>(`/api/caption-presets/${id}`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/caption-presets/${id}`);
  }
}
