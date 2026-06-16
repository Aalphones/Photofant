import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { BackupInfo } from '@photofant/models';

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
}
