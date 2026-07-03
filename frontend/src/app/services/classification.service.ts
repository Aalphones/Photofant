import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type {
  CategoryCreateRequest,
  CategoryPatchRequest,
  ClassificationCategory,
  ClassificationLabel,
  LabelCreateRequest,
  LabelPatchRequest,
} from '@photofant/models';
import { ClassifyService } from './classify.service';

@Injectable({ providedIn: 'root' })
export class ClassificationService {
  private readonly http = inject(HttpClient);
  private readonly classifyService = inject(ClassifyService);

  listCategories(): Observable<ClassificationCategory[]> {
    return this.http.get<ClassificationCategory[]>('/api/classification/categories');
  }

  createCategory(request: CategoryCreateRequest): Observable<ClassificationCategory> {
    return this.http.post<ClassificationCategory>('/api/classification/categories', request);
  }

  patchCategory(id: number, request: CategoryPatchRequest): Observable<ClassificationCategory> {
    return this.http.patch<ClassificationCategory>(`/api/classification/categories/${id}`, request);
  }

  deleteCategory(id: number): Observable<void> {
    return this.http.delete<void>(`/api/classification/categories/${id}`);
  }

  createLabel(categoryId: number, request: LabelCreateRequest): Observable<ClassificationLabel> {
    return this.http.post<ClassificationLabel>(`/api/classification/categories/${categoryId}/labels`, request);
  }

  patchLabel(id: number, request: LabelPatchRequest): Observable<ClassificationLabel> {
    return this.http.patch<ClassificationLabel>(`/api/classification/labels/${id}`, request);
  }

  deleteLabel(id: number): Observable<void> {
    return this.http.delete<void>(`/api/classification/labels/${id}`);
  }

  reclassifyAll(): Observable<{ job_id: string }> {
    return this.classifyService.rerun({ asset_ids: 'all', steps: ['categories'] });
  }
}
