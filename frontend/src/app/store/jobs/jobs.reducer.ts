import { createEntityAdapter, type EntityAdapter, type EntityState } from '@ngrx/entity';
import { createFeature, createReducer, on } from '@ngrx/store';
import type { Job } from '@photofant/models';
import { jobsActions } from './jobs.actions';

interface JobsState extends EntityState<Job> {
  isDockOpen: boolean;
}

const adapter: EntityAdapter<Job> = createEntityAdapter<Job>({
  selectId: (job: Job) => job.id,
});

const initialState: JobsState = adapter.getInitialState({ isDockOpen: false });

export const jobsFeature = createFeature({
  name: 'jobs',
  reducer: createReducer(
    initialState,
    on(jobsActions.upsertJob, (state: JobsState, { job }) =>
      adapter.upsertOne(job, state)
    ),
    on(jobsActions.toggleDock, (state: JobsState) => ({
      ...state,
      isDockOpen: !state.isDockOpen,
    })),
    on(jobsActions.closeDock, (state: JobsState) => ({
      ...state,
      isDockOpen: false,
    })),
  ),
  extraSelectors: ({ selectJobsState }) => ({
    ...adapter.getSelectors(selectJobsState),
  }),
});
