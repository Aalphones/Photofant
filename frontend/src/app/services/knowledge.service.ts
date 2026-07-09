import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type { CreateEntityRequest, DomainDto, EntityDto, LoreDto, TaskDto, TaskStatus } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class KnowledgeService {
  private readonly http = inject(HttpClient);

  listDomains(): Observable<DomainDto[]> {
    return this.http.get<DomainDto[]>('/api/knowledge/domains');
  }

  searchEntities(query: string, type?: string, domain?: string): Observable<EntityDto[]> {
    let params = new HttpParams().set('q', query);
    if (type) {
      params = params.set('type', type);
    }
    if (domain) {
      params = params.set('domain', domain);
    }
    return this.http.get<EntityDto[]>('/api/knowledge/entities/search', { params });
  }

  createEntity(request: CreateEntityRequest): Observable<EntityDto> {
    return this.http.post<EntityDto>('/api/knowledge/entities', request);
  }

  // Gebündeltes Wissen zu einem Bild (asset_id) oder einer Person (person_id). Ohne
  // verknüpfte Entity liefert das Backend 200 mit `entity: null` (kein 404 — P25-Kontrakt).
  getLore(params: { assetId?: number | null; personId?: number | null }): Observable<LoreDto> {
    let httpParams = new HttpParams();
    if (params.assetId != null) {
      httpParams = httpParams.set('asset_id', params.assetId);
    }
    if (params.personId != null) {
      httpParams = httpParams.set('person_id', params.personId);
    }
    return this.http.get<LoreDto>('/api/knowledge/lore', { params: httpParams });
  }

  listTasks(status?: TaskStatus): Observable<TaskDto[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return this.http.get<TaskDto[]>('/api/knowledge/tasks', { params });
  }

  resolveTask(taskId: number): Observable<TaskDto> {
    return this.http.post<TaskDto>(`/api/knowledge/tasks/${taskId}/resolve`, {});
  }

  dismissTask(taskId: number): Observable<TaskDto> {
    return this.http.post<TaskDto>(`/api/knowledge/tasks/${taskId}/dismiss`, {});
  }
}
