import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { TagListItem } from '@photofant/models';

export interface MergeTagsRequest {
  from_ids: number[];
  into_id: number;
}

export interface BulkTagRequest {
  asset_ids: number[];
  add: string[];
  remove: number[];
}

@Injectable({ providedIn: 'root' })
export class TagService {
  private readonly http = inject(HttpClient);

  listTags(query?: string, pageSize = 20): Observable<TagListItem[]> {
    let params = new HttpParams().set('page_size', pageSize);
    if (query) {
      params = params.set('query', query);
    }
    return this.http.get<TagListItem[]>('/api/tags', { params });
  }

  renameTag(id: number, name: string): Observable<TagListItem> {
    return this.http.patch<TagListItem>(`/api/tags/${id}`, { name });
  }

  mergeTags(request: MergeTagsRequest): Observable<void> {
    return this.http.post<void>('/api/tags/merge', request);
  }

  bulkTag(request: BulkTagRequest): Observable<void> {
    return this.http.post<void>('/api/tags/bulk', request);
  }
}
