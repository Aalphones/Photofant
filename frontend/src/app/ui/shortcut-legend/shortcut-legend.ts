import { ChangeDetectionStrategy, Component, inject, output } from '@angular/core';
import { ShortcutEntry, ShortcutService } from '../../services/shortcut.service';
import { Icon } from '../icon/icon';

@Component({
  selector: 'pf-shortcut-legend',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './shortcut-legend.html',
  styleUrl: './shortcut-legend.scss',
})
export class ShortcutLegend {
  private readonly shortcutService = inject(ShortcutService);

  readonly close = output<void>();

  protected readonly entries = this.shortcutService.entries;

  protected groupByContext(): { context: string; entries: ShortcutEntry[] }[] {
    const map = new Map<string, ShortcutEntry[]>();
    for (const entry of this.entries()) {
      const context = entry.context ?? 'Global';
      const group = map.get(context) ?? [];
      group.push(entry);
      map.set(context, group);
    }
    return Array.from(map.entries()).map(([context, entries]) => ({ context, entries }));
  }

  protected onClose(): void {
    this.shortcutService.closeLegend();
    this.close.emit();
  }
}
