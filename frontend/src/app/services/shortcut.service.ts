import { computed, inject, Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import type { ShortcutConfig } from '@photofant/models';
import { SHORTCUT_DEFAULTS } from '@photofant/models';
import { modelsActions, modelsSelectors } from '@photofant/store';

@Injectable({ providedIn: 'root' })
export class ShortcutService {
  private readonly store = inject(Store);

  private readonly storedConfig = this.store.selectSignal(modelsSelectors.selectKeyboardShortcuts);

  readonly resolvedShortcuts = computed((): Map<string, string[]> => {
    const map = new Map<string, string[]>(
      SHORTCUT_DEFAULTS.shortcuts.map((binding) => [binding.action, binding.keys])
    );
    const stored = this.storedConfig();
    if (stored != null) {
      for (const binding of stored.shortcuts) {
        map.set(binding.action, binding.keys);
      }
    }
    return map;
  });

  saveShortcuts(config: ShortcutConfig): void {
    this.store.dispatch(modelsActions.updateShortcuts({ config }));
  }

  resetShortcuts(): void {
    this.store.dispatch(modelsActions.updateShortcuts({ config: null }));
  }
}
