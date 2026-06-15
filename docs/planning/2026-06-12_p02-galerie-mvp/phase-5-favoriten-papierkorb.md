# P2 · Phase 5 — Favoriten & Papierkorb

> Rating: **heikel** (physischer Move + DB müssen crash-sicher zusammenpassen — Kernmuster für P7) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (favourite/trash-Endpoints)
- [Konzept](../../Konzept-Photofant.md) §4.3 (aktive Moves), §13.4 (Papierkorb)
- [docs/conventions/testing.md](../../conventions/testing.md) — Critical Rule 3 (Moves testpflichtig)

## Akzeptanzkriterien

- Favorit setzen verschiebt die Datei `photos/` → `favourites/` (zurück beim Entfernen); DB-Pfad + `favourite`-Flag konsistent — auch bei Kollision (Namensgleichheit) und nach Crash zwischen Move und DB-Write.
- Soft-Delete: `deleted_at` gesetzt, Datei nach `.photofant/trash/` (Pfad-Erhaltung für Restore); Restore stellt Datei + DB her; endgültiges Löschen entfernt Datei + DB-Zeilen + Thumbnails.
- Move-Helfer ist **das** wiederverwendbare Modul (P7 nutzt es für Personen-Korrekturen): Reihenfolge Move-dann-DB mit Wiederanlauf-Logik (Reconciliation in P3 findet Drift).
- UI: Fav-Stern in Zelle + Lightbox (optimistisches Update mit Rollback), Papierkorb-View unter Einstellungen/Wartung vorerst als einfache Liste, `trash`-Slice.

## Checkliste

- [ ] Move-Modul im Backend (atomar so weit das FS es hergibt: gleicher Volume-Rename; Kollisions-Suffix; DB-Update in derselben Operation kapseln)
- [ ] Favourite-Endpoint + Trash-Endpoints (Liste/Restore/Endgültig) inkl. Thumbnail-Aufräumen
- [ ] Unit-Tests fürs Move-Modul (Erfolg, Kollision, Datei fehlt, simulierter Abbruch) — hier ausnahmsweise Pflicht trotz Lean-Profil, siehe testing.md
- [ ] Frontend: Fav-Toggle (Zelle hover + Lightbox), optimistisch mit Failure-Rollback-Action
- [ ] Papierkorb-Ansicht (Liste mit Restore/Löschen, Leeren-Button) + `store/trash/`
- [ ] Doc-Update: docs/models.md (deleted_at-Semantik), routes.md

## Report-Back
