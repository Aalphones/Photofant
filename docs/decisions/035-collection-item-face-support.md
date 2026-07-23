# ADR-035 — CollectionItem trägt Face-Crops als eigenständige Mitglieder

**Status:** Akzeptiert — 2026-07-23
**Querverweise:** `Version`-XOR-Pattern in `backend/photofant/db/models.py` (`ck_version_xor`,
Migration `0018`); [033](033-face-cleanup-score-on-demand.md) (`Face.is_upscaled`, das dieser
Plan erstmals setzt)

## Kontext

Die Gesichter-Galerie soll Mehrfachauswahl mit „Zu Trainingsset hinzufügen" bekommen. Trainingssets
(`Collection.kind == "training_set"`) waren bislang ausschließlich foto-basiert — `CollectionItem`
kennt nur `asset_id`. Ein Face kann aber auch ganz ohne Quell-Foto existieren (`asset_id IS NULL`,
`origin="manual_original"`, direkter Crop-Import) — ein Foto-Proxy („füge das Foto hinzu, zu dem
das Gesicht gehört") würde für diese Faces ins Leere laufen und würde außerdem das ganze Foto statt
nur des Crops zum Trainingsdatensatz machen, was der Absicht hinter einem Face-Trainingsset
widerspricht.

## Entscheidung

`collection_item` bekommt eine neue nullable `face_id`-Spalte (FK auf `face.id`), XOR mit
`asset_id` (analog zum bestehenden `Version`-Modell). Primärschlüssel wechselt von
`(collection_id, asset_id)` auf einen surrogaten `id`, Uniqueness pro Achse über zwei partielle
Unique-Indizes (Muster aus Migration `0027`: ein normaler Multi-Spalten-Unique-Constraint greift
bei NULL-Werten laut SQL-Standard nicht). Export, Stats und Trainingsset-Editor lernen, beide
Item-Typen zu lesen; Reorder und Near-Dupe-Review bleiben für v1 asset-only (kein Embedding pro
Face-Crop vorhanden, nicht angefragt).

Die Migration (`0042`) ist als manueller Tabellen-Neuaufbau umgesetzt (neue Tabelle → `INSERT
SELECT` → alte droppen → umbenennen), nicht als `batch_alter_table(recreate="always")` mit
`drop_constraint(type_="primary")`: SQLite speichert den PK-Constraint-Namen nicht, ein Drop per
Name wäre also unzuverlässig. Keine andere Tabelle referenziert `collection_item` per FK — der
Neuaufbau ist gefahrlos und wurde gegen eine Kopie der Dev-DB verifiziert (Daten erhalten, XOR-
und Unique-Constraints greifen, Downgrade + Re-Upgrade reversibel).

## Betrachtete Optionen

- **Foto-Proxy** (Face-Auswahl fügt das zugrundeliegende Asset hinzu) — kein Schema-Change,
  aber funktioniert nicht für Faces ohne Quell-Foto und würde ganze Fotos statt Crops in ein
  Face-Trainingsset einspeisen. Verworfen — widerspricht der Absicht hinter einem
  Crop-Trainingsset.
- **Separate `face_collection_item`-Tabelle** statt Erweiterung der bestehenden Tabelle — hätte
  Export/Stats/Editor gezwungen, zwei komplett getrennte Datenquellen zu unionen statt eine
  gemeinsame Query mit Typ-Diskriminator zu fahren. Verworfen — mehr Code-Verdopplung für
  denselben fachlichen Zweck („ein Trainingsset-Mitglied").

## Konsequenzen

- Jede Stelle, die bisher `CollectionItem.asset_id` als garantiert `NOT NULL` annahm, muss auf
  den XOR-Fall geprüft werden (Phase 2/3 dieses Plans deckt: add/remove/list/stats/export).
- Reorder und Near-Dupe-Review bleiben absichtlich asset-only in v1 — dokumentierte Lücke, kein
  Versehen (siehe Plan-README „Bewusst draußen").
- Die partiellen Unique-Indizes leben nur in der Migration, nicht im ORM-Model (`index=True`
  deckt nur die Plain-Indizes ab). Ein via `create_all` gebautes Schema — falls Tests das je tun —
  hätte die Uniqueness nicht; die laufende DB entsteht ausschließlich über Migrationen.
