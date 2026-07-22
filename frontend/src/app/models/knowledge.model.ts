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

// P38 Phase 2 — ein Merkmal (Geburtstag, Beruf, …) mit eigenem Owner. Der Owner sitzt
// bewusst pro Merkmal: ein selbst gepflegter Wert überlebt eine Web-Recherche.
export interface AttributeDto {
  value: string;
  owner: Owner;
  confidence: number;
}

// P38 Phase 2 — die für einen Entity-Typ vorgesehenen Merkmale (kommen aus der Domänen-Datei).
export interface EntityFieldDefDto {
  key: string;
  label: string;
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
  attributes: Record<string, AttributeDto>;
  // Anteil gefüllter Merkmale (0..1) — vom Backend berechnet, nie gespeichert.
  completeness: number;
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
  // P38 Phase 2 — Anteil gefüllter Merkmale (0..1), damit Personen-Karte und Übersicht
  // den Prozentwert ohne zweiten Request zeigen können.
  completeness: number;
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
  // P38 Phase 2 — welche Merkmale dieser Typ vorsieht. Leer ist gültig (Typ ohne Merkmale).
  fields: EntityFieldDefDto[];
}

export interface DomainDto {
  name: string;
  entity_types: EntityType[];
  relationship_types: string[];
  // P27 Phase 4 — private Domänen (reale Personen/Haustiere) laufen nie über den
  // Web-Import; sie entstehen über den Interview-Mode (Konzept-ADR-009).
  private: boolean;
}

export const TASK_KINDS = ['new_person', 'missing_entity', 'confirm_relationship', 'review_recommendation', 'incomplete_entity', 'missing_field', 'low_completeness', 'auto_link'] as const;
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
  // P38 Phase 4 — praktisch nur 'off'/'auto': die Bestätigung sitzt im Wizard (Fakten
  // abhaken), nicht in diesem Schalter (ADR-031).
  discovery: AiAutonomyMode;
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

// P27 Phase 4 — Interview-Mode für private Personen. Ein beantwortetes Frage-Paar aus dem
// geführten Dialog (kein freies Chat — festes Fragen-Skript im Wizard-Rahmen).
export interface InterviewAnswer {
  question: string;
  answer: string;
}

// P27 Phase 4 — synthetisiert aus den Interview-Antworten einen Entity-Vorschlag. `domain`
// muss privat sein (Backend-Guard). `person_ids`/`asset_ids` verknüpfen optional die
// bekannte Photofant-Person/-Aufnahme.
export interface InterviewSynthesizeRequest {
  title: string;
  domain: string;
  type: string;
  answers: InterviewAnswer[];
  person_ids?: number[];
  asset_ids?: number[];
}

export interface InterviewSynthesizeResponse {
  job_id: string;
}

// P27 Phase 4 — Explainability der Interview-Zusammenfassung (gleiche Form wie Import/Update).
export interface KnowledgeInterviewExplainability {
  model_id: string;
  capability: string;
  prompt_version: string | null;
  duration_ms: number;
  confidence: number | null;
  reason: string;
}

// P27 Phase 4 — der aus den Antworten synthetisierte Vorschlag (nur bestätigungspflichtig,
// wie der Import-Vorschlag). Aliase/Beziehungen bleiben leer — ein rohes Text-LM liefert
// dafür nichts Verlässliches (FINDINGS Phase 2/3).
export interface KnowledgeInterviewSuggestion {
  title: string;
  type: string;
  domain: string;
  aliases: string[];
  relationships: Relationship[];
  body: string;
}

// P27 Phase 4 — Ergebnis des InterviewJob, über den Job-Stream geliefert. `suggestion` ist
// null, wenn der Validator den Kandidaten abgewiesen hat (`validation_errors` erklärt warum).
export interface KnowledgeInterviewResult {
  suggestion: KnowledgeInterviewSuggestion | null;
  explainability: KnowledgeInterviewExplainability;
  validation_errors: string[];
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

// P38 Phase 4 — startet den KnowledgeDiscoveryJob. Das Ergebnis sind Vorschläge (ADR-031);
// geschrieben wird erst über DiscoveryApplyRequest.
export interface DiscoveryRequest {
  entity_id: string;
  // P38 Phase 7 — optionaler Hinweis aus dem Web-Suche-Wizard (Beruf, Stadt, Link …),
  // geht nur in die Suchanfrage ein, kein eigener Prompt-Slot.
  hint?: string;
}

export interface DiscoveryResponse {
  job_id: string;
}

// P38 Phase 4 — ein von Gemma vorgeschlagener Fakt (Job-Ergebnis, noch nicht geschrieben).
export interface KnowledgeDiscoveryFact {
  field: string; // Merkmals-Key aus der Domäne, oder 'body'
  label: string; // Anzeigename ('Beruf', 'Beschreibung')
  value: string;
  source: string; // Host der Quelle, z.B. 'linkedin.com'
  source_url: string;
  confidence: number;
}

// P38 Phase 4 — eine von Gemma vorgeschlagene neue Entity (z.B. eine gefundene Beziehung).
export interface KnowledgeDiscoveryEntitySuggestion {
  title: string;
  type: string;
  relationship_type: string;
  body: string;
}

// P38 Phase 4 — Explainability der Web-Recherche (gleiche Form wie Import/Update/Interview).
export interface KnowledgeDiscoveryExplainability {
  model_id: string;
  capability: string;
  prompt_version: string | null;
  duration_ms: number;
  confidence: number | null;
  reason: string;
}

// P38 Phase 4 — Ergebnis des KnowledgeDiscoveryJob, über den Job-Stream geliefert. Reine
// Vorschläge — nichts ist geschrieben, bis der User im Wizard Haken setzt.
export interface KnowledgeDiscoveryResult {
  facts: KnowledgeDiscoveryFact[];
  entity_suggestions: KnowledgeDiscoveryEntitySuggestion[];
  sources: string[];
  errors: string[];
  explainability: KnowledgeDiscoveryExplainability;
}

// P38 Phase 4 — bestätigte Auswahl aus dem Wizard (Haken gesetzt). Geschrieben wird nur,
// was hier ankommt, nicht der volle Job-Output.
export interface DiscoveryApplyRequest {
  entity_id: string;
  facts: KnowledgeDiscoveryFact[];
  entity_suggestions: KnowledgeDiscoveryEntitySuggestion[];
}

export interface DiscoveryApplyResponse {
  written_fields: string[];
  created_entities: EntityRefDto[];
  errors: string[];
}
