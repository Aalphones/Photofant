# Phase 5 — Doku & ADR-012

**Tier:** mechanisch
**Status:** complete

---

## Kontext (was vorher lesen)

- `docs/code-map.md` — Zeile „Galerie & Lightbox"
- `docs/models.md` — Sektionen `asset`, `version`, `face`
- `docs/routes.md` — `GET /api/assets`, `GET /api/faces`
- `docs/design-reconciliation.md` — falls Stapel-Verhalten dort als Gap geführt wurde
- Nächste freie ADR-Nummer: **ADR-012** (007 P11, 010 P18, 011 P20 reserviert — alle
  noch nicht auf Platte; 009 ist der letzte tatsächlich angelegte ADR)

---

## Abnahme-Kriterien

- [x] `docs/decisions/012-galerie-stapel-flache-einzeleintraege.md` angelegt
- [x] `docs/code-map.md`, `docs/models.md`, `docs/routes.md` spiegeln die neuen Felder/Endpunkte
- [ ] `STATE.md`-Backlog-Zeile für P21 auf „archiviert" bzw. entfernt (macht `mode-implementing`
  beim Archivieren, hier nur zur Erinnerung)

---

## Checkliste

- [x] ADR-012 schreiben (Kontext / Optionen / Entscheidung / Konsequenzen, ~10 Zeilen):
  ```markdown
  # ADR-012 — Galerie-Stapel: flache Einzeleinträge statt kollabiertem Stapel-Kopf

  ## Kontext
  Ein Original mit mehreren Edits soll in der Galerie sichtbar bleiben, wie viele
  Edits es hat und wann jedes einzelne entstand — nicht nur "es gibt ein neuestes Edit".

  ## Betrachtete Optionen
  - A: Flache Einzeleinträge — jede Version (Original + jedes Edit) ist ein eigener,
    gleichberechtigter Galerie-Eintrag an seiner eigenen chronologischen Stelle (gewählt)
  - B: Kollabierter Stapel-Kopf (nur neuestes Edit sichtbar, Original als zweiter
    Echo-Eintrag) — erste Fassung dieses Plans, vom User als zu wenig granular
    verworfen: bei 10 Edits will man 10 Einträge sehen, nicht 2
  - C: Client-seitige Gruppierung nach Fetch (verworfen — Sortierung/Pagination
    müsste dann clientseitig laufen, bricht bei großen Bibliotheken)

  ## Entscheidung
  Option A. `total`/`items` bleiben 1:1 zu physischen Objekten (Asset oder Version) —
  einfacher als Option B, weil keine Aggregation/Kollabier-Logik nötig ist. Jeder
  Eintrag trägt `stack_size`/`stack_group_id` fürs Icon, keine Zeitpunkt-Aggregation.

  ## Konsequenzen
  - `version`-Zeilen (bisher nur im separaten Edits-Tab sichtbar) erscheinen jetzt
    auch im Fotos-/Gesichter-Tab als Pseudo-Einträge (Query mischt zwei Quellen)
  - Bulk-Aktionen wirken pro Eintrag (Original, Version, `original_id`-Kind je einzeln),
    nicht pro Gruppe — kein Sonderfall für "doppelte Aktion auf demselben Asset"
  ```
- [x] `docs/code-map.md` Zeile „Galerie & Lightbox": Stapel-Logik erwähnt (kein Edits-Tab
  mehr, Entity-Key-Kompromiss, Query mischt asset+version)
- [x] `docs/models.md`: kein neues Feld/Index (stack_size/stack_group_id sind
  query-time-berechnet, keine Spalte) — dafür `version`-Sektion um Stapel-Semantik +
  den single-hop-Kompromiss ergänzt
- [x] `docs/routes.md`: `GET /api/assets` Response-Felder ergänzt; `GET /api/faces/gallery`
  (Gesichter-Tab-Endpunkt, war zuvor komplett undokumentiert) neu angelegt + Response-Felder

---

## Report-Back

**Abweichung vom Plan:** `GET /api/faces` aus der Abnahme-Kriterien-Formulierung existiert
nicht — der tatsächliche Endpunkt ist `GET /api/faces/gallery` und war vor dieser Phase
komplett undokumentiert (Vorbedingung, keine P21-Regression). Jetzt nachgetragen.

**Zusätzlich erledigt (aus FINDINGS.md, Phase 5 getaggt):**
- CSS-Budget-Fehler in `lightbox.scss` behoben — `anyComponentStyle`-Error-Budget in
  `frontend/angular.json` von 16 kB auf 32 kB angehoben (Warning 6→8 kB), einfachster Weg
  statt Datei-Split. `ng build --configuration production` verifiziert grün.
- Zwei bekannte, bewusst nicht in P21 behobene Lücken (Version-Favorit/-Löschen fehlt am
  Backend; toter `versionSlotBindings`-Verdrahtungsrest ohne UI-Einstiegspunkt seit
  Edits-Tab-Wegfall) als akzeptierte Konsequenzen in ADR-012 dokumentiert statt neu gebaut —
  beides wäre neuer Scope über P21 hinaus (Follow-ups, siehe Archiv-Footer der README).
