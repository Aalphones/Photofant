import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ExportFilterParams {
  sources?: string[];
  quality_min?: number;
  tag_ids?: number[];
  person_id?: number;
  include_versions?: boolean;
}

export interface ExportRandomParams {
  count: number;
  images_per_set: number;
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

  exportFavouritesByPerson(): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>('/api/export/favourites/by-person', {});
  }

  exportFavouritesRandom(params: ExportRandomParams): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>('/api/export/favourites/random', params);
  }

  exportCollection(collectionId: number): Observable<ExportJobStarted> {
    return this.http.post<ExportJobStarted>(`/api/collections/${collectionId}/export`, {});
  }
}
