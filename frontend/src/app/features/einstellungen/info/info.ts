import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { maintenanceActions, maintenanceSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen-info',
  imports: [Icon],
  templateUrl: './info.html',
  styleUrl: './info.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Info {
  private readonly store = inject(Store);

  readonly appInfo = this.store.selectSignal(maintenanceSelectors.selectAppInfo);
  readonly isLoadingAppInfo = this.store.selectSignal(maintenanceSelectors.selectIsLoadingAppInfo);
  readonly objectKeys = Object.keys;

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadAppInfo());
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) { return `${bytes} B`; }
    if (bytes < 1024 * 1024) { return `${(bytes / 1024).toFixed(1)} KB`; }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
