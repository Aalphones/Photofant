export interface BackupInfo {
  filename: string;
  path: string;
  size: number;
  created_at: string;
}

export const ISSUE_KINDS = [
  'orphan',
  'missing',
  'drift',
  'orphaned_face',
  'misassigned',
  'acknowledged_missing',
  'orphaned_edit',
  'stranded_face',
] as const;
export type IssueKind = typeof ISSUE_KINDS[number];

export const REPAIR_ACTIONS = [
  'index',
  'mark_missing',
  'trash',
  'fix_path',
  'purge',
  'fix_assignment',
  'move_crop',
] as const;
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

export interface OrphanedFace {
  face_id: number;
  asset_id: number;
  crop_path: string;
  person_name: string | null;
  detail: string;
}

export interface MisassignedInstance {
  instance_id: number;
  asset_id: number;
  path: string;
  person_name: string | null;
  detail: string;
}

export interface AcknowledgedMissing {
  instance_id: number;
  asset_id: number;
  path: string;
  person_name: string | null;
  missing_at: string;
  detail: string;
}

export interface StrandedFace {
  face_id: number;
  person_id: number;
  person_name: string | null;
  crop_path: string;
  detail: string;
}

export interface ReconcileReport {
  generated_at: string | null;
  orphaned_files: OrphanFile[];
  missing_files: MissingFile[];
  path_drift: DriftFile[];
  orphaned_faces: OrphanedFace[];
  misassigned_instances: MisassignedInstance[];
  acknowledged_missing: AcknowledgedMissing[];
  orphaned_edits: OrphanFile[];
  stranded_faces: StrandedFace[];
}

export interface RepairItem {
  kind: IssueKind;
  instance_id?: number;
  face_id?: number;
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

export const REBUILD_TARGETS = ['thumbnails', 'embeddings', 'faces', 'knowledge', 'knowledge_reconcile'] as const;
export type RebuildTarget = typeof REBUILD_TARGETS[number];

export interface MaintenanceStatus {
  db_size: number;          // db.sqlite size in bytes
  thumbnail_count: number;  // assets with at least one cached thumbnail
  cache_size: number;       // thumbnails.sqlite size in bytes
  image_count: number;      // total assets in the database
  face_crop_count: number;  // total face crops in the database
  disk_total: number;       // total bytes on the filesystem hosting data_root
  disk_used: number;        // used bytes on that filesystem
}
