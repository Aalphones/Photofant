import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import type { Job } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class JobsService {
  triggerDemo(): Observable<string> {
    return new Observable<string>((observer) => {
      fetch('/api/jobs/demo', { method: 'POST' })
        .then((response: Response) => response.json())
        .then((body: { job_id: string }) => {
          observer.next(body.job_id);
          observer.complete();
        })
        .catch((error: Error) => observer.error(error));
    });
  }

  streamJobs(): Observable<Job> {
    return new Observable<Job>((observer) => {
      const source = new EventSource('/api/jobs/stream');

      source.addEventListener('job', (event: MessageEvent) => {
        const job = JSON.parse(event.data) as Job;
        observer.next(job);
      });

      // EventSource reconnected von sich aus nach einem Verbindungsabbruch (readyState
      // wechselt auf CONNECTING). Nur bei CLOSED hat der Browser selbst aufgegeben — erst
      // dann geben wir terminal auf, statt jeden kurzen Aussetzer hart zu beenden.
      source.onerror = (): void => {
        if (source.readyState === EventSource.CLOSED) {
          observer.error(new Error('SSE connection failed'));
        } else {
          console.warn('[jobs] SSE reconnecting…');
        }
      };

      return (): void => source.close();
    });
  }
}
