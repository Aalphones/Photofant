import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { AssetDetailDto, AssetDto, AssetsPage, SearchMode, SortKey, SortOrder } from '@photofant/models';

export interface ListAssetsParams {
  page: number;
  page_size: number;
  sort: SortKey;
  order: SortOrder;
  favourite?: boolean | null;
  sources?: string[];
  qualityMin?: number;
  tagIds?: number[];
  collectionId?: number | null;
  q?: string;
  qMode?: SearchMode;
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
    if (params.sources?.length) {
      for (const source of params.sources) {
        httpParams = httpParams.append('source', source);
      }
    }
    if (params.qualityMin) {
      httpParams = httpParams.set('quality_min', String(params.qualityMin));
    }
    if (params.tagIds?.length) {
      for (const tagId of params.tagIds) {
        httpParams = httpParams.append('tags', String(tagId));
      }
    }
    if (params.collectionId != null) {
      httpParams = httpParams.set('collection_id', String(params.collectionId));
    }
    if (params.q) {
      httpParams = httpParams.set('q', params.q);
    }
    if (params.qMode) {
      httpParams = httpParams.set('q_mode', params.qMode);
    }
    return this.http.get<AssetsPage>('/api/assets', { params: httpParams });
  }

  getAsset(id: number): Observable<AssetDetailDto> {
    return this.http.get<AssetDetailDto>(`/api/assets/${id}`);
  }

  setFavourite(id: number, value: boolean): Observable<AssetDto> {
    return this.http.patch<AssetDto>(`/api/assets/${id}/favourite`, { value });
  }

  deleteAsset(id: number): Observable<void> {
    return this.http.delete<void>(`/api/assets/${id}`);
  }

  listTrash(): Observable<AssetDto[]> {
    return this.http.get<AssetDto[]>('/api/trash');
  }

  restoreAsset(id: number): Observable<AssetDto> {
    return this.http.post<AssetDto>(`/api/trash/${id}/restore`, {});
  }

  purgeAsset(id: number): Observable<void> {
    return this.http.delete<void>(`/api/trash/${id}`);
  }

  emptyTrash(): Observable<void> {
    return this.http.delete<void>('/api/trash');
  }

  patchTags(id: number, add: string[], remove: number[]): Observable<AssetDetailDto> {
    return this.http.patch<AssetDetailDto>(`/api/assets/${id}/tags`, { add, remove });
  }

  patchCaption(id: number, caption: string): Observable<AssetDetailDto> {
    return this.http.patch<AssetDetailDto>(`/api/assets/${id}/caption`, { caption });
  }

  importPaths(paths: string[]): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/assets/import', { paths });
  }

  uploadFiles(files: File[]): Observable<{ job_id: string }> {
    const form = new FormData();
    for (const file of files) {
      form.append('files', file, file.name);
    }
    return this.http.post<{ job_id: string }>('/api/assets/upload', form);
  }

  scan(): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/assets/scan', {});
  }

  thumbnailUrl(id: number, size: 256 | 512 | 1024 = 256): string {
    return `/api/assets/${id}/thumbnail?size=${size}`;
  }

  fileUrl(id: number): string {
    return `/api/assets/${id}/file`;
  }
}
