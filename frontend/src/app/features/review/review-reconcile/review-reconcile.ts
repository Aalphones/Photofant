import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import type {
  DriftFile,
  MissingFile,
  OrphanFile,
  RepairAction,
} from '@photofant/models';
import { maintenanceActions, maintenanceSelectors } from '@photofant/store';

@Component({
  selector: 'pf-review-reconcile',
  imports: [Icon, DatePipe],
  templateUrl: './review-reconcile.html',
  styleUrl: './review-reconcile.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewReconcile {
  private readonly store = inject(Store);

  protected readonly report = this.store.selectSignal(maintenanceSelectors.selectReport);
  protected readonly isScanning = this.store.selectSignal(maintenanceSelectors.selectIsScanning);
  protected readonly isRepairing = this.store.selectSignal(maintenanceSelectors.selectIsRepairing);

  protected readonly selectedOrphans = signal<Set<string>>(new Set());
  protected readonly selectedMissing = signal<Set<number>>(new Set());
  protected readonly selectedDrift = signal<Set<number>>(new Set());

  protected readonly orphanCount = computed(() => this.report()?.orphaned_files.length ?? 0);
  protected readonly missingCount = computed(() => this.report()?.missing_files.length ?? 0);
  protected readonly driftCount = computed(() => this.report()?.path_drift.length ?? 0);
  protected readonly totalIssues = computed(() =>
    this.orphanCount() + this.missingCount() + this.driftCount()
  );

  protected readonly selOrphanCount = computed(() => this.selectedOrphans().size);
  protected readonly selMissingCount = computed(() => this.selectedMissing().size);
  protected readonly selDriftCount = computed(() => this.selectedDrift().size);
  protected readonly anySelected = computed(() =>
    this.selOrphanCount() > 0 || this.selMissingCount() > 0 || this.selDriftCount() > 0
  );

  protected readonly allOrphansSelected = computed((): boolean => {
    const orphans = this.report()?.orphaned_files ?? [];
    const sel = this.selectedOrphans();
    return orphans.length > 0 && orphans.every((orphan: OrphanFile) => sel.has(orphan.path));
  });

  protected readonly allMissingSelected = computed((): boolean => {
    const missing = this.report()?.missing_files ?? [];
    const sel = this.selectedMissing();
    return missing.length > 0 && missing.every((item: MissingFile) => sel.has(item.instance_id));
  });

  protected readonly allDriftSelected = computed((): boolean => {
    const drift = this.report()?.path_drift ?? [];
    const sel = this.selectedDrift();
    return drift.length > 0 && drift.every((item: DriftFile) => sel.has(item.instance_id));
  });

  protected triggerScan(): void {
    this.store.dispatch(maintenanceActions.triggerReconcile());
    this.clearSelections();
  }

  protected clearSelections(): void {
    this.selectedOrphans.set(new Set());
    this.selectedMissing.set(new Set());
    this.selectedDrift.set(new Set());
  }

  // ── Orphan selection ─────────────────────────────────────────

  protected toggleOrphan(path: string): void {
    this.selectedOrphans.update((sel: Set<string>) => {
      const next = new Set(sel);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }

  protected toggleAllOrphans(): void {
    const orphans = this.report()?.orphaned_files ?? [];
    if (this.allOrphansSelected()) {
      this.selectedOrphans.set(new Set());
    } else {
      this.selectedOrphans.set(new Set(orphans.map((orphan: OrphanFile) => orphan.path)));
    }
  }

  protected isOrphanSelected(path: string): boolean {
    return this.selectedOrphans().has(path);
  }

  // ── Missing selection ─────────────────────────────────────────

  protected toggleMissing(instanceId: number): void {
    this.selectedMissing.update((sel: Set<number>) => {
      const next = new Set(sel);
      if (next.has(instanceId)) {
        next.delete(instanceId);
      } else {
        next.add(instanceId);
      }
      return next;
    });
  }

  protected toggleAllMissing(): void {
    const missing = this.report()?.missing_files ?? [];
    if (this.allMissingSelected()) {
      this.selectedMissing.set(new Set());
    } else {
      this.selectedMissing.set(new Set(missing.map((item: MissingFile) => item.instance_id)));
    }
  }

  protected isMissingSelected(instanceId: number): boolean {
    return this.selectedMissing().has(instanceId);
  }

  // ── Drift selection ───────────────────────────────────────────

  protected toggleDrift(instanceId: number): void {
    this.selectedDrift.update((sel: Set<number>) => {
      const next = new Set(sel);
      if (next.has(instanceId)) {
        next.delete(instanceId);
      } else {
        next.add(instanceId);
      }
      return next;
    });
  }

  protected toggleAllDrift(): void {
    const drift = this.report()?.path_drift ?? [];
    if (this.allDriftSelected()) {
      this.selectedDrift.set(new Set());
    } else {
      this.selectedDrift.set(new Set(drift.map((item: DriftFile) => item.instance_id)));
    }
  }

  protected isDriftSelected(instanceId: number): boolean {
    return this.selectedDrift().has(instanceId);
  }

  // ── Bulk actions ──────────────────────────────────────────────

  protected indexSelectedOrphans(): void {
    const orphans = this.report()?.orphaned_files ?? [];
    const sel = this.selectedOrphans();
    const actions: RepairAction[] = orphans
      .filter((orphan: OrphanFile) => sel.has(orphan.path))
      .map((orphan: OrphanFile) => ({
        item: { kind: 'orphan' as const, path: orphan.path },
        action: 'index' as const,
      }));
    if (actions.length > 0) {
      this.store.dispatch(maintenanceActions.repair({ actions }));
      this.selectedOrphans.set(new Set());
    }
  }

  protected trashSelectedOrphans(): void {
    const orphans = this.report()?.orphaned_files ?? [];
    const sel = this.selectedOrphans();
    const actions: RepairAction[] = orphans
      .filter((orphan: OrphanFile) => sel.has(orphan.path))
      .map((orphan: OrphanFile) => ({
        item: { kind: 'orphan' as const, path: orphan.path },
        action: 'trash' as const,
      }));
    if (actions.length > 0) {
      this.store.dispatch(maintenanceActions.repair({ actions }));
      this.selectedOrphans.set(new Set());
    }
  }

  protected markSelectedMissing(): void {
    const missing = this.report()?.missing_files ?? [];
    const sel = this.selectedMissing();
    const actions: RepairAction[] = missing
      .filter((item: MissingFile) => sel.has(item.instance_id))
      .map((item: MissingFile) => ({
        item: { kind: 'missing' as const, instance_id: item.instance_id },
        action: 'mark_missing' as const,
      }));
    if (actions.length > 0) {
      this.store.dispatch(maintenanceActions.repair({ actions }));
      this.selectedMissing.set(new Set());
    }
  }

  // ── Single-item actions (called from template) ───────────────

  protected repairOrphan(path: string, action: 'index' | 'trash'): void {
    this.store.dispatch(maintenanceActions.repair({
      actions: [{ item: { kind: 'orphan', path }, action }],
    }));
  }

  protected repairMissing(instanceId: number): void {
    this.store.dispatch(maintenanceActions.repair({
      actions: [{ item: { kind: 'missing', instance_id: instanceId }, action: 'mark_missing' }],
    }));
  }

  protected repairDrift(instanceId: number, foundPath: string): void {
    this.store.dispatch(maintenanceActions.repair({
      actions: [{ item: { kind: 'drift', instance_id: instanceId, found_path: foundPath }, action: 'fix_path' }],
    }));
  }

  protected fixSelectedDrift(): void {
    const drift = this.report()?.path_drift ?? [];
    const sel = this.selectedDrift();
    const actions: RepairAction[] = drift
      .filter((item: DriftFile) => sel.has(item.instance_id))
      .map((item: DriftFile) => ({
        item: {
          kind: 'drift' as const,
          instance_id: item.instance_id,
          found_path: item.found_path,
        },
        action: 'fix_path' as const,
      }));
    if (actions.length > 0) {
      this.store.dispatch(maintenanceActions.repair({ actions }));
      this.selectedDrift.set(new Set());
    }
  }

  protected fileName(path: string): string {
    return path.split(/[\\/]/).pop() ?? path;
  }

  protected folderLabel(path: string): string {
    const parts = path.split(/[\\/]/);
    return parts.length >= 2 ? (parts[parts.length - 2] ?? '') : '';
  }
}
