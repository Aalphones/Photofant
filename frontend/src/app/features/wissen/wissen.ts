import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import type { CreateEntityRequest } from '@photofant/models';
import { knowledgeActions, knowledgeSelectors } from '@photofant/store';
import { Icon } from '../../ui/icon/icon';
import { EntityWizardDialog } from './entity-wizard-dialog/entity-wizard-dialog';

@Component({
  selector: 'pf-wissen',
  imports: [Icon, EntityWizardDialog],
  templateUrl: './wissen.html',
  styleUrl: './wissen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Wissen {
  private readonly store = inject(Store);

  protected readonly domains = this.store.selectSignal(knowledgeSelectors.selectDomains);
  protected readonly domainsLoading = this.store.selectSignal(knowledgeSelectors.selectDomainsLoading);
  protected readonly isSaving = this.store.selectSignal(knowledgeSelectors.selectIsSaving);
  protected readonly saveError = this.store.selectSignal(knowledgeSelectors.selectSaveError);
  protected readonly lastCreatedEntity = this.store.selectSignal(knowledgeSelectors.selectLastCreatedEntity);

  protected readonly showWizard = signal(false);

  constructor() {
    this.store.dispatch(knowledgeActions.loadDomains());

    // Wizard schließt sich selbst, sobald das Anlegen erfolgreich war.
    effect(() => {
      if (this.lastCreatedEntity() !== null) {
        this.showWizard.set(false);
      }
    });
  }

  protected openWizard(): void {
    this.store.dispatch(knowledgeActions.resetCreateEntityState());
    this.showWizard.set(true);
  }

  protected closeWizard(): void {
    this.showWizard.set(false);
  }

  protected onSave(request: CreateEntityRequest): void {
    this.store.dispatch(knowledgeActions.createEntity({ request }));
  }
}
