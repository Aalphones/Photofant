# FINDINGS — P36 Reverse Image Search

Erkenntnisse während der Umsetzung, getaggt nach Phase. Format:

- [ ] → Phase N: <Erkenntnis / Abweichung / Nachtrag>

- [ ] → Phase 1: **Es gibt bereits eine „Ähnliche Bilder"-Funktion in der Lightbox** —
  `GET /api/assets/{id}/similar` (`backend/photofant/api/review.py:226`), Teil der
  Duplikaterkennung. Sie zeigt Treffer **nur bis zu einem festen Schwellenwert**
  (`similar_clip_threshold`, aktuell 0.15 Cosine-Distanz) — kein Top-N, kann auch leer sein.
  P36 Phase 3 soll laut README eine *zweite* Related-Rail in derselben Lightbox bauen: fixe
  Top-10 über `/api/search/semantic?like_asset_id=`, unabhängig vom Schwellenwert, p26-kompatibel
  (`reasons`-Feld). Beide würden nebeneinander „Ähnliche Bilder" heißen, mit unterschiedlicher
  Trefferzahl und unterschiedlicher Logik — für den User verwirrend.
  **Vor Phase 3 klären:** ersetzt die neue Related-Rail `/api/assets/{id}/similar` komplett
  (Frontend auf `like_asset_id`-Pfad umstellen, alten Endpoint ggf. auf Sicht behalten/entfernen),
  oder bleiben beide nebeneinander bestehen (dann eindeutige Beschriftung nötig, damit klar ist,
  welche Liste was zeigt)?

  **Entschieden (2026-07-07):** Related-Rail ersetzt das Overlay komplett — Details/AK in
  `phase-3-lightbox-aehnliche.md` (Abschnitt „Entscheidung"). Der eigenständige Duplikat-Abgleich
  im Review-Tab (`/api/review/dupes`) ist davon nicht betroffen, nur der Lightbox-Klick-Shortcut
  entfällt.
