import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { SemanticSearchResponse } from '@photofant/models';

/**
 * Zugriff auf die Embedding-Suche (`/api/search/*`, P36). Reverse Image Search
 * bettet ein hochgeladenes Bild ein und liefert die ähnlichsten Bibliotheks-Bilder;
 * das Upload-Bild wird serverseitig nur eingebettet, nie importiert oder gespeichert.
 */
@Injectable({ providedIn: 'root' })
export class SearchService {
  private readonly http = inject(HttpClient);

  searchByImage(file: File, limit?: number): Observable<SemanticSearchResponse> {
    const form = new FormData();
    form.append('file', file, file.name);
    let params = new HttpParams();
    if (limit != null) {
      params = params.set('limit', String(limit));
    }
    return this.http.post<SemanticSearchResponse>('/api/search/by-image', form, { params });
  }

  // „Ähnlich zu Asset X" — Lightbox-Rail und der „mehr"-Sprung in die Reverse-Search.
  semanticByAsset(likeAssetId: number, limit?: number): Observable<SemanticSearchResponse> {
    const body: { like_asset_id: number; limit?: number } = { like_asset_id: likeAssetId };
    if (limit != null) {
      body.limit = limit;
    }
    return this.http.post<SemanticSearchResponse>('/api/search/semantic', body);
  }
}
