"""Vault — die Markdown-Wissensbasis auf der Platte.

Legt die Ordnerstruktur (`knowledge/`, `domains/`, `prompts/`) beim ersten Zugriff
an, seedet die mitgelieferten Domänen und löst Entity-IDs auf Dateipfade auf.
Diese Schicht macht reines Datei-I/O; Ownership-/Confidence-Regeln liegen im
späteren ``KnowledgeService`` (Phase 3).
"""
from __future__ import annotations

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

from photofant.knowledge.domains import Domain, load_domain
from photofant.knowledge.parser import parse_entity, serialize_entity
from photofant.knowledge.schema import Entity

log = logging.getLogger(__name__)

_DOMAINS_DIRNAME = "domains"
_PROMPTS_DIRNAME = "prompts"
# Mitgelieferte Beispiel-Domänen, die beim ersten Zugriff in den Vault kopiert werden.
_PACKAGED_DOMAINS_DIR = Path(__file__).parent / _DOMAINS_DIRNAME


class Vault:
    """Wurzel der Markdown-Wissensbasis."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def ensure_structure(self) -> None:
        """Legt die Vault-Ordner an und seedet fehlende mitgelieferte Domänen."""
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / _DOMAINS_DIRNAME).mkdir(exist_ok=True)
        (self.root / _PROMPTS_DIRNAME).mkdir(exist_ok=True)
        self._seed_packaged_domains()

    def domain_path(self, domain_name: str) -> Path:
        return self.root / _DOMAINS_DIRNAME / f"{domain_name.lower()}.yaml"

    def load_domain(self, domain_name: str) -> Domain:
        """Lädt eine Domäne aus dem Vault (nach ``ensure_structure``)."""
        return load_domain(self.domain_path(domain_name))

    def entity_path(self, entity: Entity, domain: Domain) -> Path:
        """Zielpfad einer Entity: ``<root>/<type-folder>/<slug>.md``."""
        return self.root / domain.folder_for(entity.type) / f"{entity.slug}.md"

    def load_entity(self, path: Path) -> Entity:
        return parse_entity(path.read_text(encoding="utf-8"))

    def iter_entity_files(self) -> Iterator[Path]:
        """Alle Entity-Markdown-Dateien im Vault (für Rebuild/Reconcile).

        Läuft rekursiv über die Typ-Ordner und überspringt die Nicht-Entity-Bereiche
        ``domains/`` (YAML) und ``prompts/`` (später P27) — dort liegende ``.md``
        sind keine Entities. Reihenfolge ist die von ``rglob`` (nicht sortiert);
        der Aufrufer verlässt sich nicht darauf.
        """
        for path in self.root.rglob("*.md"):
            top_level = path.relative_to(self.root).parts[0]
            if top_level in {_DOMAINS_DIRNAME, _PROMPTS_DIRNAME}:
                continue
            yield path

    def load_all(self) -> Iterator[tuple[Path, Entity]]:
        """(Pfad, Entity) für jede Entity-Datei — reines I/O, keine Validierung.

        Ein defektes Frontmatter lässt ``load_entity`` werfen; der Aufrufer (Rebuild/
        Reconcile) fängt das pro Datei ab, damit eine kaputte Notiz nicht den ganzen
        Lauf abbricht.
        """
        for path in self.iter_entity_files():
            yield path, self.load_entity(path)

    def save_entity(self, entity: Entity, domain: Domain) -> Path:
        """Schreibt eine Entity als Markdown und gibt den Pfad zurück.

        Reines I/O — der Aufrufer verantwortet Validierung und Ownership.
        """
        path = self.entity_path(entity, domain)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialize_entity(entity), encoding="utf-8")
        return path

    def delete_entity(self, entity: Entity, domain: Domain) -> None:
        """Löscht die Markdown-Datei einer Entity, falls vorhanden.

        Reines I/O — der Aufrufer verantwortet Ownership-Prüfung und Cache-Löschung.
        """
        self.entity_path(entity, domain).unlink(missing_ok=True)

    def _seed_packaged_domains(self) -> None:
        target_dir = self.root / _DOMAINS_DIRNAME
        if not _PACKAGED_DOMAINS_DIR.is_dir():
            return
        for source in _PACKAGED_DOMAINS_DIR.glob("*.yaml"):
            target = target_dir / source.name
            if target.exists():
                continue
            try:
                shutil.copyfile(source, target)
                log.info("knowledge: seeded default domain '%s' into vault", source.name)
            except OSError as error:
                log.warning("knowledge: could not seed domain '%s': %s", source.name, error)


def get_vault_path() -> Path:
    """Vault-Wurzel aus den Settings (``knowledge.vault_path``), Default ``<data>/knowledge``."""
    from photofant.config import get_data_root_base
    from photofant.settings import load_settings

    settings = load_settings()
    configured = settings["knowledge"].get("vault_path")
    if configured:
        return Path(configured)
    return get_data_root_base() / "knowledge"


def open_vault() -> Vault:
    """Öffnet den konfigurierten Vault und stellt die Struktur sicher."""
    vault = Vault(get_vault_path())
    vault.ensure_structure()
    return vault
