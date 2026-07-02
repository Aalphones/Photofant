import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SearchService {
  private readonly http = inject(HttpClient);

  /** Prewarm the CLIP text encoder session in the background (fire-and-forget). */
  warmSemantic(): Observable<void> {
    return this.http.post<void>('/api/search/warm', {});
  }
}
