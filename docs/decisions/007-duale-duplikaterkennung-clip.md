# ADR-007 — Duale Duplikaterkennung: DHash + CLIP parallel

**Status:** Ergänzt durch ADR-018 — DHash-Zweig entfernt, CLIP-Teil bleibt gültig
**Datum:** 2026-07-02
**Betrifft:** Plan `2026-06-22_p11-duale-duplikaterkennung`, ergänzt ADR-006

---

## Kontext

ADR-006 legte DHash als alleinige Ähnlichkeits-Metrik fest und schloss CLIP
explizit aus („zu weit — kein geeignetes Signal für Dateivarianten"). In der
Praxis zeigt sich aber eine zweite, eigene Fundgruppe: gleiche Szene, aber
andere Aufnahme oder deutliche Bearbeitung (z.B. Re-Crop mit anderem
Bildausschnitt, Farbfilter, Export in anderer Auflösung mit Zuschnitt) — DHash
reißt hier über die Distanz-Schwelle, weil sich der Pixel-Inhalt zu stark
ändert, obwohl es visuell dasselbe Motiv ist. CLIP-Embeddings liegen bereits
für die Suche vor (`asset.clip_embedding`, ADR-001) und können ohne
zusätzliches Modell für einen zweiten, semantischen Duplikat-Scan
wiederverwendet werden.

## Entscheidung

DHash und CLIP laufen **parallel**, nicht alternativ:

- **DHash bleibt Exact-Copy-Detector:** nur noch `phash_distance == 0`
  zählt als Treffer — kein Slider, nur ein An/Aus-Toggle
  (`dupe_phash_enabled`). Der bisherige `dupe_threshold`-Wert wird von
  Phase 2 an nicht mehr für den Scan gelesen (Altlast, kein Breaking Change).
- **CLIP erfasst semantische Ähnlichkeit** über eine konfigurierbare
  Cosine-Distance-Schwelle (`dupe_clip_threshold`, Default `0.15`,
  Range 0.05–0.30 ≙ 70–95 % Ähnlichkeit), an/aus per `dupe_clip_enabled`.
- **OR-Logik:** Ein Paar landet in der Review-Queue, wenn DHash **oder**
  CLIP anschlägt. Beide Scores werden getrennt gespeichert und im UI getrennt
  angezeigt (`triggered_by: "phash" | "clip" | "both"`).
- CLIP-Scan ignoriert Assets ohne `clip_embedding` stillschweigend (kein
  Fehler) — betrifft Altbestände, bei denen `auto_embed` früher aus war.

## Konsequenzen

- `review_item.phash_distance` wird nullable (NULL bei CLIP-only Treffern)
- `review_item.clip_distance` neu (Float, nullable, NULL bei DHash-only Treffern)
- Drei neue Settings: `dupe_phash_enabled`, `dupe_clip_enabled`,
  `dupe_clip_threshold`
- CLIP-Pairwise-Vergleich ist O(N²) — ab ~5 000 Assets muss der Scan in
  1 000er-Blöcken chunken (Phase 2)
- Frontend zeigt beide Methoden getrennt in Einstellungen und Review-UI
  (Phase 4/5)
