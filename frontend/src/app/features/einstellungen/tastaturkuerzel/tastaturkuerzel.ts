import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import type { ShortcutConfig } from '@photofant/models';
import { ShortcutService } from '../../../services/shortcut.service';
import { SHORTCUT_ROWS } from '../einstellungen.types';

@Component({
  selector: 'pf-einstellungen-tastaturkuerzel',
  imports: [],
  templateUrl: './tastaturkuerzel.html',
  styleUrl: './tastaturkuerzel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tastaturkuerzel {
  private readonly shortcutService = inject(ShortcutService);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  readonly shortcutRows = SHORTCUT_ROWS;
  readonly resolvedShortcuts = this.shortcutService.resolvedShortcuts;
  readonly listeningAction = signal<string | null>(null);

  constructor() {
    const onCaptureKey = (event: KeyboardEvent): void => {
      const action = this.listeningAction();
      if (action == null) { return; }
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
      event.preventDefault();
      event.stopPropagation();
      this.applyCapture(action, event.key);
    };
    this.document.addEventListener('keydown', onCaptureKey, { capture: true });
    this.destroyRef.onDestroy(() =>
      this.document.removeEventListener('keydown', onCaptureKey, { capture: true })
    );
  }

  startListening(action: string): void {
    this.listeningAction.set(action);
  }

  private applyCapture(action: string, key: string): void {
    const current = this.resolvedShortcuts();
    const shortcuts = SHORTCUT_ROWS.map((row): { action: string; keys: string[] } => ({
      action: row.action,
      keys: row.action === action ? [key] : (current.get(row.action) ?? []),
    }));
    const config: ShortcutConfig = { version: 1, shortcuts };
    this.shortcutService.saveShortcuts(config);
    this.listeningAction.set(null);
  }

  resetShortcuts(): void {
    this.shortcutService.resetShortcuts();
  }

  formatKeys(keys: string[] | undefined): string {
    if (keys == null || keys.length === 0) { return '–'; }
    return keys
      .map((key: string) => {
        const labels: Record<string, string> = {
          ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓',
          Escape: 'Esc', Delete: 'Entf', Backspace: '⌫', Enter: '↵',
          ' ': 'Leertaste',
        };
        return labels[key] ?? key;
      })
      .join(' / ');
  }
}
