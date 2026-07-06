# ADR-018 — CLIP-only Duplikaterkennung, pHash entfernt

**Status:** Angenommen
**Datum:** 2026-07-06
**Betrifft:** Plan `2026-07-03_p33-phash-abloesung`, supersedes ADR-006, ergänzt ADR-007

---

## Kontext

pHash (DHash) trug vier Funktionen: Sofort-Dupe-Check beim Import, zweite Stimme im
Dupe-Scan (parallel zu CLIP, ADR-007), Trainingsset-Dupes/-Quote und Face-Crop-Dedupe
bei Edit-Versionen. In der Praxis lieferte DHash spürbar schlechtere Treffer als CLIP —
Anlass, den zweiten, schwächeren Vergleichsweg ganz zu streichen statt ihn weiter parallel
zu pflegen.

## Optionen

- **Behalten als Import-Tripwire:** DHash nur noch für den Sofort-Check beim Import, CLIP
  für alles andere. Verworfen — zwei Code-/Settings-Pfade für denselben Zweck, ohne
  Qualitätsgewinn gegenüber CLIP allein.
- **Komplett ersetzen (gewählt):** CLIP/Embeddings für alle vier Funktionen. Import-Check
  wandert hinter den Embedding-Job (Kandidat erscheint Sekunden später statt sofort);
  Face-Crop-Dedupe nutzt die ohnehin vorhandenen buffalo_l-Face-Embeddings.

## Entscheidung

CLIP-only. DHash fällt ersatzlos weg:

- Import-Dupe-Check läuft **nach** dem Embedding-Job per sqlite-vec-Suche.
- Dupe-Scan, Review-UI, Trainingsset-Dupes/-Quote: nur noch CLIP, kein `triggered_by`
  mehr.
- Face-Crop-Dedupe bei Edit-Versionen: Cosine auf Face-Embeddings statt Bild-Hash.
- Drei neue Settings: `dupe_search_limit`, `training_near_dupe_clip_threshold`,
  `face_dedupe_similarity_threshold`. `dupe_threshold` und `dupe_phash_enabled` entfernt.

## Konsequenzen

- Kein modellfreier Dupe-Pfad mehr — ohne CLIP (Teil des ONNX-Kerns) gibt es keine
  Duplikaterkennung. Akzeptiert, da CLIP ohnehin für Suche/Klassifizierung erforderlich ist.
- Kandidaten-Latenz beim Import = Laufzeit des Embedding-Jobs statt sofort.
- `asset.phash`, `face.phash`, `review_item.phash_distance` sowie die `imagehash`-Dependency
  entfernt (Migration 0031).

> Supersedes ADR-006. Ergänzt ADR-007 (DHash-Zweig entfernt, CLIP-Teil bleibt gültig).
