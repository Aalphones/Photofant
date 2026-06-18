import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { modelsActions, modelsSelectors, jobsFeature } from '@photofant/store';
import { TIER_META, MODEL_TIERS } from '@photofant/models';
import type { ModelTier, ModelView, Job } from '@photofant/models';
import { ModelCard } from './model-card/model-card';
import { ModelDrawer } from './model-drawer/model-drawer';
import { DownloadDialog } from './download-dialog/download-dialog';
import { BindDialog } from './bind-dialog/bind-dialog';

@Component({
  selector: 'pf-modelle',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ModelCard, ModelDrawer, DownloadDialog, BindDialog],
  templateUrl: './modelle.html',
  styleUrl: './modelle.scss',
  host: { class: 'modelle-host' },
})
export class Modelle {
  private readonly store = inject(Store);

  readonly modelsByTier = this.store.selectSignal(modelsSelectors.selectModelsByTier);
  readonly capabilities = this.store.selectSignal(modelsSelectors.selectCapabilities);
  readonly modelsDir = this.store.selectSignal(modelsSelectors.selectModelsDir);
  readonly isLoading = this.store.selectSignal(modelsSelectors.selectIsLoading);
  readonly activeCount = this.store.selectSignal(modelsSelectors.selectActiveCount);
  readonly missingCoreCount = this.store.selectSignal(modelsSelectors.selectMissingCoreCount);
  readonly isAllCoreInstalled = this.store.selectSignal(modelsSelectors.selectIsAllCoreInstalled);
  readonly pendingDownloads = this.store.selectSignal(modelsSelectors.selectPendingDownloads);
  private readonly downloadJobIds = this.store.selectSignal(modelsSelectors.selectDownloadJobIds);
  private readonly jobEntities = this.store.selectSignal(jobsFeature.selectEntities);
  readonly bindError = this.store.selectSignal(modelsSelectors.selectBindError);

  protected readonly drawerModel = signal<ModelView | null>(null);
  protected readonly downloadTarget = signal<ModelView | null>(null);
  protected readonly bindTarget = signal<ModelView | null>(null);

  protected readonly tiers: ModelTier[] = MODEL_TIERS;
  protected readonly tierMeta = TIER_META;

  constructor() {
    effect(() => {
      this.store.dispatch(modelsActions.loadModels());
      this.store.dispatch(modelsActions.loadCapabilities());
      this.store.dispatch(modelsActions.loadConfig());
    }, { allowSignalWrites: false });
  }

  protected openDrawer(model: ModelView): void {
    this.drawerModel.set(model);
  }

  protected closeDrawer(): void {
    this.drawerModel.set(null);
  }

  protected onDownload(model: ModelView): void {
    this.downloadTarget.set(model);
    this.drawerModel.set(null);
  }

  protected onBind(model: ModelView): void {
    this.bindTarget.set(model);
    this.drawerModel.set(null);
    this.store.dispatch(modelsActions.clearBindError());
  }

  protected onDelete(model: ModelView): void {
    this.drawerModel.set(null);
    this.store.dispatch(modelsActions.deleteModel({ manifestId: model.id }));
  }

  protected onDownloadConfirm(event: { model: ModelView; licenseAck: boolean }): void {
    this.downloadTarget.set(null);
    this.store.dispatch(modelsActions.downloadModel({
      manifestId: event.model.id,
      licenseAck: event.licenseAck,
    }));
  }

  protected onBindConfirm(event: { model: ModelView; path: string }): void {
    this.store.dispatch(modelsActions.registerLocal({
      manifestId: event.model.id,
      path: event.path,
    }));
  }

  protected onBindCancel(): void {
    this.bindTarget.set(null);
    this.store.dispatch(modelsActions.clearBindError());
  }

  protected triggerCoreSetup(): void {
    const coreModels = this.modelsByTier()['core'] ?? [];
    for (const model of coreModels) {
      if (model.status === 'missing' || model.status === 'available') {
        this.store.dispatch(modelsActions.downloadModel({ manifestId: model.id, licenseAck: true }));
      }
    }
  }

  protected isPendingDownload(modelId: string): boolean {
    return this.pendingDownloads().includes(modelId);
  }

  protected isPendingBind(modelId: string): boolean {
    return this.store.selectSignal(modelsSelectors.selectPendingBinds)().includes(modelId);
  }

  protected getDownloadJob(modelId: string): Job | null {
    const jobId = this.downloadJobIds()[modelId];
    if (jobId === undefined) return null;
    return this.jobEntities()[jobId] ?? null;
  }

  protected getModelsForTier(tier: ModelTier): ModelView[] {
    return this.modelsByTier()[tier] ?? [];
  }

  protected countActive(tier: ModelTier): number {
    const models = this.getModelsForTier(tier);
    return models.filter((model) => model.status === 'active' || model.status === 'inplace').length;
  }

  protected tierLabel(tier: ModelTier): string {
    return this.tierMeta[tier]?.label ?? tier;
  }

  protected tierDesc(tier: ModelTier): string {
    return this.tierMeta[tier]?.desc ?? '';
  }
}
