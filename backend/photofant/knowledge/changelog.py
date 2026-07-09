"""ChangelogService — Explainability-Log der Korrekturen (P25 Phase 3).

Gegenstück zu ``TaskService`` (P23): reiner Arbeitszustand/Metadaten über der
Wissensbasis (``knowledge_changelog``), kein Vault-Wissen. Der neue Feldwert selbst
lebt im Markdown + im Entity-Cache (``KnowledgeService.update_entity``) — hier wird
nur *was/warum/wer/wann* protokolliert (Dok 020 §14), damit die Explainability-UI
(geteilte Payload mit P26 Phase 3) sie abfragen kann, ohne Markdown-Diffs zu parsen.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeChangelog


class ChangelogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        entity_id: str,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str,
        source: str,
        job_id: str,
    ) -> KnowledgeChangelog:
        entry = KnowledgeChangelog(
            entity_id=entity_id,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            source=source,
            job_id=job_id,
            created_at=datetime.now(UTC),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for_entity(self, entity_id: str) -> list[KnowledgeChangelog]:
        statement = (
            select(KnowledgeChangelog)
            .where(KnowledgeChangelog.entity_id == entity_id)
            .order_by(KnowledgeChangelog.created_at.desc())
        )
        return list(self.session.execute(statement).scalars())
