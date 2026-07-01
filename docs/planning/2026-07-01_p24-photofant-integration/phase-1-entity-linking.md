# Phase 1 — Entity-Linking + Job-Kette (Backend)

**Komplexität:** standard (Schleifenschutz ist der heikle Kern) · **Status:** pending

## Kontext
- README → Kontrakt + Chesterton (Bestätigungs-Pfad!)
- **P22** (`link_media`, media_links) · **P23** (LookupJob, Tasks)
- Bestand vor Trigger lesen: `api/persons.py`, `jobs/clustering_job.py`, `jobs/face_job.py`, `media/person_folders.py`, `jobs/queue.py` (Depth/ParentJobId), Konzept Dok 030 §10/§11

## AK
- [ ] `POST/DELETE /api/persons/{id}/link-entity` verknüpft/löst (media_links Vault + Cache); analog Assets. Überlebt Cache-Rebuild.
- [ ] Person bestätigt ohne Entity + `autoLookup` → **ein** `KnowledgeLookupJob`.
- [ ] **Schleifenschutz belegbar:** bei erreichter `jobs.maxDepth` kein Folgejob, kein Selbst-Typ-Recurse.
- [ ] `autoLookup=false` → kein Auto-Job.
- [ ] Bestehende Personen-Funktionen unverändert.

## Umsetzung
- [ ] link/unlink-Routen in `api/persons.py` + `api/assets.py` (dünn, Logik im Service)
- [ ] Detail-DTO um optionales `linked_entity` (Cache-Projektion)
- [ ] Trigger am Bestätigungs-Einstiegspunkt anhängen (additiv), Depth/ParentJobId setzen
- [ ] Link-Löschung an Personen-Löschung koppeln (Waisen-Schutz)
- [ ] Doc: `docs/routes.md`, `docs/code-map.md`, ADR-011 anlegen (falls in P22 nicht geschehen)
