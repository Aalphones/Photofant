import { createSelector } from '@ngrx/store';
import { modelsFeature } from './models.reducer';
import { MODEL_ENRICHMENT, MODEL_TIERS } from '@photofant/models';
import type { ModelDto, ModelTier, ModelView } from '@photofant/models';

const {
  selectModels,
  selectCapabilities,
  selectModelsDir,
  selectDataRoot,
  selectRebootRequired,
  selectProcessingConfig,
  selectKeyboardShortcuts,
  selectIsLoading,
  selectPendingDownloads,
  selectDownloadJobIds,
  selectPendingBinds,
  selectBindError,
  selectBindWarnings,
  selectVram,
  selectError,
} = modelsFeature;

const selectModelViews = createSelector(selectModels, (models: ModelDto[]) =>
  models.map((model): ModelView => {
    const enrichment = MODEL_ENRICHMENT[model.id];
    return {
      ...model,
      tier: enrichment?.tier ?? 'optional',
      desc: enrichment?.desc ?? '',
      licenseNc: enrichment?.licenseNc ?? false,
    };
  })
);

const selectModelsByTier = createSelector(selectModelViews, (models: ModelView[]) => {
  const grouped: Record<ModelTier, ModelView[]> = { core: [], optional: [], generativ: [] };
  for (const model of models) {
    const bucket = grouped[model.tier];
    if (bucket !== undefined) {
      bucket.push(model);
    }
  }
  return grouped;
});

const selectActiveCount = createSelector(selectModels, (models: ModelDto[]) =>
  models.filter((model) => model.status === 'active' || model.status === 'inplace').length
);

const selectMissingCoreCount = createSelector(selectModelViews, (models: ModelView[]) =>
  models.filter((model) => model.tier === 'core' && model.status === 'missing').length
);

const selectCoreModels = createSelector(selectModelViews, (models: ModelView[]) =>
  models.filter((model) => model.tier === 'core')
);

const selectIsAllCoreInstalled = createSelector(selectCoreModels, (coreModels: ModelView[]) =>
  coreModels.length > 0 &&
  coreModels.every((model) => model.status === 'active' || model.status === 'inplace')
);

export const modelsSelectors = {
  selectModels,
  selectCapabilities,
  selectModelsDir,
  selectDataRoot,
  selectRebootRequired,
  selectProcessingConfig,
  selectKeyboardShortcuts,
  selectIsLoading,
  selectPendingDownloads,
  selectDownloadJobIds,
  selectPendingBinds,
  selectBindError,
  selectBindWarnings,
  selectVram,
  selectError,
  selectModelViews,
  selectModelsByTier,
  selectActiveCount,
  selectMissingCoreCount,
  selectCoreModels,
  selectIsAllCoreInstalled,
  MODEL_TIERS,
};
