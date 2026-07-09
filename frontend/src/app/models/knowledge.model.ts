export const OWNERS = ['user', 'manual', 'web', 'inferred'] as const;
export type Owner = typeof OWNERS[number];

export interface MediaLinks {
  persons: number[];
  assets: number[];
}

export interface Relationship {
  type: string;
  target: string;
}

export interface EntityDto {
  id: string;
  type: string;
  title: string;
  domain: string;
  owner: Owner;
  confidence: number;
  status: string;
  aliases: string[];
  media_links: MediaLinks;
  relationships: Relationship[];
  sources: string[];
  body: string;
}

export interface CreateEntityRequest {
  id: string;
  type: string;
  title: string;
  domain: string;
  aliases?: string[];
  status?: string;
  owner?: Owner;
  confidence?: number;
  media_links?: MediaLinks;
  relationships?: Relationship[];
  sources?: string[];
  body?: string;
}

export interface UpdateEntityRequest {
  owner?: Owner;
  title?: string;
  aliases?: string[];
  status?: string;
  confidence?: number;
  media_links?: MediaLinks;
  relationships?: Relationship[];
  sources?: string[];
  body?: string;
}

// P24 Phase 3 — schlanke Read-only-Projektion für Person/Asset-Detail (kein voller EntityDto-Roundtrip).
export interface EntityRefDto {
  id: string;
  title: string;
  type: string;
}

// P25 Phase 1 — Beziehung mit aufgelöstem Ziel (Titel/Typ statt roher id).
export interface ResolvedRelationshipDto {
  type: string;
  target: EntityRefDto;
}

// P25 Phase 1 — ein per media_links verknüpftes Person-/Asset-Bild samt fertigem Thumbnail.
export interface MediaRefDto {
  kind: 'person' | 'asset';
  id: number;
  thumbnail_url: string;
  label: string | null;
}

// P25 Phase 1 — Vollform der Lore-Aggregation. `entity` ist null, wenn Bild/Person
// keine verknüpfte Entity hat (Kontrakt: 200 statt 404).
export interface LoreDto {
  entity: EntityDto | null;
  relationships: ResolvedRelationshipDto[];
  franchises: EntityRefDto[];
  related_media: MediaRefDto[];
  sources: string[];
}

export interface EntityType {
  name: string;
  folder: string;
}

export interface DomainDto {
  name: string;
  entity_types: EntityType[];
  relationship_types: string[];
}

export const TASK_KINDS = ['new_person', 'missing_entity', 'confirm_relationship', 'review_recommendation', 'incomplete_entity'] as const;
export type TaskKind = typeof TASK_KINDS[number];

export const TASK_STATUSES = ['open', 'resolved', 'dismissed'] as const;
export type TaskStatus = typeof TASK_STATUSES[number];

export interface TaskDto {
  id: number;
  kind: TaskKind;
  status: TaskStatus;
  context: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
}

export interface CreateTaskRequest {
  kind: TaskKind;
  context?: Record<string, unknown>;
}

// P25 Phase 3 — „Das stimmt nicht"-Korrektur. `owner` ist bewusst kein Request-Feld
// (anders als UpdateEntityRequest): die Route ist fix die Nutzer-Korrektur (owner=user).
export interface PatchEntityRequest {
  field: string;
  value: unknown;
  reason: string;
}

export interface PatchJobResponse {
  job_id: string;
}

// P25 Phase 3 — Explainability-Eintrag einer Korrektur (geteilte Payload mit P26 Phase 3).
export interface ChangelogEntryDto {
  id: number;
  entity_id: string;
  field: string;
  old_value: unknown;
  new_value: unknown;
  reason: string;
  source: Owner;
  job_id: string;
  created_at: string;
}
