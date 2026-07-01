import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import { Icon } from '@photofant/ui';
import type {
  RrAction,
  RrBadgeVariant,
  RrKey,
  RrRepairEvent,
  RrRow,
} from '../review-reconcile.types';

/**
 * One reconcile issue bucket: a titled, badged list with row selection and
 * repair buttons. Selection lives here; the shell only feeds rows + actions and
 * receives a repair event with the affected keys. Drives every bucket so the
 * shell stays a thin configuration layer.
 */
@Component({
  selector: 'pf-rr-section',
  imports: [Icon],
  templateUrl: './rr-section.html',
  styleUrl: './rr-section.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RrSection {
  readonly title = input.required<string>();
  readonly subtitle = input.required<string>();
  readonly variant = input.required<RrBadgeVariant>();
  readonly rows = input.required<RrRow[]>();
  readonly actions = input.required<RrAction[]>();
  readonly busy = input<boolean>(false);

  readonly repair = output<RrRepairEvent>();

  protected readonly selected = signal<Set<RrKey>>(new Set());

  protected readonly count = computed((): number => this.rows().length);
  protected readonly selCount = computed((): number => this.selected().size);

  protected readonly allSelected = computed((): boolean => {
    const rows = this.rows();
    const selected = this.selected();
    return rows.length > 0 && rows.every((row: RrRow) => selected.has(row.key));
  });

  protected isSelected(key: RrKey): boolean {
    return this.selected().has(key);
  }

  protected toggle(key: RrKey): void {
    this.selected.update((selected: Set<RrKey>) => {
      const next = new Set(selected);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  protected toggleAll(): void {
    if (this.allSelected()) {
      this.selected.set(new Set());
    } else {
      this.selected.set(new Set(this.rows().map((row: RrRow) => row.key)));
    }
  }

  protected runBulk(action: RrAction): void {
    const keys = [...this.selected()];
    if (keys.length === 0) {
      return;
    }
    this.repair.emit({ action: action.action, keys });
    this.selected.set(new Set());
  }

  protected runRow(action: RrAction, key: RrKey): void {
    this.repair.emit({ action: action.action, keys: [key] });
  }
}
