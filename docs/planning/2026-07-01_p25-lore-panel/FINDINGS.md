# FINDINGS — P25 Lore Panel

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

- [ ] → Phase 2: `franchises[]` (aus `get_lore`) enthält Ziele **zusätzlich** zu `relationships[]`
  (keine Deduplizierung im Backend) — beim Rendern der „Beziehungen"-Sektion Franchise-Ziele
  (Ziel-Typ `"Franchise"`) selbst rausfiltern, sonst erscheinen sie doppelt (einmal in
  „Beziehungen", einmal in „Franchises").
- [ ] → Phase 2: `related_media[]` lässt Personen ohne Gesichts-Portrait aus (kein Eintrag,
  nicht mit leerem Thumbnail) — eine verknüpfte Person kann also unsichtbar in „Eigene Bilder"
  bleiben, wenn sie noch keine erkannten Gesichter hat. Kein Fehlerzustand, aber beim Testen
  „Verknüpfung da, Bild fehlt trotzdem" nicht als Bug werten, ohne das zu prüfen.
- [ ] → Phase 2: Beziehungsziele, die (noch) keine eigene Entity im Cache haben, kommen mit
  `target.type == ""` und `target.title == <rohe id>` zurück (Fallback statt Fehler) — beim
  Klick-Handling/„Ziel-Entity" (AK Phase 2) diesen Fall abfangen (kein Navigationsziel, oder
  zumindest kein Crash bei leerem Typ).
