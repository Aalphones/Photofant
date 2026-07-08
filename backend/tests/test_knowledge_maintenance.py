"""Knowledge-Cache-Wartung — Rebuild + Reconcile aus dem Markdown-Vault (P22 Phase 4).

Setup läuft über den ``KnowledgeService`` (Markdown-first), damit Vault und Cache konsistent
starten; danach wird der Cache manipuliert / der Vault von Hand geändert und geprüft, dass
Rebuild bzw. Reconcile den Kontrakt einhalten (Markdown ist die Wahrheit).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from photofant.knowledge.maintenance import rebuild_cache, reconcile_cache
from photofant.knowledge.schema import Entity, Owner
from photofant.knowledge.service import KnowledgeService
from photofant.knowledge.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    instance = Vault(tmp_path / "vault")
    instance.ensure_structure()
    return instance


@pytest.fixture
def service(db_session: Session, vault: Vault) -> KnowledgeService:
    return KnowledgeService(db_session, vault)


def _actor(**overrides: object) -> Entity:
    defaults: dict[str, object] = {
        "id": "actors/robert-downey-jr",
        "type": "Actor",
        "title": "Robert Downey Jr.",
        "domain": "Movies",
        "aliases": ["RDJ"],
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def _movie(**overrides: object) -> Entity:
    defaults: dict[str, object] = {
        "id": "movies/iron-man",
        "type": "Movie",
        "title": "Iron Man",
        "domain": "Movies",
    }
    defaults.update(overrides)
    return Entity(**defaults)  # type: ignore[arg-type]


def test_rebuild_from_cleared_cache_restores_entities(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """Smoke-Checkliste #3: Cache leeren → Rebuild → Suche findet die Entity wieder."""
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)

    service.entities.clear_all()
    assert service.entities.get("actors/robert-downey-jr") is None

    result = rebuild_cache(db_session, vault)

    assert result.imported == 2
    assert result.failed == 0
    assert service.entities.get("actors/robert-downey-jr") is not None
    # Alias-Suche funktioniert nach dem Rebuild wieder (Kind-Zeilen mit rekonstruiert).
    assert [entity.id for entity in service.search_entities("RDJ")] == ["actors/robert-downey-jr"]


def test_rebuild_is_idempotent(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """Zweimal rebuilden erzeugt keine Duplikate — voller Ersatz aus dem Vault."""
    service.create_entity(_actor(), Owner.USER)

    rebuild_cache(db_session, vault)
    rebuild_cache(db_session, vault)

    assert len(service.entities.all()) == 1


def test_reconcile_takes_hand_edited_markdown(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """AK #2: eine von Hand geänderte Notiz wird in den Cache übernommen (Markdown gewinnt)."""
    service.create_entity(_actor(title="Robert Downey Jr."), Owner.USER)

    # Notiz von Hand ändern (nur Datei, Cache bleibt zunächst auf altem Stand).
    path = vault.root / "actors" / "robert-downey-jr.md"
    edited = vault.load_entity(path)
    edited.title = "Robert John Downey Jr."
    vault.save_entity(edited, vault.load_domain("Movies"))
    assert service.entities.get("actors/robert-downey-jr").title == "Robert Downey Jr."

    reconcile_cache(db_session, vault)

    assert service.entities.get("actors/robert-downey-jr").title == "Robert John Downey Jr."


def test_reconcile_removes_cache_row_without_vault_file(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """AK #2: eine Cache-Zeile ohne zugehörige Notiz-Datei wird entfernt."""
    service.create_entity(_actor(), Owner.USER)
    service.create_entity(_movie(), Owner.USER)

    # Notiz-Datei direkt löschen (simuliert manuelles Löschen im Dateisystem) — Cache-Zeile bleibt.
    (vault.root / "movies" / "iron-man.md").unlink()

    result = reconcile_cache(db_session, vault)

    assert result.removed == 1
    assert service.entities.get("movies/iron-man") is None
    assert service.entities.get("actors/robert-downey-jr") is not None


def test_reconcile_keeps_row_when_file_present_but_malformed(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """Sicherheit: eine vorhandene, aber defekt geparste Notiz darf ihre Cache-Zeile behalten.

    Sonst würde ein Tippfehler im Frontmatter stillen Datenverlust im Cache auslösen.
    """
    service.create_entity(_actor(), Owner.USER)

    path = vault.root / "actors" / "robert-downey-jr.md"
    path.write_text("---\nid: actors/robert-downey-jr\nconfidence: not-a-number\n---\nkaputt\n",
                    encoding="utf-8")

    result = reconcile_cache(db_session, vault)

    assert result.failed == 1
    assert result.removed == 0
    assert service.entities.get("actors/robert-downey-jr") is not None


def test_rebuild_skips_malformed_file_and_counts_it(
    service: KnowledgeService, vault: Vault, db_session: Session
) -> None:
    """Ein defektes Frontmatter reißt den Rebuild nicht ab — es wird gezählt und übersprungen."""
    service.create_entity(_actor(), Owner.USER)
    (vault.root / "actors" / "broken.md").write_text(
        "---\nid: actors/broken\nconfidence: nope\n---\n", encoding="utf-8"
    )

    result = rebuild_cache(db_session, vault)

    assert result.imported == 1
    assert result.failed == 1
    assert service.entities.get("actors/robert-downey-jr") is not None
