import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type {
  BackupInfo,
  MaintenanceStatus,
  RebuildTarget,
  ReconcileReport,
  RepairAction,
  RepairResponse,
} from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class MaintenanceService {
  private readonly http = inject(HttpClient);

  triggerBackup(targetDir?: string): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/maintenance/backup', {
      target_dir: targetDir ?? null,
    });
  }

  listBackups(): Observable<BackupInfo[]> {
    return this.http.get<BackupInfo[]>('/api/maintenance/backups');
  }

  triggerReconcile(): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/maintenance/reconcile', {});
  }

  loadReconcileReport(): Observable<ReconcileReport> {
    return this.http.get<ReconcileReport>('/api/maintenance/reconcile/report');
  }

  repair(actions: RepairAction[]): Observable<RepairResponse> {
    return this.http.post<RepairResponse>('/api/maintenance/reconcile/repair', {
      actions,
    });
  }

  triggerRebuild(target: RebuildTarget): Observable<{ job_id: string }> {
    return this.http.post<{ job_id: string }>('/api/maintenance/rebuild', {
      target,
    });
  }

  loadStatus(): Observable<MaintenanceStatus> {
    return this.http.get<MaintenanceStatus>('/api/maintenance/status');
  }
}
