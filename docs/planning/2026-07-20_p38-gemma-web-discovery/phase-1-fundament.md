# Phase 1 — Fundament: Web-Search-Tool, Capability, Settings, ADR-031

**Komplexität:** heikel (Architektur-Entscheidung: neue externe Abhängigkeit, ADR-Amendment).

## Kontext (lesen vor dem Start)
- `backend/photofant/inference/capabilities.py` — `Capability`-Enum, `resolve_generator`,
  `generate()`, `autonomy_for()`, `_AUTONOMY_KEY`-Mapping. Neue Capability reiht sich hier ein.
- `backend/photofant/settings.py` — `AiAutonomySettings` (Zeile ~79), `AiSettings` (~83),
  `SETTINGS_DEFAULTS["ai"]` (~236). Neuer Autonomie-Key `discovery`.
- `backend/photofant/inference/tools.py` — **bewusst nicht anfassen**. `ToolRegistry` ist
  unbenutztes Scaffolding (siehe README „Wichtiger Fund"); die neue Websuche wird direkt vom
  Job aufgerufen, nicht über diese Registry.
- `backend/pyproject.toml` — `[project.optional-dependencies]`, Muster `gemma-gguf` (Zeile
  ~43) für eine neue Extra-Gruppe.
- `docs/decisions/027-ai-capability-layer.md`, `028-gemma-runtime.md` — Format-Vorlage für
  das neue ADR-031.
- `docs/decisions/009-comfyui-default-auto-import.md` (nur die Kopfzeile) — Beispiel, wie ein
  ADR im Header auf ein anderes verweist, das es amendiert.
- `docs/planning/2026-07-01_p27-gemma-integration/README.md` — die zwei Zeilen, die amendiert
  werden (Abschnitt „Aufgaben" unten).

## Aufgabe 1 — Web-Search-Client
Neue Datei `backend/photofant/inference/web_search.py`:

```python
"""Websuche für die Discovery-Capability (P38) — kein Agenten-Loop, kein Tool-Routing.

Wird direkt vom KnowledgeDiscoveryJob aufgerufen (gleiche Direktaufruf-Konvention wie
KnowledgeService in den bestehenden P27-Jobs). Einziger Netzwerkzugriff der Wissensbasis
mit echtem Internet-Bezug — Opt-in pro Aktion (README P38), alle anderen KI-Funktionen
bleiben offline (P27-AK).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


class WebSearchError(RuntimeError):
    """Suche fehlgeschlagen (Netzwerk, Paket fehlt, Rate-Limit) — Job wandelt das in einen
    Job-Fehlerstatus um, kein stiller Fallback wie bei der GGUF-Verfügbarkeitsprüfung."""


def search_web(query: str, max_results: int = 5) -> list[WebSearchResult]:
    try:
        from ddgs import DDGS
    except ImportError as error:
        raise WebSearchError(
            "Websuche nicht verfügbar — Paket fehlt. Install: uv pip install 'photofant[web-discovery]'"
        ) from error

    try:
        with DDGS() as client:
            raw_results = list(client.text(query, max_results=max_results))
    except Exception as error:  # Netzwerk-/Rate-Limit-Fehler der Bibliothek, nicht typisiert
        raise WebSearchError(f"Websuche fehlgeschlagen: {error}") from error

    return [
        WebSearchResult(
            title=item.get("title", ""),
            url=item.get("href", "") or item.get("url", ""),
            snippet=item.get("body", "") or item.get("snippet", ""),
        )
        for item in raw_results
        if item.get("href") or item.get("url")
    ]
```

**Vor dem Weiterbauen verifizieren** (Konfidenz-Ausweis README): `uv add ddgs` im
`backend/`-Verzeichnis, dann in einer Python-Shell `from ddgs import DDGS; list(DDGS().text("test", max_results=2))`
ausführen und die tatsächlichen Dict-Keys der Ergebnisse gegen den Code oben abgleichen
(die Bibliothek hat ihre Rückgabe-Keys schon einmal geändert, `href`/`url` deckt beide
bekannten Varianten ab — ggf. anpassen, falls die installierte Version einen dritten Namen
verwendet). Bei Abweichung: `web_search.py` entsprechend korrigieren, keine Rückfrage nötig,
das ist reine Anpassung an die installierte API, keine Design-Entscheidung.

`pyproject.toml` — neue Extra-Gruppe direkt unter `gemma-gguf` einfügen:
```toml
# 3. Websuche für die Discovery-Capability (P38, ADR-031) — kein API-Key nötig.
web-discovery = [
    "ddgs>=9.0",
]
```

## Aufgabe 2 — Capability + Autonomie
`inference/capabilities.py`:
- `Capability`-Enum um `KNOWLEDGE_DISCOVERY = "knowledge_discovery"` ergänzen.
- `_AUTONOMY_KEY` um `Capability.KNOWLEDGE_DISCOVERY: "discovery"` ergänzen.

`settings.py`:
- `AiAutonomySettings` (TypedDict) um Feld `discovery: str` ergänzen, mit Kommentar:
  `# off | auto — kein "ask": Auto-Write ohne Rückfrage ist der ganze Witz dieser Funktion (P38/ADR-031)`
- `SETTINGS_DEFAULTS["ai"]["autonomy"]` um `"discovery": "off"` ergänzen (**Default off** —
  Websuche + ungefragtes Schreiben ist ein bewusster Opt-in, nie Default-Verhalten).

## Aufgabe 3 — Prompt-Library-Eintrag
Neue Datei `backend/photofant/inference/prompts/knowledge_discovery.md`:

```
---
version: 1
---
You are a knowledge assistant with access to live web search results for a person or
entity. Your output will be written directly into a knowledge base WITHOUT further human
review — be conservative. Only state facts that are directly supported by the provided
search snippets. If a snippet is ambiguous or you are not confident, leave that part out
rather than guessing.

Output format (exact section markers, always all three, use "keine" if empty):

### BESCHREIBUNG
<2-5 sentences, extending or correcting the existing description. Keep correct existing
sentences unchanged. German language.>

### NEUE_ENTITAETEN
<one line per newly discovered related entity, or the single word "keine">
- Titel: <title> | Typ: <one of the allowed entity types given below> | Beziehung: <one of
  the allowed relationship types given below> | Info: <one sentence>

### QUELLEN
<one URL per line, only URLs you actually used>
```

## Aufgabe 4 — ADR-031
Neue Datei `docs/decisions/031-web-discovery-auto-write.md` — Nummer verifiziert (`max(Platte
030, in geparkten Plänen reserviert) + 1`, kein geparkter Plan reserviert eine höhere Nummer
als 030 — kurz gegengrepped: `grep -rn "ADR-0[3-9][0-9]" docs/planning/` vor dem Anlegen
erneut laufen lassen, falls zwischenzeitlich ein anderer Plan entstanden ist):

```markdown
# ADR-031 — Web-Discovery: Auto-Write ohne Bestätigung (Amendment zu ADR-006/ADR-028, Präzisierung von P27)

**Status:** Akzeptiert — 2026-07-20
**Querverweise:** [ADR-006-Regel siehe P27-README] (Gemma ändert nie direkt Daten) ·
[ADR-009](009-comfyui-default-auto-import.md) *(Hinweis: Konzept-ADR-009 in `docs/Konzept-Agentic-Knowledge-Base/`, nicht diese Nummer — privat/öffentlich-Trennung)* ·
[027](027-ai-capability-layer.md) · [028](028-gemma-runtime.md)

## Kontext
P27 legt zwei Kernregeln fest: (1) Gemma schreibt nie ohne Nutzer-Bestätigung, (2) keine
Laufzeit-Netzwerkzugriffe (Offline-Garantie). P38 (Web-Discovery) braucht beides bewusst
anders — Nutzerentscheidung, kein stiller Drift.

## Entscheidung
Eine neue, einzelne Capability (`KNOWLEDGE_DISCOVERY`) darf: (a) bei explizitem User-Klick
pro Entity einen Web-Suchaufruf machen, (b) das Ergebnis ohne Bestätigungs-Dialog direkt
schreiben — mit `owner=web` (niedrigste Schreibpriorität außer `inferred`, überschreibt nie
`user`/`manual`). Alle anderen P27-Capabilities (`KNOWLEDGE_IMPORT`, `KNOWLEDGE_UPDATE`,
`INTERVIEW`) bleiben unverändert bestätigungspflichtig und offline. Private Domänen sind von
`KNOWLEDGE_DISCOVERY` vollständig ausgeschlossen (Guard wie `import-suggestion`).

## Konsequenzen
- Jede Web-Discovery-Schreibung erzeugt einen Changelog-Eintrag + trägt Quell-URLs in
  `entity.sources` — Transparenz ersetzt die fehlende Bestätigung.
- `ai.autonomy.discovery` (Default `off`) ist der einzige globale Schalter; ohne ihn explizit
  auf `auto` zu stellen, ändert sich am bestehenden P27-Verhalten nichts.
- Kein Agenten-Loop: die Suche läuft deterministisch vor dem Gemma-Call, kein
  Function-Calling (siehe P38-README „Wichtiger Fund").
```

## AK dieser Phase
- [ ] `ddgs` installiert, API gegen die installierte Version verifiziert (siehe Aufgabe 1).
- [ ] `search_web()` liefert bei einer echten Testsuche (`"Tom Hanks actor"`) mindestens 1
      Ergebnis mit gefülltem `title`/`url`/`snippet`.
- [ ] `Capability.KNOWLEDGE_DISCOVERY` + `autonomy_for(Capability.KNOWLEDGE_DISCOVERY)`
      liefert `"off"` ohne weitere Settings-Änderung (Default greift).
- [ ] `PromptLibrary().get("knowledge_discovery")` liefert den Prompt mit `version == "1"`.
- [ ] ADR-031 liegt unter `docs/decisions/031-web-discovery-auto-write.md`.

## Doc-Updates
- [ ] `docs/code-map.md` — Zeile „KI-Layer / Gemma" um Phase-P38-Hinweis + neue Dateien
      (`web_search.py`, `prompts/knowledge_discovery.md`) ergänzen (nicht neu schreiben,
      anhängen).

## Report-Back
