# Phase 4 — Lightbox-Anbindung: Klick-Ziel + Versions-Navigation

**Tier:** standard
**Status:** pending

Setzt Phase 2/3 voraus (Grid liefert `list_role`/`thumbnail_source_id`) sowie
P15 Phase 4 (Versionen-Sektion) und P15 Phase 7 (Gesichter-Modus) — diese Phase
verdrahtet nur den **Einstiegspunkt**, die Versionen-Navigation selbst kommt aus P15.

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/galerie.ts` — `onOpenAsset`/`onOpenFace`,
  `galleryActions.openFaceLightbox` (Zeile ~244)
- `frontend/src/app/store/gallery/gallery.effects.ts` — `openFaceLightbox$`
- P15 README — Kontrakt `versions: VersionDto[]`, `linked_edits`, `original_id`
- P15 `phase-7-gesichter-modus.md` — Face-Modus der Lightbox

---

## Abnahme-Kriterien

- [ ] Klick auf einen Stapel-Kopf-Eintrag (`list_role: 'stack_head'`) öffnet die Lightbox
  direkt auf dem neuesten Gruppenmitglied (`thumbnail_source_id`)
- [ ] Klick auf einen Original-Echo-Eintrag (`list_role: 'original_echo'`) öffnet die
  Lightbox auf dem Original selbst
- [ ] Aus beiden Einstiegen ist über die Versionen-Sektion (P15 Phase 4) dieselbe
  vollständige Gruppe navigierbar — kein Unterschied im Versionen-Inhalt je nach Einstieg
- [ ] Face-Stapel-Klick (Phase 3) öffnet die Lightbox im Face-Modus (P15 Phase 7) auf der
  neuesten Face-Version, nicht mehr pauschal auf dem umgebenden Asset
- [ ] Schließen der Lightbox kehrt zur Galerie an der ursprünglichen Scroll-Position zurück
  (bestehendes Verhalten — nicht regressen)

---

## Checkliste

- [ ] `onOpenAsset(event)` in `galerie.ts`: unterscheidet `list_role` und übergibt bei
  `stack_head` die `thumbnail_source_id` als Öffnungs-Ziel statt der Asset-ID
- [ ] `openFaceLightbox`-Action/Effect: analog für Face-Stapel — `faceId` + ggf.
  `versionId` der neuesten Face-Version durchreichen
- [ ] Deep-Link/URL-Zustand (falls Lightbox einen Query-Param für die offene Asset-ID
  führt) prüfen: zeigt er die Version-ID oder die Original-Asset-ID? Konsistenz mit
  Browser-Zurück/Teilen-Link sicherstellen
- [ ] Manuelles Durchklicken: Original öffnen → im Versionen-Bereich zum Edit wechseln →
  zurück zur Galerie → Original-Echo-Eintrag klicken → muss wieder beim Original landen
  (Regressions-Check, kein automatisierter Test nötig laut Profil, aber im Report-Back
  festhalten dass es geprüft wurde)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
