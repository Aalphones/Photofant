import { createSelector } from '@ngrx/store';
import type { Job } from '@photofant/models';
import { jobsFeature } from './jobs.reducer';

const { selectAll, selectIsDockOpen } = jobsFeature;

export const jobsSelectors = {
  allJobs:      selectAll,
  isDockOpen:   selectIsDockOpen,
  activeCount:  createSelector(selectAll, (jobs: Job[]) =>
    jobs.filter((job: Job) => job.state === 'running' || job.state === 'queued').length
  ),
  hasActiveJobs: createSelector(selectAll, (jobs: Job[]) =>
    jobs.some((job: Job) => job.state === 'running' || job.state === 'queued')
  ),
};
