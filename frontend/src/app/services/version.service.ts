import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class VersionService {
  thumbnailUrl(versionId: number, size: 256 | 512 | 1024 = 256): string {
    return `/api/versions/${versionId}/thumbnail?size=${size}`;
  }
}
