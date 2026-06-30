import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type { VersionsPage } from '@photofant/models';

export interface ListVersionsParams {
  page: number;
  page_size: number;
}

@Injectable({ providedIn: 'root' })
export class VersionService {
  private readonly http = inject(HttpClient);

  listVersions(params: ListVersionsParams): Observable<VersionsPage> {
    const httpParams = new HttpParams()
      .set('page', params.page)
      .set('page_size', params.page_size);
    return this.http.get<VersionsPage>('/api/versions', { params: httpParams });
  }
}
