"""KnowledgeUpdateJob (P27 Phase 3) — Gemma schlägt eine Ergänzung zu einer bestehenden
Entity vor.

Der Nutzer klickt im Lore Panel „Ergänzen (KI)": dieser Job fordert die Fähigkeit
``KNOWLEDGE_UPDATE`` an (nie ein Modell — ADR-027), lässt Gemma aus dem aktuellen
Wissensstand (Titel, Typ, Domäne, Aliase, Beziehungen, Beschreibung) eine überarbeitete
Beschreibung erzeugen und prüft sie als **Patch** gegen die Domäne (P22-Validator,
Trockenlauf). Nichts wird geschrieben: das Ergebnis reist über den Job-Stream zurück und
zeigt sich im Lore Panel als Diff (alt→neu) mit Begründung. Erst „Annehmen" schreibt —
über den P25-Patch-Pfad (``enqueue_knowledge_patch``) mit ``owner=inferred`` (P27-
Sicherheitsregel, Konzept-ADR-006).

Nur die Beschreibung wird vorgeschlagen (FINDINGS Phase 2/3): ein rohes Text-LM liefert
für Aliase/Beziehungen nichts Verlässliches — dieselbe bewusste Einschränkung wie
``KnowledgeImportJob``. Reine Sackgasse: löst keine Folge-Jobs aus.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from photofant.db.models import Asset, AssetInstance, AssetTag, Tag
from photofant.db.session import SessionLocal
from photofant.inference.capabilities import Capability, generate
from photofant.inference.prompt_library import PromptLibrary
from photofant.jobs.queue import JobKind, JobState, JobStatus, job_queue
from photofant.knowledge.schema import Entity
from photofant.knowledge.service import EntityNotFoundError, KnowledgeService
from photofant.knowledge.vault import open_vault

log = logging.getLogger(__name__)

# Deckel für das Foto-Signal im Prompt (P39 Phase 8, README-Vorbehalt „noch keine Zahl
# verifiziert") — kompakt genug, dass der Prompt nicht durch viele Fotos aufgebläht wird.
# FINDINGS, falls sich das als zu knapp/groß herausstellt.
_MAX_PHOTO_CAPTIONS = 8
_MAX_PHOTO_TAGS = 12

# Rohe Textgenerierung liefert keine kalibrierte Confidence (FINDINGS: GenerationResult.
# confidence bleibt None). Ein KI-Ergänzungsvorschlag ist per Definition unbestätigt — er
# bekommt dieselbe feste, mittlere „inferred"-Confidence wie der Import-Vorschlag.
SUGGESTION_CONFIDENCE = 0.5

_PROMPT_NAME = "knowledge_update"


def _recognized_photo_asset_ids(session: Session, person_ids: list[int]) -> list[int]:
    """Fotos, auf denen eine der verknüpften Personen erkannt wurde (dasselbe Muster wie
    ``api/knowledge.py::_combined_photo_asset_ids`` — hier bewusst separat gehalten, damit
    ``jobs`` nicht von ``api`` importiert). Nur erkannte Fotos, keine manuell verknüpften
    Assets: AK 2 verlangt, dass ohne Personen-Verknüpfung nichts einfließt."""
    if not person_ids:
        return []
    rows = session.execute(
        select(AssetInstance.asset_id)
        .where(AssetInstance.person_id.in_(person_ids), AssetInstance.deleted_at.is_(None))
        .distinct()
    ).all()
    return [int(row[0]) for row in rows]


def _photo_signal_section(session: Session, person_ids: list[int]) -> str | None:
    """Kompakte Zusammenfassung aus Captions + häufigsten Tags der erkannten Fotos einer
    Person — zusätzlicher Hinweis für Gemma, kein Beleg (README „Kritisch gegenlesen",
    dieselbe Vorsicht wie beim Halluzinations-Risiko, ADR-034). ``None`` ohne Fotos (AK 2)."""
    asset_ids = _recognized_photo_asset_ids(session, person_ids)
    if not asset_ids:
        return None

    caption_rows = session.execute(
        select(Asset.caption)
        .where(Asset.id.in_(asset_ids), Asset.caption.is_not(None))
        .order_by(func.coalesce(Asset.created_at, Asset.imported_at).desc())
        .limit(_MAX_PHOTO_CAPTIONS)
    ).scalars().all()
    tag_rows = session.execute(
        select(Tag.name, func.count(AssetTag.id).label("freq"))
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .where(AssetTag.asset_id.in_(asset_ids), AssetTag.manually_removed.is_(False))
        .group_by(Tag.name)
        .order_by(func.count(AssetTag.id).desc())
        .limit(_MAX_PHOTO_TAGS)
    ).all()
    if not caption_rows and not tag_rows:
        return None

    lines = ["Hinweise aus Fotos dieser Person (automatisch erkannt, keine bestätigten Fakten):"]
    if caption_rows:
        # `is_not(None)` filtert oben schon NULLs raus — mypy kennt die Spalte trotzdem
        # als `str | None`, daher hier explizit auf `str` engen.
        lines.append("Bildbeschreibungen: " + " / ".join(caption for caption in caption_rows if caption))
    if tag_rows:
        lines.append("Häufige Motive/Tags: " + ", ".join(name for name, _ in tag_rows))
    return "\n".join(lines)


def _build_user_prompt(entity: Entity, photo_signal: str | None) -> str:
    """Der konkrete Kontext-Turn für Gemma — die bestehende Entity als Ausgangspunkt.
    Die Rollen-/Regelanweisung (nur ergänzen/korrigieren, nichts Bestätigtes verwerfen)
    kommt als System-Teil aus der Prompt-Library."""
    aliases = ", ".join(entity.aliases) if entity.aliases else "keine"
    relationships = (
        ", ".join(f"{relationship.type}→{relationship.target}" for relationship in entity.relationships)
        if entity.relationships
        else "keine"
    )
    photo_block = f"{photo_signal}\n\n" if photo_signal else ""
    return (
        f"Entity-Titel: {entity.title}\n"
        f"Typ: {entity.type}\n"
        f"Domäne: {entity.domain}\n"
        f"Aliase: {aliases}\n"
        f"Beziehungen: {relationships}\n"
        f"Aktuelle Beschreibung:\n{entity.body or '(leer)'}\n\n"
        f"{photo_block}"
        "Schreibe eine überarbeitete, vollständige Beschreibung (2-5 Sätze): ergänze "
        "fehlende Fakten und korrigiere Falsches, richtige Sätze unverändert übernehmen. "
        "Nur belegbare Fakten; keine Aufzählung, kein Markdown-Titel."
    )


def _run_update(status: JobStatus, entity_id: str) -> None:
    prompt = PromptLibrary().get(_PROMPT_NAME)
    if prompt is None:
        raise RuntimeError(
            f"Prompt '{_PROMPT_NAME}' nicht gefunden — Prompt-Library prüfen (ai.promptLibraryPath)"
        )

    job_queue.update(status, progress=0.2, state=JobState.RUNNING)
    vault = open_vault()
    with SessionLocal() as session:
        service = KnowledgeService(session, vault)
        entity = service.find_entity(entity_id)
        if entity is None:
            raise EntityNotFoundError(f"Entity '{entity_id}' nicht gefunden")

        job_queue.update(status, progress=0.4, state=JobState.RUNNING)
        photo_signal = _photo_signal_section(session, entity.media_links.persons)
        generation = generate(
            Capability.KNOWLEDGE_UPDATE,
            _build_user_prompt(entity, photo_signal),
            system=prompt.text,
            prompt_version=prompt.version,
        )
        new_body = generation.text.strip()
        if not new_body:
            raise RuntimeError(
                "Das Modell lieferte keinen Vorschlag — Modell nicht verfügbar oder leere Antwort"
            )

        job_queue.update(status, progress=0.8, state=JobState.RUNNING)
        validation_errors = service.validate_patch(entity_id, {"body": new_body})
        old_body = entity.body

    explainability: dict[str, Any] = {
        "model_id": generation.model_id,
        "capability": generation.capability,
        "prompt_version": generation.prompt_version,
        "duration_ms": generation.duration_ms,
        "confidence": SUGGESTION_CONFIDENCE,
        "reason": "Vorschlag von Gemma auf Basis der bestehenden Beschreibung.",
    }

    if validation_errors:
        # Ungültiger Vorschlag wird abgewiesen, nicht angezeigt (AK: kein Direkt-Write,
        # aber auch kein unbrauchbarer Vorschlag im Panel).
        result: dict[str, Any] = {
            "proposal": None,
            "old_body": old_body,
            "explainability": explainability,
            "validation_errors": validation_errors,
        }
        log.info("knowledge_update: Vorschlag für '%s' abgewiesen (%d Fehler)", entity_id, len(validation_errors))
    else:
        result = {
            "proposal": {"body": new_body},
            "old_body": old_body,
            "explainability": explainability,
            "validation_errors": [],
        }
        log.info("knowledge_update: Vorschlag für '%s' erzeugt (%.0f ms)", entity_id, generation.duration_ms)

    job_queue.set_result(status, result)


async def run_knowledge_update_job(status: JobStatus, entity_id: str) -> None:
    job_queue.update(status, progress=0.1, state=JobState.RUNNING)
    await asyncio.to_thread(_run_update, status, entity_id)


async def enqueue_knowledge_update(entity_id: str) -> JobStatus:
    async def _factory(status: JobStatus) -> None:
        await run_knowledge_update_job(status, entity_id)

    return await job_queue.enqueue(
        kind=JobKind.KNOWLEDGE_UPDATE,
        label=f"KI-Ergänzung: {entity_id}",
        coro_factory=_factory,
    )
