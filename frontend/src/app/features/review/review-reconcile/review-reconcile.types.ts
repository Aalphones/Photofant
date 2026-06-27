import type { RepairActionKind } from '@photofant/models';

/** A row's stable identity — a path (orphans) or a numeric DB id (everything else). */
export type RrKey = string | number;

/** Visual weight of a section's count badge. */
export type RrBadgeVariant = 'warn' | 'danger' | 'info';

/** One issue rendered as a list row, projected from any reconcile bucket. */
export interface RrRow {
  key: RrKey;
  name: string;
  meta: string;
}

/** A repair button available on a section (both as bulk and per-row). */
export interface RrAction {
  label: string;
  variant: 'primary' | 'danger';
  action: RepairActionKind;
  icon: string;
}

/** Emitted by a section when the user triggers a repair on one or more rows. */
export interface RrRepairEvent {
  action: RepairActionKind;
  keys: RrKey[];
}
