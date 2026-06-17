export interface BackupInfo {
  filename: string;
  path: string;
  size: number;
  created_at: string;
}

export const ISSUE_KINDS = ['orphan', 'missing', 'drift'] as const;
export type IssueKind = typeof ISSUE_KINDS[number];

export const REPAIR_ACTIONS = ['index', 'mark_missing', 'trash', 'fix_path'] as const;
export type RepairActionKind = typeof REPAIR_ACTIONS[number];

export interface OrphanFile {
  path: string;
  size: number;
  person_name: string | null;
  detail: string;
}

export interface MissingFile {
  instance_id: number;
  asset_id: number;
  path: string;
  person_name: string | null;
  detail: string;
}

export interface DriftFile {
  instance_id: number;
  asset_id: number;
  db_path: string;
  found_path: string;
  person_name: string | null;
  detail: string;
}

export interface ReconcileReport {
  generated_at: string | null;
  orphaned_files: OrphanFile[];
  missing_files: MissingFile[];
  path_drift: DriftFile[];
}

export interface RepairItem {
  kind: IssueKind;
  instance_id?: number;
  path?: string;
  found_path?: string;
}

export interface RepairAction {
  item: RepairItem;
  action: RepairActionKind;
}

export interface RepairResult {
  kind: IssueKind;
  action: RepairActionKind;
  status: 'ok' | 'error';
  message: string | null;
}

export interface RepairResponse {
  results: RepairResult[];
  import_job_id: string | null;
}

export const REBUILD_TARGETS = ['thumbnails', 'embeddings'] as const;
export type RebuildTarget = typeof REBUILD_TARGETS[number];

export interface MaintenanceStatus {
  db_size: number;          // db.sqlite size in bytes
  thumbnail_count: number;  // assets with at least one cached thumbnail
  cache_size: number;       // thumbnails.sqlite size in bytes
}
