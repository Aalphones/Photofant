# Phase 4 — Lightbox-Anbindung: Klick-Ziel + Versions-Navigation

**Tier:** standard
**Status:** pending

Setzt Phase 2/3 voraus (Grid liefert `kind`/`version_id`) sowie P15 Phase 4
(Versionen-Sektion) und P15 Phase 7 (Gesichter-Modus) — diese Phase verdrahtet nur
den **Einstiegspunkt**, die Versionen-Navigation selbst kommt aus P15.

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/galerie.ts` — `onOpenAsset`/`onOpenFace`,
  `galleryActions.openFaceLightbox` (Zeile ~244)
- `frontend/src/app/store/gallery/gallery.effects.ts` — `openFaceLightbox$`
- P15 README — Kontrakt `versions: VersionDto[]`, `linked_edits`, `original_id`
- P15 `phase-7-gesichter-modus.md` — Face-Modus der Lightbox

---

## Abnahme-Kriterien

- [ ] Klick auf eine Kachel mit `kind: 'asset'` öffnet die Lightbox auf diesem Asset
  (heutiges Verhalten, unverändert)
- [ ] Klick auf eine Kachel mit `kind: 'version'` öffnet die Lightbox auf dem
  zugehörigen Original-Asset, aber mit dieser Version **initial als Stage-Bild
  ausgewählt** (nicht `is_current` in der DB ändern — nur die initiale Anzeige-Auswahl,
  analog zum Panel-Selektor aus P15 Phase 4)
- [ ] Aus jedem Einstieg ist über die Versionen-Sektion (P15 Phase 4) dieselbe
  vollständige Gruppe navigierbar — kein Unterschied im Versionen-Inhalt je nach Einstieg
- [ ] Face-Stapel-Klick (Phase 3) öffnet die Lightbox im Face-Modus (P15 Phase 7); bei
  `kind: 'version'` mit dieser Face-Version initial ausgewählt
- [ ] Schließen der Lightbox kehrt zur Galerie an der ursprünglichen Scroll-Position zurück
  (bestehendes Verhalten — nicht regressen)

---

## Checkliste

- [ ] `onOpenAsset(event)` in `galerie.ts`: übergibt bei `kind === 'version'` zusätzlich
  die `version_id` als initiale Stage-Auswahl, sonst unverändert
- [ ] `openFaceLightbox`-Action/Effect: analog für Face-Versionen — `faceId` + optionale
  `versionId` durchreichen
- [ ] Deep-Link/URL-Zustand (falls Lightbox einen Query-Param für die offene Asset-ID
  führt) prüfen: braucht es einen zusätzlichen `version`-Query-Param für Konsistenz mit
  Browser-Zurück/Teilen-Link?
- [ ] Manuelles Durchklicken: eine Version-Kachel öffnen → prüfen dass Stage-Bild diese
  Version zeigt, nicht das Original → im Versionen-Bereich zu anderen Mitgliedern
  wechseln → zurück zur Galerie klicken → Original-Kachel öffnen → muss beim Original
  landen (Regressions-Check, kein automatisierter Test nötig laut Profil, aber im
  Report-Back festhalten dass es geprüft wurde)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
