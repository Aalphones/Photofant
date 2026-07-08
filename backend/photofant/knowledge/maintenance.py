"""Wartungs-Kern der Wissensbasis — Cache aus dem Vault neu aufbauen / abgleichen.

Markdown ist die Wahrheit, der SQLite-Cache ist jederzeit aus dem Vault neu aufbaubar
(Kontrakt-AK). Dieses Modul kapselt genau zwei Operationen als reine, testbare Sync-
Funktionen (kein Job-Framework, keine Queue — die async-Hülle liegt in
``jobs/rebuild_job.py``):

- **rebuild** — Cache komplett leeren, dann jede Vault-Entity neu importieren. Für den
  Fall eines verdorbenen Caches: das Ergebnis ist garantiert identisch zum Vault.
- **reconcile** — sanfter Abgleich ohne Nuke: jede Vault-Entity re-importieren (Markdown
  gewinnt), Cache-Zeilen ohne zugehörige Vault-Datei entfernen.

Ein defektes Frontmatter bricht den Lauf nicht ab — die betroffene Datei wird geloggt
und übersprungen (``failed``-Zähler), der Rest läuft durch.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from photofant.db.models import KnowledgeEntity
from photofant.knowledge.repository import EntityRepository
from photofant.knowledge.schema import Entity
from photofant.knowledge.vault import Vault

log = logging.getLogger(__name__)


@dataclass
class KnowledgeSyncResult:
    """Zählwerk eines Wartungslaufs — nur für Logging/Diagnose."""

    imported: int = 0
    removed: int = 0
    failed: int = 0


def rebuild_cache(session: Session, vault: Vault) -> KnowledgeSyncResult:
    """Leert den Cache und baut ihn vollständig aus dem Vault neu auf.

    Mutiert die Session; der Aufrufer committet (der Job-Wrapper tut das).
    """
    repository = EntityRepository(session)
    repository.clear_all()
    imported, failed = _import_all(vault, repository)
    log.info("knowledge rebuild: %d imported, %d failed", imported, failed)
    return KnowledgeSyncResult(imported=imported, failed=failed)


def reconcile_cache(session: Session, vault: Vault) -> KnowledgeSyncResult:
    """Gleicht den Cache an den Vault an, ohne ihn zu leeren (Markdown gewinnt).

    Jede Vault-Entity wird re-importiert (überschreibt die Cache-Zeile), anschließend
    werden Cache-Zeilen entfernt, deren zugehörige Vault-Datei nicht mehr existiert. Es
    gibt keinen mtime-Vergleich: der Cache führt keine Zeitstempel-Spalte, also wird bei
    jedem Lauf voll re-importiert — bei persönlicher Notizmenge vernachlässigbar, und ein
    strikter Superset des „neuere Datei wird übernommen"-Verhaltens.

    Die Entfernung prüft die **Existenz der Datei**, nicht den Import-Erfolg: eine
    vorhandene, aber defekt geparste Notiz behält ihre Cache-Zeile (sonst würde ein
    Tippfehler im Frontmatter stillen Datenverlust auslösen).
    """
    repository = EntityRepository(session)
    imported, failed = _import_all(vault, repository)

    removed = 0
    for row in repository.all():
        if not _vault_file_exists(vault, row):
            repository.delete(row.id)
            removed += 1

    log.info(
        "knowledge reconcile: %d imported, %d removed, %d failed", imported, removed, failed
    )
    return KnowledgeSyncResult(imported=imported, removed=removed, failed=failed)


def _import_all(vault: Vault, repository: EntityRepository) -> tuple[int, int]:
    """Importiert jede Vault-Entity in den Cache. Gibt ``(importiert, fehlgeschlagen)`` zurück.

    Resilient pro Datei: eine kaputte Notiz wird geloggt und übersprungen, damit sie
    nicht den ganzen Lauf reißt.
    """
    imported = 0
    failed = 0
    for path in vault.iter_entity_files():
        try:
            entity = vault.load_entity(path)
            repository.upsert_from_vault(entity)
            imported += 1
        except Exception:
            failed += 1
            log.exception("knowledge sync: skipping unreadable entity file %s", path)
    return imported, failed


def _vault_file_exists(vault: Vault, row: KnowledgeEntity) -> bool:
    """Liegt für diese Cache-Zeile noch eine Markdown-Datei im Vault?

    Der Pfad wird allein aus ``id``/``type``/``domain`` der Cache-Zeile rekonstruiert
    (wie ``KnowledgeService._load_from_cache_row``) — der Dateiinhalt wird nicht gelesen,
    damit ein defektes Frontmatter die Existenzprüfung nicht kippt. Lässt sich die Domäne
    einer Zeile nicht auflösen (z.B. Domänen-Datei fehlt), wird die Zeile konservativ
    **behalten** — im Zweifel nichts löschen.
    """
    try:
        domain = vault.load_domain(row.domain)
        placeholder = Entity(id=row.id, type=row.type, title=row.title, domain=row.domain)
        return vault.entity_path(placeholder, domain).exists()
    except Exception:
        log.warning("knowledge reconcile: cannot resolve vault path for '%s', keeping it", row.id)
        return True
