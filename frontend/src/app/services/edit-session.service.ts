import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { ApplyStepResponse, CreateSessionResponse, EditorTargetKind, OrientationOverwriteResponse, RollbackResponse, SaveMode, VersionDto } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class EditSessionService {
  private readonly http = inject(HttpClient);

  createSession(kind: EditorTargetKind, targetId: number): Observable<CreateSessionResponse> {
    return this.http.post<CreateSessionResponse>('/api/edit-sessions', {
      target: { kind, id: targetId },
    });
  }

  applyStep(sessionKey: string, op: string, params: Record<string, unknown>): Observable<ApplyStepResponse> {
    return this.http.post<ApplyStepResponse>(`/api/edit-sessions/${sessionKey}/steps`, { op, params });
  }

  rollback(sessionKey: string, toSeq: number): Observable<RollbackResponse> {
    return this.http.post<RollbackResponse>(`/api/edit-sessions/${sessionKey}/rollback`, { to_seq: toSeq });
  }

  save(sessionKey: string, mode: SaveMode): Observable<VersionDto | OrientationOverwriteResponse> {
    return this.http.post<VersionDto | OrientationOverwriteResponse>(`/api/edit-sessions/${sessionKey}/save`, { mode });
  }

  previewUrl(sessionKey: string, seq: number): string {
    return `/api/edit-sessions/${sessionKey}/preview/${seq}`;
  }
}
