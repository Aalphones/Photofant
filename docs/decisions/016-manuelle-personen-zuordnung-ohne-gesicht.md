# ADR-016 — Manuelle Personen-Zuordnung ohne Gesicht: physischer Move/Copy statt DB-only-Tag

**Status:** Akzeptiert · 2026-07-02
**Querverweise:** P30 (Lightbox — Personenzuordnung ohne Gesicht), Phase 1.

## Kontext

Bilder ohne extrahiertes Gesicht (Hinterkopf, zu weit weg, gescheiterte Extraktion) lassen
sich aktuell keiner Person zuordnen — die Gesichter-Sektion verschwindet einfach. Ein neuer
Endpoint soll das Asset direkt (ohne Umweg über ein Face) einer Person zuweisen.

## Optionen

| Option | Beschreibung |
|---|---|
| **A — physischer Move/Copy über `materialize_assignment`** | Wiederverwendet dieselbe Logik wie die Face-Zuordnung: Datei landet physisch im Ordner der Zielperson, `AssetInstance` mit `fixed_person=True`. |
| B — schlanker DB-only-Tag | Nur eine DB-Zeile „Asset X gehört zu Person Y", keine Datei bewegt sich. Weniger I/O, aber Datei bleibt im `_unknown`-Ordner — inkonsistent zu jeder Face-basierten Zuordnung, die immer physisch verschiebt. |

## Entscheidung

**Option A.** `materialize_assignment` (`backend/photofant/media/person_folders.py:236`)
macht bereits alles Nötige und ist bereits Face-unabhängig (`AssetInstance` referenziert kein
Face) — reiner Wiederverwendungs-Task, kein neuer Move/Copy-Pfad. Ein DB-only-Tag würde eine
zweite, abweichende Zuordnungs-Semantik einführen (Datei bleibt bei „Unbekannt", obwohl die
Person feststeht) — Inkonsistenz gegenüber dem etablierten Verhalten, kein Aufwands-Gewinn,
der das rechtfertigt.

## Konsequenzen

- Kein neuer Code-Pfad für Datei-Bewegung — Endpoint ruft `materialize_assignment(..., fixed=True)`
  in einem Thread auf, identisch zum Muster in `reassign_face`.
- 500 bei physischem Fehlschlag (Datei fehlt/IO-Fehler) ist möglich, wie bei jeder
  Face-Zuordnung auch — kein Sonderfall für den Asset-ohne-Face-Pfad.
