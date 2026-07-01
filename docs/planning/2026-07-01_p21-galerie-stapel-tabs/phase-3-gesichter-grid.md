# Phase 3 — Frontend Gesichter-Grid: Stapel-Äquivalent

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (Faces-Äquivalent der Stapel-Felder). Spiegelt Phase 2, aber
für `features/galerie/face-grid/` statt `grid/`.

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/face-grid/`, `face-cell/`
- `frontend/src/app/models/asset.model.ts` — `FaceGalleryItemDto`
- Phase 2 dieses Plans — gleiches Icon/gleiche SCSS-Klasse wiederverwenden, nicht neu erfinden

---

## Abnahme-Kriterien

- [ ] Face-Zelle zeigt dasselbe Stapel-Icon wie Foto-Zelle (Phase 2), wenn `stack_size > 1`
- [ ] Ein Face mit Edit-Version(en) zeigt **jede** Version als eigene Kachel (nicht nur
  die neueste) — Original-Face + jede Face-Version einzeln, je mit eigenem Datum
- [ ] Wurde eine Face-Version zwischenzeitlich einer anderen Person zugewiesen, zeigt die
  Personensuche jede Kachel bei der Person, zu der sie aktuell physisch gehört (Original
  ggf. bei alter Person, Edit bei neuer — abhängig vom Phase-1-Befund zur Umhängung)

---

## Checkliste

- [ ] `FaceGalleryItemDto` um `stack_size: number`, `stack_group_id: number | null` ergänzen
  (Typen wie in Phase 2; Faces haben kein `kind`-Unterscheidungsfeld nötig, da alle
  Face-Versionen über `version.face_id` laufen — kein `original_id`-Äquivalent für Faces)
- [ ] `face-cell.ts`/`.html`: Stapel-Badge analog zu `cell` (Phase 2) einbauen — gleiche
  SCSS-Klasse wiederverwenden statt duplizieren
- [ ] Sortierung im Face-Grid folgt dem eigenen Datum jedes Eintrags
- [ ] Klick-Verhalten (`openFace`/`onOpenFace`) bleibt erhalten, liefert aber jetzt bei
  einem Version-Eintrag dessen `version_id` mit (siehe Phase 4 für Lightbox-Seite)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
