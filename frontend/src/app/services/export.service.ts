import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ExportFilterParams {
  sources?: string[];
  quality_min?: number;
  tag_ids?: number[];
  person_id?: number;
  include_versions?: boolean;
  favourite?: boolean | null;
  target_dir?: string;
}

export interface ExportRandomParams {
  count: number;
  images_per_set: number;
  target_dir?: string;
}

export type SidecarMode = 'tags' | 'caption' | 'both';

export interface CollectionExportParams {
  sidecar?: SidecarMode | null;
  split_ratio?: number | null;
  target_dir?: string;
}

export interface ExportJobStarted {
  job_id: string;
}

@Injectable({ providedIn: 'root' })
export class ExportService {
  private readonly http = inject(HttpClient);

  revealExportFolder(): Observable<void> {
    return this.http.get<void>('/api/export/reveal');
  }

  exportFavouritesFilter(params: ExportFilterParams): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>('/api/export/favourites/filter', params);
  }

  exportFavouritesByPerson(targetDir?: string): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>('/api/export/favourites/by-person', {
      target_dir: targetDir || undefined,
    });
  }

  exportFavouritesRandom(params: ExportRandomParams): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>('/api/export/favourites/random', params);
  }

  exportCollection(collectionId: number, params: CollectionExportParams = {}): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>(`/api/collections/${collectionId}/export`, params);
  }
}
