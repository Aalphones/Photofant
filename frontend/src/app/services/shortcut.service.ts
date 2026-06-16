import { Injectable, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { inject } from '@angular/core';

export interface ShortcutEntry {
  key: string;
  description: string;
  context?: string;
}

@Injectable({ providedIn: 'root' })
export class ShortcutService {
  private readonly document = inject(DOCUMENT);
  private readonly _entries = signal<ShortcutEntry[]>([]);

  readonly entries = this._entries.asReadonly();
  readonly isLegendVisible = signal(false);

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
}
