# P25 — Lore Panel (MVP-Zielpunkt)

> Roadmap-Phase 4 (Dok 050 §5/§7/§10). **Danach ist Photofant 2.0 MVP-fertig** (Konzept: „nutzbar nach Phase 4", ohne Gemma). Baut auf **P22** + **P24** auf. *(private, lean.)*

## Ziel
Beim Öffnen eines Bildes zeigt ein ruhiger Bereich rechts das Wissen zum Inhalt: Kurzbio, Rollen, Beziehungen, Franchises, eigene Bilder, Quellen, verwandte Entities — direkt sichtbar, kein Chat. Jede auto-erzeugte Info ist per „Das stimmt nicht" korrigierbar, ohne Markdown von Hand zu editieren.

## Scope
**Drin:** Lore-Aggregations-API (Asset/Person → gebündelte Sicht, read-only, keine KI) · Lore-Panel-UI im Lightbox-Kontextbereich · Korrektur-Flow „Das stimmt nicht" → `PatchJob` → Update → Cache (Dok 050 §7); Patch stammt hier vom **Nutzer** (Formular), Struktur = späterer Gemma-Pfad (P27).
**Draußen:** Empfehlungen → P26 · KI-Lore-Texte (`LoreJob` mit Gemma) → P27. P25 zeigt nur vorhandenes, per Wizard/Nutzer eingetragenes Wissen.

## Abhängigkeiten
**P22** (`get_lore`-Ausbau, Cache-Reads) + **P24** (media_links — ohne sie ist das Panel leer).
⚠️ **Screen-Eigentümer:** Lightbox gehört **P15** (`2026-06-28_p15-lightbox-angleichung/`). P25 dockt an P15s Panel-Struktur an, **kein** Parallel-Container. Beim Umsetzen zuerst P15-README + `features/galerie/lightbox/` lesen, Andockpunkt benennen. Ist P15 noch offen → Reihenfolge mit Sascha klären (🔴 an Implementierungs-Start).

## Kontrakt-Ergänzungen
- **`get_lore(id)` voll** (P22-Stub → aus): `{ entity, relationships[{type,target_entity}], related_media[], sources[], franchises[] }`; Beziehungs-Ziele als Titel/Typ aufgelöst.
- **REST:** `GET /api/knowledge/lore?asset_id=` **oder** `?person_id=`; kein Wissen → 200 mit `entity: null`.
- **`PatchJob`** `jobs/knowledge_patch_job.py`: Patch (Feld, Wert, Grund, owner=user) → Validator (P22) → `update_entity` → Cache-Update; erzeugt Explainability-Eintrag (Grund, Quelle, Zeit, Job — Dok 020 §14).
- **REST:** `POST /api/knowledge/entities/{id}/patch` (field, value, reason).

## Reservierte Entscheidungen
Kein neues ADR (Realisierung der P22-Mutations-Regel/ADR-010). Keine neuen settings-Keys.

## Design-Lage (freihändig — freigegeben)
Kein Mockup. Panel-Struktur unten als AK fixiert (Dok 050 §5), eingepasst in P15s Panel-System + Tailwind-Tokens. Ruhig, kein Chat.

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Lore-Aggregations-API (Backend) | standard | complete |
| 2 | Lore-Panel-UI (Lightbox) | heikel (fremder Screen P15 + freihändiges Design) | complete |
| 3 | Korrektur-Flow (PatchJob) | standard | complete |

## Finale AK (Gesamt)
- [ ] Bild mit verknüpfter Entity → Panel rechts zeigt Kurzbio, Rollen, Beziehungen, Franchises, eigene Bilder, Quellen, verwandte Entities (soweit vorhanden).
- [ ] Ohne Wissen: Panel leer/ausgeblendet, kein Fehler.
- [ ] Nutzer markiert auto/inferred-Info als falsch → Korrektur landet als Patch im Markdown, Cache aktualisiert sich, ohne dass der Nutzer Dateien anfasst.
- [ ] Jede Korrektur erzeugt einen Explainability-Eintrag.
- [ ] Panel fügt sich sauber in P15s Lightbox ein, keine Lightbox-Regression.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. Bild einer verknüpften Person öffnen → Panel zeigt gefüllte Sektionen; Beziehung anklicken → Ziel-Entity.
2. Bild ohne Wissen öffnen → „Noch kein Wissen — anlegen?"-Zustand, kein Fehler.
3. Ein inferred-Feld „Das stimmt nicht" → Wert ändern → Panel zeigt neuen Wert; `cat` der Vault-Datei zeigt Änderung + Changelog-Eintrag.
4. P15-Lightbox (Zoom, Toolbar) funktioniert unverändert.

## Risiken
- 🟡 **Screen-Konflikt mit P15** → andocken statt danebenbauen, Andockpunkt benennen; Reihenfolge ggf. klären.
- 🟡 **Leeres Panel als Normalfall** (frühes MVP wenig Wissen) → dezenter „anlegen?"-Zustand mit Wizard-Absprung (P23).
- 🟡 **Patch-Ownership** → Patch läuft durch denselben Service-Ownership-Pfad (P22), keine Sonderlogik.

## Chesterton
**Vor Änderung verstehen:** P15s Lightbox-Panel-Struktur (`features/galerie/lightbox/`, `store/gallery/`) regelt Zoom-Stage + Panel-Header + Toolbar. P25 hängt einen Panel-Bereich an; Zoom-/Toolbar-Pfad bleibt unangetastet. Andockpunkt beim Umsetzen benennen.

---
## Summary / Deviations / Follow-ups

**Summary:** Lore-Panel + Korrektur-Flow fertig — P25 komplett, **Photofant 2.0 MVP erreicht**
(ohne Gemma, wie im Ziel-Satz oben vorgesehen). Bild öffnen zeigt gebündeltes Wissen rechts im
Lightbox-Panel (5 Sektionen); auto/inferred-Kurzbio ist per „Das stimmt nicht" korrigierbar,
Korrektur läuft als Job über den P22-Ownership-Pfad und erzeugt einen Explainability-Eintrag.

**Files touched (Phase 3):** Backend: `db/models.py` (+`KnowledgeChangelog`), `knowledge/changelog.py`
(neu, `ChangelogService`), `knowledge/service.py` (`PATCHABLE_FIELDS` öffentlich), `knowledge/repository.py`
(Cascade-Delete für Changelog), `jobs/queue.py` (+`JobKind.KNOWLEDGE_PATCH`), `jobs/knowledge_patch_job.py`
(neu, `KnowledgePatchJob`), `api/knowledge.py` (+`POST .../patch`, +`GET .../changelog`) · Tests:
`tests/test_knowledge_patch_job.py` (neu), `tests/test_knowledge_api.py` (+3 Tests). Frontend:
`models/knowledge.model.ts`+`models/index.ts` (+`PatchEntityRequest`/`PatchJobResponse`/`ChangelogEntryDto`),
`models/job.model.ts` (+`knowledge_patch`), `services/knowledge.service.ts` (+`patchEntity`/`getChangelog`),
`features/galerie/lightbox/lore-panel/*` (Korrektur-Formular + SSE-Job-Warte + Lore-Reload).
Docs: `docs/routes.md`, `docs/code-map.md`.

**Deviations:**
- „Das stimmt nicht" deckt in dieser Phase nur die Kurzbio (`body`) ab, nicht jedes einzelne
  Panel-Feld (siehe `phase-3-correction-flow.md` AK-Anmerkung) — Backend/Job/Route sind bereits
  feldgenerisch, Erweiterung auf weitere Felder ist reine UI-Arbeit bei Bedarf.
- Explainability-Log liegt als Cache-Tabelle (`knowledge_changelog`), nicht als Vault-Anhang —
  Begründung wie bei `knowledge_tasks` (Arbeitszustand/Metadaten, nicht Vault-Wissen).

**Gefundene, nicht gefixte Lücke (pre-existing, außerhalb des Phasen-Scopes):** `JOB_KINDS` im
Frontend-Model (`models/job.model.ts`) fehlte schon vor dieser Phase `'knowledge_lookup'` (P23) —
`knowledge_patch` wurde jetzt ergänzt, der ältere Eintrag nicht (nicht Teil dieser Phase, aber
gemeldet statt stillschweigend übersehen).

**Follow-ups:** KI-Lore-Texte (`LoreJob`) → P27 · Empfehlungen unter dem Panel → P26 ·
`KnowledgeUpdateJob` (P27 Phase 3) und das geteilte Explainability-Popover (P26 Phase 3) bauen
direkt auf dieser Phase auf (Patch-Pfad + Changelog-Payload wiederverwendet) · Korrektur-Formular
auf weitere Felder ausweiten, falls in der Praxis gebraucht.
