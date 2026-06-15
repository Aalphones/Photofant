import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { AssetDetailDto, AssetsPage, SortKey, SortOrder } from '@photofant/models';

export interface ListAssetsParams {
  page: number;
  page_size: number;
  sort: SortKey;
  order: SortOrder;
  favourite?: boolean | null;
}

@Injectable({ providedIn: 'root' })
export class AssetService {
  private readonly http = inject(HttpClient);

  listAssets(params: ListAssetsParams): Observable<AssetsPage> {
    let httpParams = new HttpParams()
      .set('page', params.page)
      .set('page_size', params.page_size)
      .set('sort', params.sort)
      .set('order', params.order);
    if (params.favourite != null) {
      httpParams = httpParams.set('favourite', String(params.favourite));
    }
    return this.http.get<AssetsPage>('/api/assets', { params: httpParams });
  }

  getAsset(id: number): Observable<AssetDetailDto> {
    return this.http.get<AssetDetailDto>(`/api/assets/${id}`);
  }

  thumbnailUrl(id: number, size: 256 | 512 = 256): string {
    return `/api/assets/${id}/thumbnail?size=${size}`;
  }

  fileUrl(id: number): string {
    return `/api/assets/${id}/file`;
  }
}
