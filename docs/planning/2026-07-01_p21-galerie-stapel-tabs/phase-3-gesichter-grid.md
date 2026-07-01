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
- [ ] Ein Face mit Edit-Version zeigt den Stapel: Thumbnail = neueste Face-Version,
  Sortierdatum = deren `created_at`
- [ ] Das Original-Face erscheint zusätzlich separat an seiner eigenen Stelle (gleiche Regel
  wie bei Fotos: nur wenn nicht selbst das neueste Mitglied)
- [ ] Wurde das Face zwischenzeitlich einer anderen Person zugewiesen, zeigt die Personensuche
  beide Personen an der jeweils korrekten Stelle (Original bei alter Person, falls dort
  physisch verblieben; Edit bei neuer Person — abhängig vom Phase-1-Befund zur Umhängung)

---

## Checkliste

- [ ] `FaceGalleryItemDto` um die vier Stapel-Felder ergänzen (Typen wie in Phase 2)
- [ ] `face-cell.ts`/`.html`: Stapel-Badge analog zu `cell` (Phase 2) einbauen — gleiche
  SCSS-Klasse wiederverwenden statt duplizieren
- [ ] Sortierung im Face-Grid folgt `effective_date`
- [ ] Klick-Verhalten (`openFace`/`onOpenFace`) bleibt erhalten, liefert aber jetzt bei
  Stapel-Kopf die neueste Face-Version als Ziel (siehe Phase 4 für Lightbox-Seite)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
