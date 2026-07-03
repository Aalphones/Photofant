import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import type {
  AcknowledgedMissing,
  DriftFile,
  IssueKind,
  MisassignedInstance,
  MissingFile,
  OrphanFile,
  OrphanedFace,
  RepairAction,
  RepairActionKind,
  StrandedFace,
} from '@photofant/models';
import { maintenanceActions, maintenanceSelectors } from '@photofant/store';
import { RrSection } from './rr-section/rr-section';
import type { RrAction, RrKey, RrRepairEvent, RrRow } from './review-reconcile.types';

@Component({
  selector: 'pf-review-reconcile',
  imports: [Icon, DatePipe, RrSection],
  templateUrl: './review-reconcile.html',
  styleUrl: './review-reconcile.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewReconcile {
  private readonly store = inject(Store);

  protected readonly report = this.store.selectSignal(maintenanceSelectors.selectReport);
  protected readonly isScanning = this.store.selectSignal(maintenanceSelectors.selectIsScanning);
  protected readonly isRepairing = this.store.selectSignal(maintenanceSelectors.selectIsRepairing);

  // ── Repair button configs per bucket (label + action + style) ──────────────

  protected readonly ORPHAN_ACTIONS: RrAction[] = [
    { label: 'Indizieren', variant: 'primary', action: 'index', icon: 'plus' },
    { label: 'Papierkorb', variant: 'danger', action: 'trash', icon: 'trash' },
  ];
  protected readonly MISSING_ACTIONS: RrAction[] = [
    { label: 'Als fehlend markieren', variant: 'danger', action: 'mark_missing', icon: 'x' },
  ];
  protected readonly DRIFT_ACTIONS: RrAction[] = [
    { label: 'Pfad korrigieren', variant: 'primary', action: 'fix_path', icon: 'check' },
  ];
  protected readonly MISASSIGNED_ACTIONS: RrAction[] = [
    { label: 'Zuordnung bereinigen', variant: 'primary', action: 'fix_assignment', icon: 'check' },
  ];
  protected readonly ORPHANED_FACE_ACTIONS: RrAction[] = [
    { label: 'Endgültig entfernen', variant: 'danger', action: 'purge', icon: 'trash' },
  ];
  protected readonly STRANDED_FACE_ACTIONS: RrAction[] = [
    { label: 'In richtigen Ordner verschieben', variant: 'primary', action: 'move_crop', icon: 'check' },
  ];
  protected readonly ACK_MISSING_ACTIONS: RrAction[] = [
    { label: 'Endgültig entfernen', variant: 'danger', action: 'purge', icon: 'trash' },
  ];
  protected readonly ORPHANED_EDIT_ACTIONS: RrAction[] = [
    { label: 'Indizieren', variant: 'primary', action: 'index', icon: 'plus' },
    { label: 'Papierkorb', variant: 'danger', action: 'trash', icon: 'trash' },
  ];

  // ── Buckets projected to display rows ───────────────────────────────────────

  protected readonly orphanRows = computed((): RrRow[] =>
    (this.report()?.orphaned_files ?? []).map((file: OrphanFile) => ({
      key: file.path,
      name: this.fileName(file.path),
      meta: this.folderLabel(file.path),
    }))
  );

  protected readonly missingRows = computed((): RrRow[] =>
    (this.report()?.missing_files ?? []).map((file: MissingFile) => ({
      key: file.instance_id,
      name: this.fileName(file.path),
      meta: file.person_name ?? '_unknown',
    }))
  );

  protected readonly driftRows = computed((): RrRow[] =>
    (this.report()?.path_drift ?? []).map((file: DriftFile) => ({
      key: file.instance_id,
      name: this.fileName(file.found_path),
      meta: `${file.person_name ?? '_unknown'} · war: ${this.fileName(file.db_path)}`,
    }))
  );

  protected readonly misassignedRows = computed((): RrRow[] =>
    (this.report()?.misassigned_instances ?? []).map((instance: MisassignedInstance) => ({
      key: instance.instance_id,
      name: this.fileName(instance.path),
      meta: `${instance.person_name ?? '_unknown'} · ohne Gesicht auf diesem Bild`,
    }))
  );

  protected readonly orphanedFaceRows = computed((): RrRow[] =>
    (this.report()?.orphaned_faces ?? []).map((face: OrphanedFace) => ({
      key: face.face_id,
      name: this.fileName(face.crop_path),
      meta: `${face.person_name ?? '_unknown'} · Bild gelöscht`,
    }))
  );

  protected readonly ackMissingRows = computed((): RrRow[] =>
    (this.report()?.acknowledged_missing ?? []).map((instance: AcknowledgedMissing) => ({
      key: instance.instance_id,
      name: this.fileName(instance.path),
      meta: `${instance.person_name ?? '_unknown'} · fehlend seit ${instance.missing_at.slice(0, 10)}`,
    }))
  );

  protected readonly orphanedEditRows = computed((): RrRow[] =>
    (this.report()?.orphaned_edits ?? []).map((file: OrphanFile) => ({
      key: file.path,
      name: this.fileName(file.path),
      meta: this.folderLabel(file.path),
    }))
  );

  protected readonly strandedFaceRows = computed((): RrRow[] =>
    (this.report()?.stranded_faces ?? []).map((face: StrandedFace) => ({
      key: face.face_id,
      name: this.fileName(face.crop_path),
      meta: `${face.person_name ?? 'Person ' + face.person_id} · Crop im falschen Ordner`,
    }))
  );

  protected readonly totalIssues = computed((): number =>
    this.orphanRows().length +
    this.missingRows().length +
    this.driftRows().length +
    this.misassignedRows().length +
    this.orphanedFaceRows().length +
    this.ackMissingRows().length +
    this.orphanedEditRows().length +
    this.strandedFaceRows().length
  );

  // ── Actions ─────────────────────────────────────────────────────────────────

  protected triggerScan(): void {
    this.store.dispatch(maintenanceActions.triggerReconcile());
  }

  protected onRepair(kind: IssueKind, event: RrRepairEvent): void {
    const actions: RepairAction[] = event.keys.map((key: RrKey) =>
      this.buildAction(kind, key, event.action)
    );
    if (actions.length > 0) {
      this.store.dispatch(maintenanceActions.repair({ actions }));
    }
  }

  private buildAction(kind: IssueKind, key: RrKey, action: RepairActionKind): RepairAction {
    switch (kind) {
      case 'orphan':
      case 'orphaned_edit':
        return { item: { kind, path: key as string }, action };
      case 'drift': {
        // fix_path needs the rediscovered location, looked up by the row's instance id.
        const drift = (this.report()?.path_drift ?? []).find(
          (file: DriftFile) => file.instance_id === key
        );
        if (!drift) {
          // The key always comes from a rendered drift row; this only guards a torn-down report.
          return { item: { kind, instance_id: key as number }, action };
        }
        return { item: { kind, instance_id: key as number, found_path: drift.found_path }, action };
      }
      case 'orphaned_face':
      case 'stranded_face':
        return { item: { kind, face_id: key as number }, action };
      default:
        // missing, misassigned, acknowledged_missing — all keyed by instance id.
        return { item: { kind, instance_id: key as number }, action };
    }
  }

  // ── Path helpers (display only) ─────────────────────────────────────────────

  protected fileName(path: string): string {
    return path.split(/[\\/]/).pop() ?? path;
  }

  protected folderLabel(path: string): string {
    const parts = path.split(/[\\/]/);
    return parts.length >= 2 ? (parts[parts.length - 2] ?? '') : '';
  }
}
