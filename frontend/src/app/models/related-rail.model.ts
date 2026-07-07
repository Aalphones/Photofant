// Related-Rail (P36): generische Kartenliste für die Lightbox-Sektion „Ähnliche Bilder".
// P36 füllt `reasons = null` (rein visuelle Ähnlichkeit über den Bild-Embedder). P26
// (Recommendation Engine) rendert später dieselbe Rail mit befüllter Begründungskette —
// die Struktur bricht dabei nicht.

export interface Reason {
  label: string;
}

export interface RelatedRailItem {
  assetId: number;
  score: number;
  reasons: Reason[] | null;
}
