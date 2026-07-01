# Photofant Architecture

## Dokument 060 -- Implementation Roadmap

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# Ziel

Die Roadmap verfolgt drei Ziele:

-   Jede Ausbaustufe ist vollständig nutzbar.
-   Jede Ausbaustufe liefert sichtbaren Mehrwert.
-   Jede Ausbaustufe erweitert die bestehende Architektur, anstatt sie
    zu ersetzen.

------------------------------------------------------------------------

# Priorisierung

Bewertung:

⭐ = gering\
⭐⭐ = mittel\
⭐⭐⭐ = hoch\
⭐⭐⭐⭐ = sehr hoch\
⭐⭐⭐⭐⭐ = extrem hoch

------------------------------------------------------------------------

# Phase 0 -- Architektur

## Ziel

Fundament schaffen.

## Enthält

-   Architektur-Dokumente
-   Datenmodell
-   Knowledge Schema
-   Entity Specification
-   Job Architecture

## Nutzermehrwert

⭐⭐

## Entwicklungsaufwand

⭐⭐

## Architektur-Risiko

⭐⭐⭐⭐⭐

## Priorität

SEHR HOCH

------------------------------------------------------------------------

# Phase 1 -- Knowledge Engine

## Ziel

Generische Wissensbasis schaffen.

## Enthält

-   KnowledgeService
-   Entity Repository
-   Relationship Repository
-   Markdown Vault
-   SQLite Tabellen

## Noch keine KI

Ja

## Nutzermehrwert

⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐

## Risiko

⭐⭐

------------------------------------------------------------------------

# Phase 2 -- Knowledge Wizard (MVP)

## Ziel

Wissen ohne KI aufbauen.

## Enthält

-   Knowledge Queue
-   TODO-System
-   Wizard
-   manuelles Anlegen von Entitäten
-   Markdown erzeugen

## Nutzermehrwert

⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐

## Risiko

⭐

------------------------------------------------------------------------

# Phase 3 -- Photofant Integration

## Ziel

Bilder und Wissen verbinden.

## Enthält

-   Person ↔ Entity Mapping
-   Media Links
-   automatische Knowledge Lookup Jobs
-   neue Events

## Nutzermehrwert

⭐⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐

## Risiko

⭐⭐

------------------------------------------------------------------------

# Phase 4 -- Lore Panel

## Ziel

Die Galerie versteht Inhalte.

## Enthält

-   Lore Panel
-   Rollen
-   Beziehungen
-   Franchises
-   Quellen
-   Verwandte Bilder

## Nutzermehrwert

⭐⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐

## Risiko

⭐⭐

------------------------------------------------------------------------

# Phase 5 -- Recommendation Engine

## Ziel

Kontextbezogene Empfehlungen.

## Enthält

-   Recommendation Jobs
-   Reason Chain
-   Explainability
-   "Warum empfohlen?"
-   "Warum nicht?"

## Nutzermehrwert

⭐⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐

## Risiko

⭐⭐⭐

------------------------------------------------------------------------

# Phase 6 -- Gemma Integration

## Ziel

KI unterstützt die Wissenspflege.

## Enthält

-   Knowledge Import
-   Knowledge Update
-   Interview Mode
-   Patch-Erzeugung

## Wichtig

Gemma schreibt niemals direkt Dateien.

Nur Patches.

## Nutzermehrwert

⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐⭐

## Risiko

⭐⭐⭐

------------------------------------------------------------------------

# Phase 7 -- Creative Jobs

## Ziel

ComfyUI intelligent nutzen.

## Enthält

-   Workflow-Auswahl
-   Capability Mapping
-   Prompt-Erzeugung
-   Bildplanung
-   automatische Referenzsuche

## Nutzermehrwert

⭐⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐⭐

## Risiko

⭐⭐⭐

------------------------------------------------------------------------

# Phase 8 -- Discovery

## Ziel

Photofant entdeckt Zusammenhänge.

## Enthält

-   fehlende Wissenseinträge
-   mögliche Personen
-   Dubletten
-   neue Beziehungen
-   Sammlungsanalysen

## Ausführung

Nur auf Wunsch des Nutzers.

Beispiele:

-   30 Minuten arbeiten
-   60 Minuten arbeiten
-   Bis Queue leer

## Nutzermehrwert

⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐⭐

## Risiko

⭐⭐⭐

------------------------------------------------------------------------

# Phase 9 -- Wissensdomänen

## Ziel

Neue Themen ergänzen.

Beispiele

-   Familie
-   Pokémon
-   Herr der Ringe
-   Geschichte
-   Architektur
-   Tiere

Die Engine bleibt unverändert.

Nur Domains werden ergänzt.

## Nutzermehrwert

⭐⭐⭐⭐⭐

## Entwicklungsaufwand

⭐⭐

## Risiko

⭐

------------------------------------------------------------------------

# MVP Definition

Ein erstes öffentlich nutzbares Photofant 2.0 besteht bereits nach Phase
4.

Enthalten:

-   Knowledge Engine
-   Markdown Vault
-   Knowledge Wizard
-   Personenverknüpfung
-   Lore Panel

Zu diesem Zeitpunkt ist Gemma noch nicht erforderlich.

------------------------------------------------------------------------

# Backlog (später)

-   Mehrsprachigkeit
-   Audiowissen
-   Videoanalyse
-   Kalenderintegration
-   Sprachsteuerung
-   Lokaler Webcrawler
-   Plugin-System für externe Datenquellen

------------------------------------------------------------------------

# Leitregel

Vor jeder neuen Funktion gilt:

1.  Liefert sie echten Mehrwert?
2.  Passt sie zur bestehenden Architektur?
3.  Kann sie als eigenständiger Job umgesetzt werden?
4.  Bleibt Photofant dadurch einfacher statt komplexer?

Wenn eine Frage mit "Nein" beantwortet wird, wird die Funktion
verschoben oder neu entworfen.

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste inkrementelle Roadmap für Photofant 2.0 mit Prioritäten,
Risikoabschätzung und klar definiertem MVP.
