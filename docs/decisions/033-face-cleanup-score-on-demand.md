# 033 — Gesichts-Bereinigung: Score on-demand, kein neuer Cache, kein `review_item`

## Kontext

Personen haben mehrere Faces; einzelne davon passen manchmal nicht (falsch geclustert,
schlecht aufgelöst, hochskaliert) und sollen gezielt gelöscht werden können. Gebraucht wird
ein Score pro Face, der Identitäts-Abweichung (Distanz zum Personen-Centroid) und
Qualitätsprobleme (Auflösung, Detection-Score, Upscale-Flag) kombiniert.

## Betrachtete Optionen

1. **Neue Cache-Tabelle** (Muster `recommendation_cache`/`vec_asset_dino`) — Score vorab
   berechnen, in Job persistieren, Endpoint liest nur.
2. **Wiederverwendung von `review_item`** (Typ `face_suggestion` nutzt bereits Face+Score
   +Resolution-Konzepte) — neuer `type='face_quality'`.
3. **Stateless on-demand** — Score bei jedem Öffnen des Bereinigen-Dialogs live berechnen,
   keine Persistenz.

Option 2 scheitert an einer harten Constraint: `review_item.asset_a_id`/`asset_b_id` sind
`NOT NULL` FK → `asset.id`. Ein manuell importiertes, eigenständiges Face
(`face.asset_id IS NULL`, P7 Phase 6, `origin=manual_original`) hätte keinen Asset zum
Eintragen — entweder Constraint lockern (Risiko für die beiden bestehenden, eingespielten
Konsumenten Dupe-Scan + Face-Suggestion-Review) oder diese Faces stillschweigend von der
Bereinigung ausschließen. Beides unattraktiv.

Option 1 lohnt sich für teure GPU-Berechnungen (Embeddings, Duplikat-Scan). Hier ist die
Rechnung eine einzige SQL-Abfrage + Numpy-Centroid+Cosine über die Faces einer Person —
für eine lokale Single-User-App im Bereich weniger hundert Faces pro Person Sub-Millisekunden.
Eine Cache-Tabelle würde nur Invalidierungs-Aufwand (neues Face, gelöschtes Face, Merge/Split
ändern die Centroid-Basis) gegen keinen messbaren Performance-Gewinn eintauschen.

## Entscheidung

**Option 3 — stateless on-demand.** Neues Modul `clustering/cleanup.py::compute_person_cleanup_scores`
berechnet den Score bei jedem Aufruf frisch aus `Face`-Zeilen + der bestehenden
`compute_person_centroid()`. Kein neues DB-Schema, keine Migration, keine Job-/Rebuild-Logik.

**Score-Formel:**
- `identity_penalty` = Cosine-Distanz zum Personen-Centroid, normiert auf `1 - face_review_threshold`
  (derselbe Cutoff, den das Clustering für „gehört noch zur Person" nutzt) — `None`/`0` wenn die
  Person weniger als `face_cleanup_min_faces` Faces hat (Centroid aus 1-2 Faces ist keine
  aussagekräftige „typische" Referenz).
- `quality_penalty` = `max()` aus drei unabhängigen Signalen (niedrige Crop-Auflösung, niedriger
  Detection-Score, `is_upscaled`-Flag) — bewusst `max` statt gewichteter Summe: **ein** starkes
  Qualitätsproblem reicht zum Flaggen, es müssen sich keine drei schwachen addieren.
- `cleanup_score = clamp(identity_weight * identity_penalty + quality_weight * quality_penalty, 0, 1)`,
  Default-Gewichte `0.6`/`0.4` (Identität wiegt schwerer als Qualität — eine fremde Person mit
  gutem Foto ist schlimmer als die richtige Person mit schlechtem Foto).

Alle Schwellen/Gewichte sind Settings (`face_cleanup_*`), analog zum bestehenden
`face_auto_threshold`/`face_review_threshold`-Muster — bewusst **ohne** neue Einstellungen-UI-Slider
(Scope-Cut: Tuning-Konstanten, kein Nutzer-Flow; Präzedenzfall: `training_near_dupe_clip_threshold`
ist ebenfalls settings-only ohne UI).

## Konsequenzen

- Kein neues DB-Schema, keine Migration nötig — kleinster Blast-Radius.
- Score ist immer frisch (kein Invalidierungs-Bug möglich), Kehrseite: wird bei jedem
  Dialog-Öffnen neu gerechnet statt gecacht — für die erwartete Datengröße (Faces pro Person)
  irrelevant.
- `review_item` bleibt unangetastet — kein Risiko für Dupe-Scan/Face-Suggestion-Review.
- Löschen läuft über einen neuen Bulk-Endpoint (`POST /api/faces/bulk-delete`), der dieselbe
  Lösch-Logik wie das bestehende `DELETE /faces/{id}` nutzt, aber Smart-Album-Reevaluation pro
  betroffenem Asset bündelt statt pro Face zu triggern.
