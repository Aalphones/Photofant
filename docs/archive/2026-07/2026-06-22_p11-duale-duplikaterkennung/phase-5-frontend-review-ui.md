# Phase 5 — Frontend-Review-UI

**Tier:** standard  
**Status:** complete

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/review/review-dupes/dupe-pair-row/dupe-pair-row.ts` + `.html` + `.scss`
- `frontend/src/app/features/review/review-dupes/dupe-compare/dupe-compare.ts` + `.html` + `.scss`
- `frontend/src/app/features/personen/dupe-check-dialog/dupe-check-dialog.html`
- `@photofant/models` — `PersonDupePair`-Interface (wo definiert?)
- `frontend/src/app/models/` — Frontend-seitige DTOs für Review-Items prüfen
- Kontrakt-Sektion in README — `PersonDupePair` und `DupePairResponse`-Typen
- Phase 3 + 4 müssen abgeschlossen sein

---

## Abnahme-Kriterien

- [x] `dupe-pair-row` zeigt bei einem Paar, das nur per CLIP gefunden wurde, „CLIP: 87 % ähnlich" — und kein DHash-Balken
- [x] `dupe-pair-row` zeigt bei einem Paar, das von beiden erkannt wurde, beide Scores untereinander
- [x] `dupe-compare` (Lightbox-Modal) zeigt in der Kopfzeile den höchsten Score und darunter eine Zeile pro Methode die getriggert hat
- [x] `dupe-check-dialog` (Person-Duplikate) zeigt analog beide Scores pro Paar
- [x] Labels erklären die Methode ohne Fachbegriff: „Pixel-Ähnlichkeit" statt „DHash", „Inhalts-Ähnlichkeit" statt „CLIP"
- [x] Frontend-Typen `PersonDupePair` und das Review-DTO sind mit dem API-Kontrakt aus Phase 3 synchron
- [x] Fehlende Scores (null) werden nicht als „0 %" dargestellt — sie werden ausgeblendet

---

## Checkliste

### Modell-Typen aktualisieren

- [x] `PersonDupePair` (in `@photofant/models`) erweitert
- [x] Review-DTO (`DupePair` in `frontend/src/app/models/review.model.ts`) analog erweitert
- [x] `similarity_pct` bleibt bei `PersonDupePair` als vom Backend vorberechneter Max-Wert bestehen (kein Frontend-seitiges Nachrechnen nötig)

### dupe-pair-row

- [x] Scores-Block ersetzt — bedingte Blöcke statt einer Ähnlichkeits-Zeile (Klassen an bestehende `dupe-pair__`-BEM-Konvention angepasst statt `dupe-pair-row__`, siehe Deviations)
- [x] SCSS — kompakte Label/Value-Zeilen mit High/Mid/Low-Farbcodierung

### dupe-compare

- [x] Kopfzeile: Hauptzahl = `max(phash_similarity_pct, clip_similarity_pct)`
- [x] Subtitle-Zeile „Pixel: 94% · Inhalt: 88%" (nur aktive Methoden)
- [x] `similarity()` Signal auf `max(...)` angepasst

### dupe-check-dialog

- [x] Score-Block pro Paar analog `dupe-pair-row` (beide Methoden, konditionell) ergänzt
- [x] Prozentzahl-Balken zeigt weiterhin höchsten Score (Backend liefert `similarity_pct` bereits als Max — keine Änderung nötig)

---

## Report-Back

**Zusätzlich zum Kontext-File angefasst** (nicht in der ursprünglichen Kontext-Liste, aber nötig für Kompilierbarkeit/AK):
- `frontend/src/app/models/asset.model.ts` — `SimilarAsset` erweitert (`phash_distance` nullable, `clip_distance`/`clip_similarity_pct` neu), da `/assets/{id}/similar` (Backend `SimilarAssetDto`) dieselbe duale Struktur zurückgibt.
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` + `.html` — Lightbox-„Ähnliche Bilder"-Overlay baute bisher ein `DupePair` nur aus `phash_distance` zusammen (kompiliert nach der Typ-Erweiterung nicht mehr) und zeigte im Badge nur den DHash-Score. Jetzt: Badge zeigt `max(phash, clip)`, `dupe-compare`-Pair bekommt alle neuen Felder inkl. `triggered_by`. Damit erfüllt auch die Lightbox die finale AK „nutzt beide Methoden".
- `frontend/src/app/store/review/review.reducer.ts` — `sortComparer` sortierte direkt über `phash_distance` (jetzt nullable → Compile-Fehler). Ersetzt durch normalisierte Distanz (pHash 0–64 auf 0–1 skaliert, `Math.min` über verfügbare Methoden), spiegelt die gleiche Normalisierung, die das Backend in `review.py::_best_score` für die Similar-Sortierung nutzt.

**Deviations:**
- BEM-Klassennamen im Score-Block sind `dupe-pair__score(-label|-value)` statt der im Plan skizzierten `dupe-pair-row__…` — folgt der im File bereits etablierten Konvention (Block-Name `dupe-pair`, nicht `dupe-pair-row`).
- Kein Fortschritts-Balken mehr in `dupe-pair-row` (nur Label+Wert je Zeile) — im Plan-Snippet auch so vorgesehen, ersetzt den alten Single-Bar-Look.

**Bekannter, bewusst nicht behobener Rand-Fall (Follow-up):**
- `lightbox.ts::openSimilarOverlay()` blockt den „Ähnliche Bilder"-Button weiterhin über `asset.has_phash` — ein Asset ganz ohne pHash aber mit CLIP-Embedding kann den Button aktuell nicht öffnen, obwohl das Backend dafür CLIP-Treffer liefern würde. Ursache: `AssetDto` hat kein `has_clip_embedding`-Feld, das wäre eine Kontrakt-Erweiterung außerhalb dieser reinen Frontend-Phase. Nicht Teil der Phase-5-AK, daher unangetastet gelassen.
