// Semantische / Reverse-Image-Suche (P36). Die API-DTOs spiegeln die Response von
// `POST /api/search/by-image` bzw. `POST /api/search/semantic` (snake_case wie das Backend).

export interface SearchHit {
  asset_id: number;
  score: number;
}

export interface SemanticSearchResponse {
  hits: SearchHit[];
}

// Frontend-UI-State des Reverse-Image-Filters: das eingebettete Quell-Bild wird nie
// importiert — wir halten nur ein kleines Vorschau-Thumbnail (Data-URL) für den Chip
// und die nach Ähnlichkeit geordnete Trefferliste, die die Galerie als Filter lädt.
export interface ReverseSearchState {
  thumbnailDataUrl: string;
  similarIds: number[];
}
