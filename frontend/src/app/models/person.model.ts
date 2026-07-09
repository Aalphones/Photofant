import type { EntityRefDto } from './knowledge.model';

export interface PersonDto {
  id: number;
  name: string | null;
  is_unknown: boolean;
  count: number;
  fav_count: number;
  portrait_face_id: number | null;
  group_name: string | null;
  created_at: string | null;
  // P24 Phase 3 — verknüpfte Wissens-Entity (read-only Cache-Projektion, vom Backend seit Phase 1 befüllt).
  linked_entity: EntityRefDto | null;
}

export interface PersonFace {
  id: number;
  asset_id: number | null;
  crop_url: string;
  score: number | null;
  age: number | null;
}

export interface FaceMatch {
  person_id: number;
  person_name: string | null;
  best_face_id: number;
  score: number;
}

export interface PersonDupePair {
  asset_a_id: number;
  asset_b_id: number;
  asset_a_content_hash: string;
  asset_b_content_hash: string;
  clip_distance: number;
  clip_similarity_pct: number;
  similarity_pct: number;
}

export interface FaceImportResult {
  face_id: number;
  person_id: number | null;
  has_embedding: boolean;
}

export interface PersonImportResponse {
  job_id: string;
}

export interface ClusterResult {
  job_id: string;
}
