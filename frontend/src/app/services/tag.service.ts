import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, expand, Observable, reduce } from 'rxjs';
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

  listTags(query?: string, pageSize = 20, page = 1): Observable<TagListItem[]> {
    let params = new HttpParams()
      .set('page_size', pageSize)
      .set('page', page);
    if (query) {
      params = params.set('query', query);
    }
    return this.http.get<TagListItem[]>('/api/tags', { params });
  }

  listAllTags(query?: string): Observable<TagListItem[]> {
    const pageSize = 2000;
    return this.listTags(query, pageSize).pipe(
      expand((items: TagListItem[], index: number) =>
        items.length === pageSize ? this.listTags(query, pageSize, index + 2) : EMPTY
      ),
      reduce((allItems: TagListItem[], items: TagListItem[]) => [...allItems, ...items], []),
    );
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

  setTagAliases(id: number, names: string[]): Observable<void> {
    return this.http.put<void>(`/api/tags/${id}/aliases`, { names });
  }
}
