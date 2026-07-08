/**
 * Backend liefert strukturierte Fehler als `{ detail: { code, message } }` (deutsche Klartext-
 * Meldung, z. B. `SEMANTIC_SEARCH_UNAVAILABLE`) oder als reinen String — beides auf eine
 * anzeigbare deutsche Meldung reduzieren. Geteilt zwischen Reverse-/Semantik-Suche
 * (search-box, gallery.effects, Lightbox-Related-Rail), die alle denselben Fehler-Shape sehen.
 */
export function extractApiErrorMessage(error: unknown, fallback: string): string {
  const detail: unknown = (error as { error?: { detail?: unknown } } | null)?.error?.detail;
  if (detail != null && typeof detail === 'object' && 'message' in detail) {
    const message: unknown = (detail as { message?: unknown }).message;
    if (typeof message === 'string') { return message; }
  }
  if (typeof detail === 'string') { return detail; }
  return fallback;
}
