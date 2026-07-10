import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type { RecommendationsResponse, WhyNotResponse } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class RecommendationService {
  private readonly http = inject(HttpClient);

  // Liest aus dem Cache; ist der Cache leer, plant das Backend den Job selbst und
  // liefert `status: "computing"` ohne Job-Id (Kontrakt: nie synchron rechnen).
  getRecommendations(assetId: number): Observable<RecommendationsResponse> {
    return this.http.get<RecommendationsResponse>('/api/recommendations', {
      params: new HttpParams().set('asset_id', assetId),
    });
  }

  // „Warum nicht?" (P26 Phase 3) — live berechnet, nur auf Anfrage (nie auf Vorrat, siehe
  // README-Risiko „teuer").
  whyNot(sourceAssetId: number, targetAssetId: number): Observable<WhyNotResponse> {
    return this.http.get<WhyNotResponse>(`/api/recommendations/${sourceAssetId}/${targetAssetId}/why-not`);
  }
}
