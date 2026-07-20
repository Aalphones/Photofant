# Phase 3 — API-Route + Autonomie-/Privat-Guard

**Komplexität:** standard (folgt exakt dem Muster der bestehenden P27-Routen).
**Voraussetzung:** Phase 2 abgeschlossen (`enqueue_knowledge_discovery` funktioniert).

## Kontext (lesen vor dem Start)
- `backend/photofant/api/knowledge_ai.py` — die komplette Datei ist die Vorlage. Insbesondere:
  `_is_private_domain` (Zeile 31), `AutonomyDto` (43), `get_autonomy` (115),
  `request_import_suggestion` (125, gleicher Guard-Stil: 409 bei `off`, 422 bei privater
  Domäne).
- `docs/routes.md` — Abschnitt zu den P27-KI-Routen (um Zeile 1091-1099) — Format-Vorlage für
  den neuen Routen-Eintrag.

## Aufgabe 1 — DTOs + Route
`api/knowledge_ai.py` ändern:

`AutonomyDto` um Feld erweitern:
```python
class AutonomyDto(BaseModel):
    knowledge_import: str
    knowledge_update: str
    interview: str
    discovery: str
```

`get_autonomy()` erweitern:
```python
    return AutonomyDto(
        knowledge_import=autonomy_for(Capability.KNOWLEDGE_IMPORT),
        knowledge_update=autonomy_for(Capability.KNOWLEDGE_UPDATE),
        interview=autonomy_for(Capability.INTERVIEW),
        discovery=autonomy_for(Capability.KNOWLEDGE_DISCOVERY),
    )
```

Neue DTOs + Route (nach `accept_update_suggestion` anfügen):
```python
class DiscoveryRequest(BaseModel):
    """P38 — löst den KnowledgeDiscoveryJob aus. Schreibt ohne Bestätigung (ADR-031)."""

    entity_id: str


class DiscoveryResponse(BaseModel):
    job_id: str


@router.post("/discovery", response_model=DiscoveryResponse)
async def request_discovery(body: DiscoveryRequest) -> DiscoveryResponse:
    """Löst den KnowledgeDiscoveryJob aus (P38, ADR-031) — Websuche + Auto-Write, keine
    Bestätigung. Bei `ai.autonomy.discovery != "auto"` wird die Aktion abgelehnt (das Panel
    bietet sie dann gar nicht erst an). Private Domänen sind kategorisch ausgeschlossen
    (Konzept-ADR-009) — derselbe Guard wie beim KI-Import."""
    if autonomy_for(Capability.KNOWLEDGE_DISCOVERY) != "auto":
        raise HTTPException(status_code=409, detail="Web-Recherche ist in den Einstellungen deaktiviert")
    if not body.entity_id.strip():
        raise HTTPException(status_code=422, detail="entity_id ist erforderlich")

    entity = _entity_for_guard(body.entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity '{body.entity_id}' nicht gefunden")
    if _is_private_domain(entity.domain):
        raise HTTPException(
            status_code=422,
            detail="Private Entitäten werden nie web-recherchiert — nutze „Ergänzen (KI)" (webfrei)",
        )

    status = await enqueue_knowledge_discovery(body.entity_id)
    return DiscoveryResponse(job_id=status.id)
```

`_entity_for_guard` ist ein kleiner neuer Helfer (nicht in `_is_private_domain` gibt es schon
Vault-Zugriff, aber der lädt keine Entity, nur eine Domäne per Name — hier brauchen wir erst
die Entity, um an ihre Domäne zu kommen):
```python
def _entity_for_guard(entity_id: str) -> Entity | None:
    """Lädt die Entity nur für den Privat-Domain-Guard — der Job lädt sie danach erneut
    (eigene DB-Session im Thread), doppeltes Lesen ist hier bewusst in Kauf genommen statt
    eine Session über die async-Grenze zu reichen."""
    from photofant.db.session import SessionLocal
    from photofant.knowledge.service import KnowledgeService

    with SessionLocal() as session:
        return KnowledgeService(session, open_vault()).find_entity(entity_id)
```
(Import `Entity` aus `photofant.knowledge.schema` oben in der Datei ergänzen; Import
`enqueue_knowledge_discovery` aus `photofant.jobs.knowledge_discovery_job` ergänzen.)

## AK dieser Phase
- [ ] `GET /api/knowledge/ai/autonomy` liefert `discovery: "off"` im Auslieferungszustand
      (Default aus Phase 1).
- [ ] `POST /api/knowledge/ai/discovery` mit `ai.autonomy.discovery == "off"` → 409.
- [ ] Nach manuellem Setzen von `ai.autonomy.discovery = "auto"` in den Settings + Backend-
      Neustart: Route mit einer **privaten** Test-Entity → 422 mit der obigen Meldung.
- [ ] Dieselbe Route mit einer **öffentlichen** Test-Entity → 200, `job_id` gültig, Job taucht
      im Job-Dock auf.

## Doc-Updates
- [ ] `docs/routes.md` — neuer Eintrag analog zum bestehenden P27-Block (Zeile ~1091):
      Route, Guards (409/422), Job-Ergebnis-Form (`KnowledgeDiscoveryResult`, siehe README-
      Kontrakt).
- [ ] `docs/code-map.md` — „KI-Layer / Gemma"-Zeile um `POST /discovery` + `DiscoveryRequest/
      Response` ergänzen.

## Report-Back
