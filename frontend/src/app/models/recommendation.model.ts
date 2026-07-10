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

// „Warum nicht?" (P26 Phase 3) — live berechnet, nur auf Anfrage (Risiko: teuer, siehe README).
// `missing` nennt fehlende Signale mit `detail: ''` (nichts vorhanden) und `weight` = was das
// Signal wert gewesen wäre, hätte es gegriffen.
export interface WhyNotResponse {
  source_asset_id: number;
  target_asset_id: number;
  score: number;
  threshold: number;
  recommended: boolean;
  reasons: RecommendationReasonDto[];
  missing: RecommendationReasonDto[];
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

// „✗ gleiche Rolle (fehlt)" — Gegenstück für die `missing`-Liste im „Warum nicht?"-Popover.
export function recommendationMissingLabel(reason: RecommendationReasonDto): string {
  const label = SIGNAL_LABELS[reason.signal] ?? reason.signal;
  return `✗ ${label} (fehlt)`;
}
