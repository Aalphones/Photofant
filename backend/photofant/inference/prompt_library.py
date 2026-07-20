"""Prompt library — versioned Markdown prompts for AI capabilities (Dok 040 §10).

Prompts live as Markdown files with a tiny frontmatter header (`version:`).
Keeping them versioned files (not string constants) gives the explainability
payload a `prompt_version` and lets a prompt change be reviewed like code.

Resolution: `ai.promptLibraryPath` if it points at a real directory (user
override), else the prompts bundled with the app. Bundled defaults ship in the
repo so a fresh install has working prompts offline without any seeding step.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from photofant.settings import load_settings

log = logging.getLogger(__name__)

_BUNDLED_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    """One prompt: its name (filename stem), version header, and body text."""

    name: str
    version: str
    text: str


def _library_dir() -> Path:
    """The active prompt directory — user override if valid, else bundled defaults."""
    configured = load_settings()["ai"].get("promptLibraryPath") or ""
    if configured:
        override = Path(configured)
        if override.is_dir():
            return override
        log.warning("ai.promptLibraryPath %r is not a directory — using bundled prompts", configured)
    return _BUNDLED_DIR


def _parse(raw: str) -> tuple[str, str]:
    """Split a prompt file into (version, body). Missing header → version '0', full text as body."""
    if raw.startswith("---"):
        _, _, rest = raw.partition("---")
        header, sep, body = rest.partition("---")
        if sep:
            version = "0"
            for line in header.splitlines():
                key, colon, value = line.partition(":")
                if colon and key.strip() == "version":
                    version = value.strip()
                    break
            return version, body.strip()
    return "0", raw.strip()


class PromptLibrary:
    """Loads versioned prompts from the active directory. Cheap enough to build per use."""

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or _library_dir()

    def get(self, name: str) -> Prompt | None:
        path = self._dir / f"{name}.md"
        if not path.is_file():
            log.warning("Prompt %r not found in %s", name, self._dir)
            return None
        version, text = _parse(path.read_text(encoding="utf-8"))
        return Prompt(name=name, version=version, text=text)

    def list(self) -> list[Prompt]:
        prompts: list[Prompt] = []
        for path in sorted(self._dir.glob("*.md")):
            version, text = _parse(path.read_text(encoding="utf-8"))
            prompts.append(Prompt(name=path.stem, version=version, text=text))
        return prompts
