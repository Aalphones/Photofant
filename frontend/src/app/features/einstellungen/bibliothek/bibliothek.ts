import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { Store } from '@ngrx/store';
import { modelsActions, modelsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-einstellungen-bibliothek',
  imports: [Icon],
  templateUrl: './bibliothek.html',
  styleUrl: './bibliothek.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Bibliothek {
  private readonly store = inject(Store);

  readonly dataRoot = this.store.selectSignal(modelsSelectors.selectDataRoot);
  readonly rebootRequired = this.store.selectSignal(modelsSelectors.selectRebootRequired);
  readonly modelsDir = this.store.selectSignal(modelsSelectors.selectModelsDir);
  readonly isDataRootEditing = signal<boolean>(false);
  readonly pendingDataRoot = signal<string>('');
  readonly isDirEditing = signal<boolean>(false);
  readonly pendingDir = signal<string>('');

  constructor() {
    effect(() => {
      this.store.dispatch(modelsActions.loadConfig());
    });
  }

  startDataRootEdit(): void {
    this.pendingDataRoot.set(this.dataRoot() ?? '');
    this.isDataRootEditing.set(true);
  }

  cancelDataRootEdit(): void {
    this.isDataRootEditing.set(false);
  }

  saveDataRootEdit(): void {
    const newPath = this.pendingDataRoot().trim();
    if (newPath.length > 0) {
      this.store.dispatch(modelsActions.updateDataRoot({ path: newPath }));
    }
    this.isDataRootEditing.set(false);
  }

  startDirEdit(): void {
    this.pendingDir.set(this.modelsDir() ?? '');
    this.isDirEditing.set(true);
  }

  cancelDirEdit(): void {
    this.isDirEditing.set(false);
  }

  saveDirEdit(): void {
    const newDir = this.pendingDir().trim();
    if (newDir.length > 0) {
      this.store.dispatch(modelsActions.updateModelsDir({ path: newDir }));
    }
    this.isDirEditing.set(false);
  }
}
