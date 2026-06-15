import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import type { Job } from '@photofant/models';
import { Icon } from '../icon/icon';

const ICON_MAP: Record<string, string> = {
  tag:      'tag',
  face:     'face',
  caption:  'search',
  download: 'download',
  import:   'import',
  thumbnail: 'gallery',
};

@Component({
  selector: 'pf-job-dock',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './job-dock.html',
  styleUrl: './job-dock.scss',
})
export class JobDock {
  readonly jobs  = input.required<Job[]>();
  readonly close = output<void>();

  protected iconFor(kind: string): string {
    return ICON_MAP[kind] ?? 'refresh';
  }

  protected pct(job: Job): number {
    return job.state === 'done' ? 100 : Math.round(job.progress * 100);
  }
}
