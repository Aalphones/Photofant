import { createSelector } from '@ngrx/store';
import type { Job } from '@photofant/models';
import { jobsFeature } from './jobs.reducer';

const { selectAll, selectIsDockOpen } = jobsFeature;

const STATE_ORDER: Record<string, number> = { running: 0, queued: 1, error: 2, done: 3 };

export const jobsSelectors = {
  allJobs:      selectAll,
  isDockOpen:   selectIsDockOpen,
  activeCount:  createSelector(selectAll, (jobs: Job[]) =>
    jobs.filter((job: Job) => job.state === 'running' || job.state === 'queued').length
  ),
  hasActiveJobs: createSelector(selectAll, (jobs: Job[]) =>
    jobs.some((job: Job) => job.state === 'running' || job.state === 'queued')
  ),
  sortedJobs: createSelector(selectAll, (jobs: Job[]) =>
    [...jobs].sort((a: Job, b: Job) => (STATE_ORDER[a.state] ?? 99) - (STATE_ORDER[b.state] ?? 99))
  ),
};
