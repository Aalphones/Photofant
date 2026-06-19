import { computed, inject, Injectable, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Store } from '@ngrx/store';
import type { ShortcutConfig } from '@photofant/models';
import { SHORTCUT_DEFAULTS } from '@photofant/models';
import { modelsActions, modelsSelectors } from '@photofant/store';

export interface ShortcutEntry {
  key: string;
  description: string;
  context?: string;
}

@Injectable({ providedIn: 'root' })
export class ShortcutService {
  private readonly document = inject(DOCUMENT);
  private readonly store = inject(Store);
  private readonly _entries = signal<ShortcutEntry[]>([]);

  readonly entries = this._entries.asReadonly();
  readonly isLegendVisible = signal(false);

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

  constructor() {
    this.document.addEventListener('keydown', (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (event.key === '?') {
        this.isLegendVisible.update((visible: boolean) => !visible);
      }
    });
  }

  register(entries: ShortcutEntry[]): () => void {
    this._entries.update((list: ShortcutEntry[]) => [...list, ...entries]);
    return () => {
      this._entries.update((list: ShortcutEntry[]) =>
        list.filter((entry: ShortcutEntry) => !entries.includes(entry))
      );
    };
  }

  closeLegend(): void {
    this.isLegendVisible.set(false);
  }

  saveShortcuts(config: ShortcutConfig): void {
    this.store.dispatch(modelsActions.updateShortcuts({ config }));
  }

  resetShortcuts(): void {
    this.store.dispatch(modelsActions.updateShortcuts({ config: null }));
  }
}
