import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type {
  Collection,
  CollectionDetail,
  CreateCollectionRequest,
  CreateTriggerRequest,
  TrainingSetItem,
  TrainingSetStats,
  Trigger,
  UpdateCollectionRequest,
} from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class CollectionService {
  private readonly http = inject(HttpClient);

  listCollections(): Observable<Collection[]> {
    return this.http.get<Collection[]>('/api/collections');
  }

  getCollection(id: number): Observable<CollectionDetail> {
    return this.http.get<CollectionDetail>(`/api/collections/${id}`);
  }

  createCollection(request: CreateCollectionRequest): Observable<CollectionDetail> {
    return this.http.post<CollectionDetail>('/api/collections', request);
  }

  updateCollection(id: number, request: UpdateCollectionRequest): Observable<CollectionDetail> {
    return this.http.patch<CollectionDetail>(`/api/collections/${id}`, request);
  }

  deleteCollection(id: number): Observable<void> {
    return this.http.delete<void>(`/api/collections/${id}`);
  }

  addTrigger(collectionId: number, request: CreateTriggerRequest): Observable<Trigger> {
    return this.http.post<Trigger>(`/api/collections/${collectionId}/triggers`, request);
  }

  updateTrigger(collectionId: number, triggerId: number, negate: boolean): Observable<Trigger> {
    return this.http.patch<Trigger>(`/api/collections/${collectionId}/triggers/${triggerId}`, { negate });
  }

  deleteTrigger(collectionId: number, triggerId: number): Observable<void> {
    return this.http.delete<void>(`/api/collections/${collectionId}/triggers/${triggerId}`);
  }

  addItems(collectionId: number, assetIds: number[]): Observable<void> {
    return this.http.post<void>(`/api/collections/${collectionId}/items`, { asset_ids: assetIds });
  }

  removeItem(collectionId: number, assetId: number): Observable<void> {
    return this.http.delete<void>(`/api/collections/${collectionId}/items/${assetId}`);
  }

  setOrder(collectionId: number, assetIds: number[]): Observable<void> {
    return this.http.put<void>(`/api/collections/${collectionId}/order`, { asset_ids: assetIds });
  }

  getItems(collectionId: number): Observable<TrainingSetItem[]> {
    return this.http.get<TrainingSetItem[]>(`/api/collections/${collectionId}/items`);
  }

  updateItemCaption(collectionId: number, assetId: number, captionOverride: string | null): Observable<void> {
    return this.http.patch<void>(`/api/collections/${collectionId}/items/${assetId}`, {
      caption_override: captionOverride,
    });
  }

  getStats(collectionId: number): Observable<TrainingSetStats> {
    return this.http.get<TrainingSetStats>(`/api/collections/${collectionId}/stats`);
  }
}
