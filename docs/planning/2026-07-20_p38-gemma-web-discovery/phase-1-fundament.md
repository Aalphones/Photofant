# Phase 1 — Fundament: Web-Search-Tool, Capability, Settings, ADR-031

**Komplexität:** heikel (Architektur-Entscheidung: neue externe Abhängigkeit, ADR-Amendment).

> **Geändert am 2026-07-21:** Web-Fakten werden bestätigt statt automatisch geschrieben
> (README, „Vorgeschichte" Punkt 2). ADR-031 regelt deshalb nur noch den **Netzwerkzugriff**;
> die Schreib-Ausnahme von der P27-Kernregel entfällt ersatzlos. Prompt und Ausgabeformat
> liefern jetzt einzelne **Fakten** (Feld/Wert/Quelle/Konfidenz) statt eines fertigen
> Beschreibungs-Absatzes — die Fakten landen in den Merkmalen aus Phase 2.

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
  `# off | auto — kein "ask": die Bestätigung sitzt im Wizard (Fakten abhaken), nicht hier (P38/ADR-031)`
- `SETTINGS_DEFAULTS["ai"]["autonomy"]` um `"discovery": "off"` ergänzen (**Default off** —
  Netzwerkzugriff ist ein bewusster Opt-in, nie Default-Verhalten).

## Aufgabe 3 — Prompt-Library-Eintrag
Neue Datei `backend/photofant/inference/prompts/knowledge_discovery.md`:

```
---
version: 1
---
You are a knowledge assistant with access to live web search results for a person or
entity. Your output is a list of PROPOSALS that a human will review and tick off one by
one — never invent to fill the list. Only state facts that are directly supported by the
provided search snippets. If a snippet is ambiguous or you are not confident, omit the
fact rather than guessing. Fewer, solid facts beat a long, shaky list.

Output format (exact section markers, always all three, use "keine" if a section is empty):

### FAKTEN
<one line per fact, or the single word "keine">
- Feld: <one of the allowed field keys given below, or the word "beschreibung"> | Wert: <the
  value, German, one short phrase — for "beschreibung" 2-5 sentences> | Quelle: <the exact
  URL from the snippets that supports it> | Konfidenz: <0.0-1.0>

### NEUE_ENTITAETEN
<one line per newly discovered related entity, or the single word "keine">
- Titel: <title> | Typ: <one of the allowed entity types given below> | Beziehung: <one of
  the allowed relationship types given below> | Info: <one sentence>

### QUELLEN
<one URL per line, only URLs you actually used>
```

Der Wert `beschreibung` im Feld-Slot ist der Sonderfall für den Freitext-`body` — der Parser
in Phase 3 mappt ihn auf `field: "body"`. Alle anderen Feld-Keys kommen aus den
Merkmals-Definitionen der Domäne (Phase 2) und werden dem Modell im User-Prompt aufgelistet.

## Aufgabe 4 — ADR-031
Neue Datei `docs/decisions/031-web-recherche-netzwerkzugriff.md` — Nummer verifiziert am
2026-07-21 (Platte bis `030`, in `docs/planning/` reserviert bis `031`; Phase 2 dieses Plans
nimmt `032`). Vor dem Anlegen `grep -rn "ADR-0[3-9][0-9]" docs/planning/` erneut laufen lassen,
falls zwischenzeitlich ein anderer Plan entstanden ist:

```markdown
# ADR-031 — Web-Recherche: einziger erlaubter Netzwerkzugriff der Wissensbasis

**Status:** Akzeptiert — 2026-07-21
**Querverweise:** [025](025-knowledge-vault-markdown-wahrheit.md) ·
[027](027-ai-capability-layer.md) · [028](028-gemma-runtime.md) ·
Konzept-ADR-009 (privat/öffentlich-Trennung, in `docs/Konzept-Agentic-Knowledge-Base/` —
nicht die gleichnamige Nummer unter `docs/decisions/`)

## Kontext
P27 legt zwei Kernregeln fest: (1) Gemma schreibt nie ohne Nutzer-Bestätigung, (2) keine
Laufzeit-Netzwerkzugriffe (Offline-Garantie). Die Web-Recherche braucht Regel (2) bewusst
anders. Regel (1) bleibt unangetastet — ein früherer Entwurf sah Auto-Write ohne Rückfrage
vor, der wurde am 2026-07-21 zugunsten des Bestätigungs-Wegs verworfen.

## Entscheidung
Eine neue, einzelne Capability (`KNOWLEDGE_DISCOVERY`) darf bei explizitem User-Klick pro
Entity einen Web-Suchaufruf machen. Ihr Ergebnis sind **Vorschläge**, keine Schreibungen:
die Fakten werden dem Nutzer zum Abhaken vorgelegt, erst die Bestätigung schreibt — mit
`owner=web` (niedrigste Schreibpriorität außer `inferred`, überschreibt nie `user`/`manual`).
Alle anderen P27-Capabilities (`KNOWLEDGE_IMPORT`, `KNOWLEDGE_UPDATE`, `INTERVIEW`) bleiben
offline. Private Domänen sind von `KNOWLEDGE_DISCOVERY` vollständig ausgeschlossen (Guard
wie `import-suggestion`).

## Betrachtete Optionen
- **Auto-Write ohne Rückfrage** (ursprünglicher Entwurf) — weniger Klicks, aber halluzinierte
  Fakten landen ungeprüft in der Ablage und die P27-Kernregel bekäme eine Ausnahme, die
  später jeder als Präzedenzfall zitiert. Verworfen.
- **Netzwerkzugriff generell erlauben** — würde die Offline-Garantie als Ganzes aufweichen.
  Verworfen: der Zugriff bleibt an genau diese eine Capability und einen expliziten Klick
  gebunden.

## Konsequenzen
- Jede bestätigte Übernahme erzeugt Changelog-Einträge + trägt Quell-URLs in
  `entity.sources` — nachvollziehbar, wo ein Wert herkommt.
- `ai.autonomy.discovery` (Default `off`) ist der einzige globale Schalter; ohne ihn explizit
  auf `auto` zu stellen, macht die Anwendung weiterhin keinen einzigen Netzwerkzugriff aus
  der Wissensbasis heraus.
- Kein Agenten-Loop: die Suche läuft deterministisch vor dem Gemma-Call, kein
  Function-Calling (siehe P38-README „Wichtige Funde").
```

## AK dieser Phase
- [x] `ddgs` installiert, API gegen die installierte Version verifiziert (siehe Aufgabe 1).
- [x] `search_web()` liefert bei einer echten Testsuche (`"Tom Hanks actor"`) mindestens 1
      Ergebnis mit gefülltem `title`/`url`/`snippet`.
- [x] `Capability.KNOWLEDGE_DISCOVERY` + `autonomy_for(Capability.KNOWLEDGE_DISCOVERY)`
      liefert `"off"` ohne weitere Settings-Änderung (Default greift).
- [x] `PromptLibrary().get("knowledge_discovery")` liefert den Prompt mit `version == "1"`.
- [x] ADR-031 liegt unter `docs/decisions/031-web-recherche-netzwerkzugriff.md`.

## Doc-Updates
- [x] `docs/code-map.md` — Zeile „KI-Layer / Gemma" um Phase-P38-Hinweis + neue Dateien
      (`web_search.py`, `prompts/knowledge_discovery.md`) ergänzen (nicht neu schreiben,
      anhängen).

## Report-Back

**Status: complete (2026-07-21).**

- **`ddgs` 9.14.4** installiert als Extra-Gruppe `web-discovery`. API gegen die installierte
  Version geprüft: die Rückgabe-Dicts tragen `title` / `href` / `body` — genau die Form, die
  der geplante Code erwartet. **Keine Anpassung nötig**, der `url`/`snippet`-Fallback bleibt
  als Puffer für ältere/spätere Key-Namen drin.
- **Nebenwirkung der Installation:** `uv add` hat die venv wieder auf die Lock-Datei
  synchronisiert. Sie hing vorher an einem alten Repo-Pfad (`B:/photofant/backend`) und trug
  ein von Hand nachinstalliertes `numpy 2.5.1`; beides steht jetzt wieder auf dem
  gelockten Stand (`numpy 2.4.6`, Projekt aus dem aktuellen Pfad). Die Lock-Datei selbst hat
  nur die neuen Websuche-Pakete dazubekommen, keine Versions-Downgrades.
- **AK-Messung** (echte Läufe gegen die installierte Umgebung):
  `autonomy_for(KNOWLEDGE_DISCOVERY)` → `'off'` · `PromptLibrary().get("knowledge_discovery")`
  → `version '1'`, 1138 Zeichen · `search_web("Tom Hanks actor", 3)` → 3 Treffer mit gefülltem
  Titel/URL/Snippet.
- **P27-Amendment:** die Offline-AK im (inzwischen archivierten) P27-Plan trägt jetzt den
  Verweis auf ADR-031 — die Offline-Garantie gilt weiter für alles außer dieser einen,
  per Default abgeschalteten Fähigkeit.
- **Gates:** ruff grün auf allen berührten Dateien. mypy meldet in `capabilities.py` genau
  den **einen vorbestehenden** Fehler (Zeile 100 vor / 104 nach der Änderung — `.get()` auf
  einem TypedDict mit variablem Key) — nicht neu, nicht angefasst.
- **Abweichung vom Plan:** keine inhaltliche. Der Kommentar am neuen Settings-Feld steht über
  der Zeile statt dahinter (die Inline-Variante riss die Zeilenlänge).
