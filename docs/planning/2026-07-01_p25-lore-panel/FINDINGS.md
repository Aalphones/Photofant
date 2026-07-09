# FINDINGS — P25 Lore Panel

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

- [x] → Phase 2: `franchises[]` (aus `get_lore`) enthält Ziele **zusätzlich** zu `relationships[]`
  (keine Deduplizierung im Backend) — beim Rendern der „Beziehungen"-Sektion Franchise-Ziele
  (Ziel-Typ `"Franchise"`) selbst rausfiltern, sonst erscheinen sie doppelt (einmal in
  „Beziehungen", einmal in „Franchises").
  → Eingearbeitet: `relationships`-computed filtert Ziele raus, deren `id` in `franchises[]`
  steht — domänen-agnostisch über die ids statt über den Typ-String „Franchise".
- [x] → Phase 2: `related_media[]` lässt Personen ohne Gesichts-Portrait aus (kein Eintrag,
  nicht mit leerem Thumbnail) — eine verknüpfte Person kann also unsichtbar in „Eigene Bilder"
  bleiben, wenn sie noch keine erkannten Gesichter hat. Kein Fehlerzustand, aber beim Testen
  „Verknüpfung da, Bild fehlt trotzdem" nicht als Bug werten, ohne das zu prüfen.
  → Berücksichtigt: „Eigene Bilder" rendert nur vorhandene Media-Refs; keine Platzhalter für
  portraitlose Personen. (Nebenbei entdeckt + gefixt: Personen-Thumbnail-URL im Backend war
  `/faces/…` statt `/api/faces/…` — hätte auch vorhandene Portraits nicht geladen.)
- [x] → Phase 2: Beziehungsziele, die (noch) keine eigene Entity im Cache haben, kommen mit
  `target.type == ""` und `target.title == <rohe id>` zurück (Fallback statt Fehler) — beim
  Klick-Handling/„Ziel-Entity" (AK Phase 2) diesen Fall abfangen (kein Navigationsziel, oder
  zumindest kein Crash bei leerem Typ).
  → Eingearbeitet: `isNavigable(ref) = ref.type !== ''`; nicht-navigierbare Ziele werden als
  `disabled`-Buttons ohne Klick-/Hover-Ziel gerendert.
