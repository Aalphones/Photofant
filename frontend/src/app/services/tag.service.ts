import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { TagListItem } from '@photofant/models';

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
}
