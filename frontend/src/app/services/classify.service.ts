import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type ClassifyStep = 'tags' | 'caption' | 'embedding' | 'heuristics' | 'faces' | 'phash';

export interface RerunRequest {
  asset_ids: number[] | 'all';
  steps: ClassifyStep[];
  caption_preset_id?: number;
}

@Injectable({ providedIn: 'root' })
export class ClassifyService {
  private readonly http = inject(HttpClient);

  rerun(request: RerunRequest): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/classify/rerun', request);
  }
}
