# Photofant Architecture

## Dokument 010 -- Knowledge Engine

**Version:** 1.0\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# 1. Zweck

Die Knowledge Engine bildet das Herzstück der Wissensbasis.

Sie verwaltet Wissen unabhängig von Bildern, KI-Modellen oder der
Benutzeroberfläche.

Alle anderen Komponenten greifen ausschließlich über die Knowledge
Engine auf Wissen zu.

------------------------------------------------------------------------

# 2. Verantwortlichkeiten

Die Knowledge Engine ist verantwortlich für:

-   Verwalten von Entitäten
-   Verwalten von Beziehungen
-   Speichern von Quellen
-   Verwalten von Aliasen
-   Verknüpfen mit Medien
-   Bereitstellen einer API für Jobs

Nicht verantwortlich ist sie für:

-   Webrecherche
-   LLM-Aufrufe
-   ComfyUI
-   Empfehlungen
-   Bildanalyse

Diese Aufgaben werden von Jobs erledigt.

------------------------------------------------------------------------

# 3. Single Source of Truth

Die eigentliche Wissensbasis besteht aus Markdown-Dateien.

Markdown ist immer die Wahrheit.

Folgende Daten werden daraus erzeugt:

-   Knowledge Graph
-   Embeddings
-   Suchindex
-   Empfehlungscache

Diese Daten dürfen jederzeit gelöscht und neu aufgebaut werden.

------------------------------------------------------------------------

# 4. Kernobjekte

## Entity

Alles im System ist eine Entity.

Beispiele:

-   Person
-   Schauspieler
-   Figur
-   Film
-   Serie
-   Episode
-   Gebäude
-   Fahrzeug
-   Waffe
-   Tier
-   Ort
-   Ereignis
-   Organisation

Der Kern kennt keine speziellen Klassen.

Er kennt ausschließlich Entity + Type.

------------------------------------------------------------------------

## Relationship

Beziehungen verbinden zwei Entitäten.

Beispiele:

Tony Stark

built

Avengers Tower

Robert Downey Jr.

plays

Tony Stark

Mark VII

appears_in

The Avengers

Relationship-Typen werden nicht im Code definiert, sondern durch
Wissensdomänen.

------------------------------------------------------------------------

## Property

Eigenschaften einer Entity.

Beispiele:

-   Name
-   Beschreibung
-   Geburtsdatum
-   Farbe
-   Gewicht

Jede Property besitzt:

-   Value
-   Source
-   Owner
-   Confidence

------------------------------------------------------------------------

## Alias

Eine Entity kann beliebig viele Aliase besitzen.

Beispiele:

Robert Downey Jr. - RDJ

Tony Stark - Iron Man

Peter Parker - Spider-Man - Spiderman

------------------------------------------------------------------------

## Source

Jede Information besitzt mindestens eine Quelle.

Mögliche Quellen:

-   user
-   manual
-   web
-   inferred
-   import

------------------------------------------------------------------------

## Ownership

Der Eigentümer bestimmt, wer Daten überschreiben darf.

Priorität:

User \> Manual \> Web \> Inferred

------------------------------------------------------------------------

## Confidence

Alle automatisch erzeugten Informationen erhalten einen Confidence-Wert
zwischen 0.0 und 1.0.

Benutzereingaben gelten immer als sicher.

------------------------------------------------------------------------

# 5. Knowledge Domains

Die Engine kennt keine Filme oder Familien.

Domänen definieren lediglich:

-   Entity Types
-   Relationship Types
-   Templates
-   optionale Quellen

Beispiele:

Movies

Family

Pokemon

History

Dadurch bleibt die Engine generisch.

------------------------------------------------------------------------

# 6. Schnittstellen

Die Knowledge Engine stellt ausschließlich Services bereit.

Beispiele:

-   CreateEntity()
-   UpdateEntity()
-   DeleteEntity()
-   FindEntity()
-   CreateRelationship()
-   RemoveRelationship()
-   SearchEntities()

Jobs greifen ausschließlich über diese Services zu.

------------------------------------------------------------------------

# 7. Integration

Die Engine kommuniziert mit:

-   SQLite
-   Markdown Vault

Optional:

-   Graph Cache
-   Vector Index

Die Benutzeroberfläche arbeitet niemals direkt mit Markdown-Dateien.

------------------------------------------------------------------------

# 8. Nicht-Ziele

Die Knowledge Engine:

-   kennt keine KI
-   kennt keine Prompts
-   kennt keine Modelle
-   kennt keine Workflows
-   kennt keine Jobs

Sie verwaltet ausschließlich Wissen.

------------------------------------------------------------------------

# 9. Offene Entscheidungen

-   Exakte Struktur der Entity-Markdown-Datei (Dokument 020)
-   Struktur der Relationship-Typen pro Wissensdomäne
-   Caching-Strategie für Graph und Embeddings
-   API für Batch-Operationen

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste Definition der Knowledge Engine als generischer Kern der
Wissensplattform.
