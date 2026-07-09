# Phase 1 — Entity-Linking + Job-Kette (Backend)

**Komplexität:** standard (Schleifenschutz ist der heikle Kern) · **Status:** complete

**Abweichung vom Plan-Text:** kein `ParentJobId`/`Depth`-Tiefenschutz gebaut — die dafür
unterstellte P22-Infrastruktur existierte nie, und `KnowledgeLookupJob` ist ein Sackgassen-Job
(kein Rekursionsrisiko). Details: `FINDINGS.md`, `ADR-014`.

## Kontext
- README → Kontrakt + Chesterton (Bestätigungs-Pfad!)
- **P22** (`link_media`, media_links) · **P23** (LookupJob, Tasks)
- Bestand vor Trigger lesen: `api/persons.py`, `jobs/clustering_job.py`, `jobs/face_job.py`, `media/person_folders.py`, `jobs/queue.py` (Depth/ParentJobId), Konzept Dok 030 §10/§11

## AK
- [x] `POST/DELETE /api/persons/{id}/link-entity` verknüpft/löst (media_links Vault + Cache); analog Assets. Überlebt Cache-Rebuild.
- [x] Person bestätigt ohne Entity + `auto_lookup` → **ein** `KnowledgeLookupJob`.
- [x] **Schleifenschutz belegbar:** kein Folgejob möglich (Sackgassen-Job) + `TaskService`-Dedup
  verhindert Mehrfach-Aufgaben — ersetzt den geplanten `maxDepth`-Mechanismus (ADR-014).
- [x] `auto_lookup=false` → kein Auto-Job.
- [x] Bestehende Personen-Funktionen unverändert (nur additive Erweiterungen, Move-Pfad nicht berührt).

## Umsetzung
- [x] link/unlink-Routen in `api/persons.py` + `api/assets.py` (dünn, Logik im Service)
- [x] Detail-DTO um optionales `linked_entity` (Cache-Projektion)
- [x] Trigger am Bestätigungs-Einstiegspunkt anhängen (additiv), kein Depth/ParentJobId (ADR-014)
- [x] Link-Löschung an Personen-Löschung koppeln (Waisen-Schutz)
- [x] Doc: `docs/routes.md`, `docs/code-map.md`, ADR-014 angelegt (ADR-011 war belegt)
