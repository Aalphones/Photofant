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

      source.onerror = (): void => {
        source.close();
        observer.error(new Error('SSE connection failed'));
      };

      return (): void => source.close();
    });
  }
}
