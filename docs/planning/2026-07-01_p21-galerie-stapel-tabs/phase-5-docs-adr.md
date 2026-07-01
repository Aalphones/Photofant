# Phase 5 — Doku & ADR-012

**Tier:** mechanisch
**Status:** pending

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

- [ ] `docs/decisions/012-galerie-stapel-dual-listing.md` angelegt
- [ ] `docs/code-map.md`, `docs/models.md`, `docs/routes.md` spiegeln die neuen Felder/Endpunkte
- [ ] `STATE.md`-Backlog-Zeile für P21 auf „archiviert" bzw. entfernt (macht `mode-implementing`
  beim Archivieren, hier nur zur Erinnerung)

---

## Checkliste

- [ ] ADR-012 schreiben (Kontext / Optionen / Entscheidung / Konsequenzen, ~10 Zeilen):
  ```markdown
  # ADR-012 — Galerie-Stapel: Dual-Listing statt reiner Stapel-Kopf

  ## Kontext
  Originale mit Edits sollen sowohl an ihrer eigenen chronologischen Stelle als auch
  nach vorne (Datum des neuesten Edits) sichtbar sein — eine reine "nur Stapel-Kopf"-
  Darstellung würde das Original in der Zeitleiste verschwinden lassen.

  ## Betrachtete Optionen
  - A: Dual-Listing — Original bekommt bei Bedarf einen zweiten Galerie-Eintrag (gewählt)
  - B: Nur Stapel-Kopf, Original nur über Versionen-Navigation erreichbar (einfacher,
    aber Original ist an seiner Zeitstelle unsichtbar — vom User explizit abgelehnt)
  - C: Client-seitige Duplizierung nach Fetch (verworfen — bricht Server-seitige
    Pagination/Facetten)

  ## Entscheidung
  Option A. `total`/`items` zählen Einträge nach Expansion, nicht Assets 1:1.

  ## Konsequenzen
  - Pagination zählt Einträge, nicht Assets — Kommentar im Code, damit niemand die
    Prämisse "1 Asset = 1 Zeile" später stillschweigend wiederherstellt
  - Bulk-Aktionen müssen Dual-Listing-Einträge auf dieselbe Asset-ID zurückführen
    (siehe Phase 2 Checkliste)
  ```
- [ ] `docs/code-map.md` Zeile „Galerie & Lightbox": Stapel-Logik erwähnen, falls die
  Query-Grobstruktur sich änderte (z.B. neue Hilfsfunktion/Modul)
- [ ] `docs/models.md`: falls Phase 1 einen neuen Index oder ein neues Feld ergänzt hat,
  hier nachziehen (Grobheits-Regel: Ordner-/Feld-Ebene, keine Zeilennummern)
- [ ] `docs/routes.md`: `GET /api/assets` und `GET /api/faces` Response-Felder ergänzen

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
