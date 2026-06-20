import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { DupePair, DupeResolution } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class ReviewService {
  private readonly http = inject(HttpClient);

  listDupePairs(): Observable<DupePair[]> {
    return this.http.get<DupePair[]>('/api/review/dupes');
  }

  resolveDupePair(itemId: number, resolution: DupeResolution): Observable<DupePair> {
    return this.http.patch<DupePair>(`/api/review/dupes/${itemId}`, { resolution });
  }

  triggerDupeScan(scope: 'all' | 'selection', assetIds?: number[]): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/jobs/dupe-scan', {
      scope,
      asset_ids: assetIds ?? null,
    });
  }
}
