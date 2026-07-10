// Explainability-Payload (P26 Phase 3) — geteilte Struktur für „Warum?"/„Warum nicht?" an
// Empfehlungs-Karten UND für die P25-Korrektur-Historie (Lore-Panel). Ein Popover-Bauteil
// (`ui/explainability-popover/`) rendert beides — kein zweites Implementat (AK P26 Phase 3).
// Absichtlich schon fertig formatierte Strings statt Rohdaten (signal/weight etc.): die
// beiden Aufrufer (Recommendation-Reasons, Changelog-Eintrag) haben zu unterschiedliche
// Rohformen, als dass ein gemeinsamer Formatter hier lohnen würde — sie bauen das Payload
// selbst und übergeben nur das Anzeige-Fertige.

export interface ExplainabilityMetaEntry {
  label: string;
  value: string;
}

export interface ExplainabilityPayload {
  title: string;
  confidencePercent: number | null;
  reasons: string[];
  missing: string[];
  meta: ExplainabilityMetaEntry[];
}
