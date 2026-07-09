"""Vault-Struktur — Seeding (Domänen, AGENTS.md) und Entity-Iteration.

Deckt zwei Regeln ab, die beim Anlegen von `AGENTS.md.template` (Anleitung für
Agenten, die direkt im Vault-Ordner arbeiten) leicht kaputtgehen: die Seed-Datei
darf Nutzer-Anpassungen nicht überschreiben, und sie darf nie als Entity
fehlinterpretiert werden (sie liegt direkt in der Vault-Wurzel, keine Entity-Datei
tut das).
"""
from __future__ import annotations

from pathlib import Path

from photofant.knowledge.schema import Entity
from photofant.knowledge.vault import Vault


def test_ensure_structure_seeds_agents_md(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "vault")

    vault.ensure_structure()

    agents_md = vault.root / "AGENTS.md"
    assert agents_md.is_file()
    assert "Wissensbasis" in agents_md.read_text(encoding="utf-8")


def test_ensure_structure_does_not_overwrite_edited_agents_md(tmp_path: Path) -> None:
    vault = Vault(tmp_path / "vault")
    vault.ensure_structure()
    agents_md = vault.root / "AGENTS.md"
    agents_md.write_text("Eigene Notizen des Nutzers.", encoding="utf-8")

    vault.ensure_structure()

    assert agents_md.read_text(encoding="utf-8") == "Eigene Notizen des Nutzers."


def test_iter_entity_files_ignores_root_level_markdown(tmp_path: Path) -> None:
    """AGENTS.md (und jede andere .md direkt in der Wurzel) ist keine Entity-Datei."""
    vault = Vault(tmp_path / "vault")
    vault.ensure_structure()
    domain = vault.load_domain("Movies")
    vault.save_entity(Entity(id="Actor/rdj", type="Actor", title="RDJ", domain="Movies"), domain)

    entity_files = list(vault.iter_entity_files())

    assert len(entity_files) == 1
    assert entity_files[0].name == "rdj.md"
