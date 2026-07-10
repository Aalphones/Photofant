// Recommendation Engine (P26): Empfehlungs-Karten unter dem Lore-Panel. Kombiniert
// CLIP-Bildähnlichkeit mit dem Wissensgraph (P22) zu Score + Begründungskette
// (Dok 050 §6). Rendert über die generische `related-rail/` (P36) — siehe deren
// Kopf-Kommentar für die geteilte {assetId, score, reasons}-Struktur.

export type RecommendationSignal = 'same_person' | 'same_role' | 'same_film' | 'clip';

export interface RecommendationReasonDto {
  signal: RecommendationSignal;
  detail: string;
  weight: number;
}

export interface RecommendationDto {
  asset_id: number;
  thumbnail_url: string;
  score: number;
  reasons: RecommendationReasonDto[];
}

export type RecommendationStatus = 'ready' | 'computing' | 'disabled';

export interface RecommendationsResponse {
  status: RecommendationStatus;
  recommendations: RecommendationDto[];
}

const SIGNAL_LABELS: Record<RecommendationSignal, string> = {
  same_person: 'gleiche Person',
  same_role: 'gleiche Rolle',
  same_film: 'gleicher Film',
  clip: 'CLIP-Ähnlichkeit',
};

// „✓ gleiche Person (Frodo Beutlin)" bzw. „✓ CLIP-Ähnlichkeit 0.94" (Dok 050 §6-Beispiel).
export function recommendationReasonLabel(reason: RecommendationReasonDto): string {
  const label = SIGNAL_LABELS[reason.signal] ?? reason.signal;
  return reason.signal === 'clip' ? `✓ ${label} ${reason.detail}` : `✓ ${label} (${reason.detail})`;
}
