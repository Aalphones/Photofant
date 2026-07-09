# Phase 1 — Lore-Aggregations-API (Backend)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Kontrakt (`get_lore` voll, REST, Payload) · **P22** (Stub, Repos) · **P24** (media_links)
- Bestand: `api/knowledge.py`, `api/assets.py`, `api/persons.py`, `db/`-Repos

## AK
- [x] `get_lore(id)` liefert Entity + Relationships mit **aufgelösten** Zielen (Titel + Typ) + verwandte Medien (media_links) + Quellen + Franchises.
- [x] `GET .../lore?asset_id=` / `?person_id=` liefern die Payload; ohne Verknüpfung → 200 mit `entity: null` (kein 404).
- [x] „Verwandte Entities" = 1 Hop über Relationships, keine abgeleiteten Beziehungen doppelt (Dok 020 §6).
- [x] Read-only, keine KI, kein Netzwerk.

## Umsetzung
- [x] `get_lore` vom Stub zur Vollform (Relationship-Auflösung, Medien-Join)
- [x] Lore-Route in `api/knowledge.py` + Pydantic-Response-Schema
- [x] Doc: `docs/routes.md`, `docs/code-map.md`

## Umsetzungs-Entscheidungen (nicht im Plan-Text fixiert)

- **`franchises[]`** ist eine Teilmenge von `relationships[]`, gefiltert auf Ziel-Typ
  `"Franchise"` (String-Vergleich gegen den domänen-eigenen Entity-Typnamen, wie er in
  `movies.yaml` steht — kein hartcodiertes Engine-Wissen, sondern dieselbe Kopplung, die
  das Lore-Panel selbst hat: Dok 050 §5 zeigt „Franchises" immer als fixe Sektion).
  Franchise-Ziele bleiben zusätzlich auch in `relationships[]` (keine Deduplizierung) —
  Phase 2 entscheidet, ob/wie sie dort ausgeblendet werden.
- **Alte Route behalten:** `GET /entities/{id}/lore` (entity-id-basiert, 404 bei unbekannter
  id) wurde nicht entfernt, sondern nur auf die neue `LoreDto`-Vollform gehoben — sie war
  bereits getestet und nicht Teil des Kontrakts, den P25 ändern sollte (Chesterton).
- **`related_media[]`-Join:** Personen ohne Portrait (keine Gesichts-Aufnahme mit Score)
  werden **ausgelassen**, nicht mit leerem Thumbnail zurückgegeben — vermeidet kaputte
  Bilder im Panel. Betrifft ggf. den „Eigene Bilder leer trotz Verknüpfung"-Fall.
