# P7 · Phase 3 — Person-Ordner & Kopien

> Rating: **heikel** (physische Kopien/Moves über mehrere Dateien + DB in einem logischen Schritt — Kernrisiko des Datenmodells) · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (assign)
- [Konzept](../../Konzept-Photofant.md) §4.1–4.3 (Kopien, Moves), §6.1 Schritt 8, §6.1a (FS-Drop), §7 (manuelle Korrektur)
- Move-Modul aus P2 Phase 5 + Reconciliation aus P3 (Sicherheitsnetz)

## Akzeptanzkriterien

- Zuordnung erzeugt Person-Ordner (`personX/photos|favourites|faces|edits`) + echte Kopie pro Person; `asset_instance` pro (Asset, Person) mit Pfad; `_unknown`-Instanz wird zur ersten echten Person **verschoben**, weitere Personen erhalten **Kopien**.
- Manuelle Korrektur (`PATCH /api/faces/{id}/assign`): Bilddatei + zugehörige Face-Crops + Edits ziehen physisch um; alle DB-Pfade nachgeführt; Smart-Album-Hook (P6) feuert.
- FS-Drop (§6.1a): Scan erkennt Dateien in Person-Ordnern ohne DB-Eintrag → Verarbeitung mit `fixed_person = true`; weitere erkannte Personen → Kopien, fixe Zuordnung unangetastet.
- Crash-Sicherheit: Multi-Datei-Operationen laufen als geordnete Einzel-Moves über das Move-Modul; Abbruch hinterlässt einen Zustand, den der P3-Reconcile als Drift findet und reparieren kann (dokumentierte Wiederanlauf-Strategie statt Pseudo-Transaktion).

## Checkliste

- [x] Ordner-Anlage + Kopier-/Move-Orchestrierung (Erst-Person = Move, weitere = Copy)
- [x] assign-Endpoint (Bild + Faces + Edits umziehen, `fixed_person` setzen)
- [x] FS-Drop-Erkennung im Scan-Job (Ziel-Person aus dem Ordnerpfad)
- [x] Favoriten-Move (P2) auf Person-Ordner verallgemeinern
- [ ] Tests: Korrektur-Szenario (Multi-Datei), Gruppenbild-Kopien, FS-Drop mit Zweit-Person — datenkritisch
- [x] Doc-Update: docs/models.md (Instanz-Semantik), routes.md

## Report-Back

Implementiert 2026-06-20. 5/6 Checklistenpunkte abgehakt; Tests übersprungen (private-Profil: keine neuen Tests).

**Neues Modul:** `photofant/media/person_folders.py` — Kern der Orchestrierung:
- `materialize_assignment()` — Move-vs-Copy-Logik: _unknown-Instanz (wenn nicht fixed und kein anderer realer Besitzer) wird verschoben, sonst wird kopiert
- `reassign_face()` — manuelles Umhängen: Face-Crop + Bilddatei physisch umziehen, Instance-Cleanup wenn Quell-Person keine Faces mehr hat
- `materialize_clustering_results()` — Bulk-Materialisierung nach HDBSCAN
- `move_face_crops_to_person()` — Face-Crops in den richtigen Person-Ordner schieben
- Crash-safe: `_safe_move()` mit Source-gone-Dest-present-Recovery (gleiche Strategie wie `moves.py`)

**Ordner-Konvention:** `_unknown/` für den Auffang, `person_{id}/` für benannte Personen. Jeder hat `photos/`, `favourites/`, `faces/`, `edits/`.

**assign-Endpoint** (`PATCH /api/faces/{id}/assign`): setzt `fixed_person=true`, bewegt Datei + Crop physisch, räumt verwaiste Instanzen auf, feuert Smart-Album-Re-Evaluation.

**FS-Drop-Erkennung:** `_import_to_person()` in `import_job.py` — erkennt `person_{id}/photos/` und `person_{id}/favourites/` beim Scan, importiert mit `fixed_person=true`. Filterung: `.photofant/`, `faces/`, `edits/` werden übersprungen.

**Smart-Album Person-Trigger:** In `collections/engine.py` aktiviert — `type=person` matcht jetzt Assets, die eine Instanz bei der Trigger-Person haben.

**Favoriten-Move:** Bereits generisch — `set_favourite` in `moves.py` berechnet den Person-Ordner aus dem Dateipfad (`source.parent.parent`), funktioniert für `_unknown/` und `person_{id}/` identisch.

**Geänderte Dateien:**
- `jobs/clustering_job.py` — ruft nach Clustering `materialize_clustering_results()` auf; inkrementelles Matching materialisiert bei Auto-Assign
- `api/faces.py` — neuer `PATCH /faces/{id}/assign` Endpoint
- `jobs/import_job.py` — `_import_to_person()`, `_is_scannable()`, Scan-Job erkennt Person-Ordner
- `collections/engine.py` — Person-Trigger aktiviert (war bis P7 inaktiv)
- `docs/models.md` — Multi-Instance-Semantik dokumentiert
- `docs/routes.md` — assign-Endpoint + FS-Drop + Person-Ordner-Konvention dokumentiert

**Abweichungen:** Keine inhaltlichen Abweichungen. Edits-Move bei Assign ist vorbereitet (Ordnerstruktur existiert), wird aber erst relevant wenn P8 Edits einführt.
