import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import type { Observable } from 'rxjs';
import type {
  PromptTemplateDto,
  CreatePromptTemplateRequest,
  UpdatePromptTemplateRequest,
} from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class PromptTemplateService {
  private readonly http = inject(HttpClient);

  list(): Observable<PromptTemplateDto[]> {
    return this.http.get<PromptTemplateDto[]>('/api/prompt-templates');
  }

  create(body: CreatePromptTemplateRequest): Observable<PromptTemplateDto> {
    return this.http.post<PromptTemplateDto>('/api/prompt-templates', body);
  }

  update(id: number, body: UpdatePromptTemplateRequest): Observable<PromptTemplateDto> {
    return this.http.patch<PromptTemplateDto>(`/api/prompt-templates/${id}`, body);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/prompt-templates/${id}`);
  }
}
