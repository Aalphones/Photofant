# Phase 1 — Backend: Stapel-Datenmodell & Query (Fotos + Gesichter)

**Tier:** heikel
**Status:** pending

Voraussetzung für alle anderen Phasen.

---

## Kontext (was vorher lesen)

- `backend/photofant/api/assets.py` — `_base_query`, `list_assets` (Zeile ~267), `AssetDto`
  (Zeile ~56), `get_asset_thumbnail` (Zeile ~379)
- `backend/photofant/api/faces.py` — bestehende Face-Liste/Query
- `backend/photofant/db/models.py` — `Asset.original_id`, `Version` (XOR `instance_id`/`face_id`,
  `is_current`), `AssetInstance`
- `docs/models.md` — Sektionen `asset`, `asset_instance`, `version`, `face`
- README dieses Plans — Kontrakt-Sektion „Stapel" (Definition Gruppe, Dual-Listing-Regel)

---

## Abnahme-Kriterien

- [ ] `GET /api/assets` liefert pro Original mit Edit-Gruppe **1 oder 2** Einträge
  (Stapel-Kopf immer; Original-Echo nur wenn Original nicht selbst das neueste Mitglied ist)
  gemäß der Regel im README
- [ ] Jeder Eintrag hat `stack_size`, `list_role`, `effective_date`, `thumbnail_source_id`
- [ ] Sortierung nach Datum nutzt `effective_date`, nicht `asset.created_at`
- [ ] `GET /api/faces` liefert dieselbe Logik für Face-Edit-Gruppen (über `version.face_id`)
- [ ] Thumbnail-Auslieferung für einen Stapel-Kopf-Eintrag zeigt das Bild des neuesten
  Gruppenmitglieds, nicht das des Assets selbst
- [ ] Bestehende Filter (Person, Tags, Quelle, Favorit, Suche) funktionieren weiterhin korrekt
  auf den expandierten Einträgen (kein Filter verliert Treffer durch die Umstellung)
- [ ] Verifiziert: Verhalten bei Personen-Umhängung eines Edits (🟡 im README) — Befund dokumentiert,
  auch wenn kein Fix in dieser Phase nötig ist

---

## Checkliste

### Untersuchung zuerst

- [ ] Nachvollziehen, wie `Version.path` heute beim Anlegen gesetzt wird — folgt es dem
  Personen-Ordner der zugehörigen `Face`/`AssetInstance` zum Anlage-Zeitpunkt, und was passiert,
  wenn die Person danach wechselt? (Chesterton's Fence — Befund vor Änderung, nicht annehmen)
- [ ] Klären: kann eine Edit-Gruppe (Fotos) Mitglieder aus **beiden** Quellen gleichzeitig haben
  (mehrere `version`-Zeilen UND ein `original_id`-Kind)? Falls ja: `latest_activity_at` muss
  beide Quellen mergen, nicht nur eine

### Query-Umbau

- [ ] Gruppierungs-Hilfsfunktion: pro Asset alle Gruppenmitglieder ermitteln
  (`version`-Zeilen der zugehörigen `asset_instance` + Assets mit `original_id == asset.id`)
- [ ] `latest_activity_at` je Gruppe berechnen (SQL-Aggregation bevorzugt vor Python-Post-Processing,
  wegen Pagination — Performance im Blick behalten, siehe Critical Rule 5 „UI blockiert nie")
- [ ] `list_assets`: nach Filtern/Facetten die Dual-Listing-Expansion anwenden, dann paginieren
  (Reihenfolge wichtig: Filter zuerst auf Asset-Ebene, Expansion danach, sonst zählt `total` falsch)
- [ ] `AssetDto` um `stack_size`, `list_role`, `effective_date`, `thumbnail_source_id` erweitern
- [ ] `get_asset_thumbnail`: bei Stapel-Kopf-Eintrag `thumbnail_source_id` statt `asset_id` für
  Datei-Auflösung nutzen (Route bleibt `/assets/{id}/thumbnail`, Auflösung intern umgeleitet —
  🟡 oder braucht es einen eigenen Query-Parameter? Im Zweifel: Route-Parameter `version_id`
  optional ergänzen, Rückwärtskompatibilität für bestehende Aufrufer prüfen)

### Faces-Äquivalent

- [ ] `api/faces.py`: gleiche Gruppierung über `version.face_id`, gleiche vier neuen Felder
  auf `FaceGalleryItemDto`

### Performance

- [ ] Bei großen Bibliotheken (Tausende Assets): Index-Check auf `version.instance_id`,
  `version.face_id`, `asset.original_id` — vorhanden laut `docs/models.md`? Ergänzen falls nicht.

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
