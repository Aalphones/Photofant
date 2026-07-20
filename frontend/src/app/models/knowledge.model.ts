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

// P27 Phase 2 — KI-gestützte Wissenspflege. Autonomie-Stufe pro KI-Funktion (Konzept-ADR-008):
// `off` blendet die KI-Aktion aus, `ask`/`auto` bieten sie an.
export const AI_AUTONOMY_MODES = ['off', 'ask', 'auto'] as const;
export type AiAutonomyMode = typeof AI_AUTONOMY_MODES[number];

export interface AiAutonomyDto {
  knowledge_import: AiAutonomyMode;
  knowledge_update: AiAutonomyMode;
  interview: AiAutonomyMode;
}

// P27 Phase 2 — Anfrage für einen KI-Vorschlag (füllt die Wizard-Felder vor).
export interface ImportSuggestionRequest {
  title: string;
  domain: string;
  type: string;
  person_ids?: number[];
  asset_ids?: number[];
}

export interface ImportSuggestionResponse {
  job_id: string;
}

// P27 Phase 2 — Explainability eines KI-Vorschlags (Modell, Prompt-Version, Confidence, Grund).
export interface KnowledgeImportExplainability {
  model_id: string;
  capability: string;
  prompt_version: string | null;
  duration_ms: number;
  confidence: number | null;
  reason: string;
}

// P27 Phase 2 — der von Gemma vorgeschlagene Feld-Satz (nur bestätigungspflichtiger Vorschlag).
export interface KnowledgeImportSuggestion {
  title: string;
  type: string;
  domain: string;
  aliases: string[];
  relationships: Relationship[];
  body: string;
}

// P27 Phase 2 — Ergebnis des KnowledgeImportJob, über den Job-Stream geliefert. `suggestion`
// ist null, wenn der Validator den Vorschlag abgewiesen hat (`validation_errors` erklärt warum).
export interface KnowledgeImportResult {
  suggestion: KnowledgeImportSuggestion | null;
  explainability: KnowledgeImportExplainability;
  validation_errors: string[];
}

// P27 Phase 3 — Anfrage für einen KI-Ergänzungsvorschlag zu einer bestehenden Entity
// (Lore Panel „Ergänzen (KI)").
export interface UpdateSuggestionRequest {
  entity_id: string;
}

export interface UpdateSuggestionResponse {
  job_id: string;
}

// P27 Phase 3 — Explainability eines Ergänzungsvorschlags (gleiche Form wie der Import).
export interface KnowledgeUpdateExplainability {
  model_id: string;
  capability: string;
  prompt_version: string | null;
  duration_ms: number;
  confidence: number | null;
  reason: string;
}

// P27 Phase 3 — die vorgeschlagene Ergänzung. Nur `body` (FINDINGS Phase 2/3: ein rohes
// Text-LM liefert für Aliase/Beziehungen nichts Verlässliches — dieselbe Einschränkung wie
// beim Import-Vorschlag).
export interface KnowledgeUpdateProposal {
  body: string;
}

// P27 Phase 3 — Ergebnis des KnowledgeUpdateJob, über den Job-Stream geliefert. `proposal`
// ist null, wenn der Validator den Vorschlag abgewiesen hat (`validation_errors` erklärt
// warum); `old_body` liefert die Diff-Basis fürs Lore Panel.
export interface KnowledgeUpdateResult {
  proposal: KnowledgeUpdateProposal | null;
  old_body: string;
  explainability: KnowledgeUpdateExplainability;
  validation_errors: string[];
}

// P27 Phase 3 — Annahme eines Ergänzungsvorschlags. Schreibt über den P25-Patch-Pfad mit
// `owner=inferred` (serverseitig fixiert) — anders als `PatchEntityRequest`, das die
// manuelle Nutzer-Korrektur ist (`owner=user`, fest im Backend).
export interface AcceptUpdateSuggestionRequest {
  entity_id: string;
  body: string;
  reason: string;
}

export interface AcceptUpdateSuggestionResponse {
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
