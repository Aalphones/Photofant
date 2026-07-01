# Photofant Architecture

## Dokument 020 -- Entity Specification

**Version:** 1.0\
**Status:** 🟡 Draft

------------------------------------------------------------------------

# 1. Zweck

Dieses Dokument definiert den Aufbau einer einzelnen Knowledge Entity.

Die Entity ist die kleinste Wissenseinheit im gesamten System.

Alle weiteren Komponenten (Graph, Embeddings, Lore, Empfehlungen, KI)
leiten ihre Informationen aus den Entity-Dateien ab.

Markdown ist die einzige Quelle der Wahrheit.

------------------------------------------------------------------------

# 2. Ziele

Eine Entity muss:

-   für Menschen leicht lesbar sein
-   von Git sauber versioniert werden
-   von Jobs verarbeitet werden können
-   vom LLM verstanden werden
-   automatisch in Graph und Embeddings überführt werden können

------------------------------------------------------------------------

# 3. Ordnerstruktur

Beispiel:

knowledge/

    movies/

    series/

    actors/

    characters/

    locations/

    vehicles/

    weapons/

    buildings/

    organizations/

    events/

    people/

    animals/

Die Ordner dienen ausschließlich der Übersicht.

Der eigentliche Typ wird im Frontmatter definiert.

------------------------------------------------------------------------

# 4. Aufbau einer Entity

Jede Datei besteht aus:

1.  Frontmatter
2.  Inhalt
3.  Quellen
4.  Änderungsverlauf (optional)

------------------------------------------------------------------------

# 5. Frontmatter

Beispiel:

``` yaml
id: actor/robert-downey-jr

type: Actor

title: Robert Downey Jr.

aliases:
  - RDJ

status: Verified

owner: user

confidence: 1.0

domain: Movies

media_links:
  persons:
    - 42

images:
  - asset_1042

sources:
  - imdb
  - wikipedia
```

Regeln:

-   id ist eindeutig und unveränderlich.
-   type kommt aus der Domain.
-   title ist der Anzeigename.
-   aliases dienen der Suche.
-   owner schützt Benutzerdaten.
-   confidence beschreibt automatische Informationen.

------------------------------------------------------------------------

# 6. Beziehungen

Beziehungen werden explizit gespeichert.

Beispiel:

``` yaml
relationships:

  - type: plays
    target: character/tony-stark

  - type: appears_in
    target: movie/iron-man

  - type: member_of
    target: franchise/mcu
```

Der Knowledge Graph wird ausschließlich aus diesen Beziehungen erzeugt.

Ableitbare Beziehungen werden NICHT gespeichert.

------------------------------------------------------------------------

# 7. Inhalt

Der eigentliche Artikel beginnt unterhalb des Frontmatters.

Er bleibt frei editierbar.

Beispiel:

# Robert Downey Jr.

Kurze Beschreibung...

## Filmografie

...

## Trivia

...

## Auszeichnungen

...

------------------------------------------------------------------------

# 8. Quellen

Quellen werden separat verwaltet.

Jede Quelle besitzt:

-   Typ
-   URL oder Beschreibung
-   Datum
-   Vertrauensstufe

Bei Konflikten überschreibt niemals automatisch eine Quelle die andere.

------------------------------------------------------------------------

# 9. Ownership

Eigentümer bestimmen Änderungsrechte.

Priorität:

User

↓

Manual

↓

Web

↓

Inferred

Jobs dürfen User-Einträge niemals überschreiben.

------------------------------------------------------------------------

# 10. Media Links

Entities können mit Photofant verbunden werden.

Beispiel:

``` yaml
media_links:

  persons:
    - 42

  assets:
    - 150
    - 188
```

Dadurch entstehen Verbindungen zwischen Wissensbasis und Galerie.

------------------------------------------------------------------------

# 11. Embeddings

Embeddings werden niemals gespeichert.

Sie werden aus der Markdown-Datei erzeugt.

Ein Neuaufbau muss jederzeit möglich sein.

------------------------------------------------------------------------

# 12. Graph

Der Graph ist ausschließlich ein Cache.

Er wird aus den Relationships erzeugt.

Er darf jederzeit gelöscht werden.

------------------------------------------------------------------------

# 13. KI-Patches

Ein LLM verändert niemals Dateien direkt.

Ein Job fordert stattdessen einen Patch an.

Beispiel:

``` text
Entity
↓

Gemma

↓

Patch

↓

Validator

↓

Markdown Writer

↓

Graph Update
```

Dadurch bleibt jede Änderung nachvollziehbar.

------------------------------------------------------------------------

# 14. Explainability

Jede automatisch erzeugte Änderung besitzt:

-   Grund
-   Quelle
-   Confidence
-   erzeugender Job
-   Zeitstempel

Die UI kann dadurch jede Änderung erklären.

------------------------------------------------------------------------

# 15. Offene Entscheidungen

-   Soll Relationship-Metadaten (z.B. Confidence) unterstützt werden?
-   Soll jede Property eigene Quellen besitzen?
-   Wie werden große Biografien strukturiert?
-   Benötigen Domains eigene Frontmatter-Felder?

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste vollständige Spezifikation einer Entity-Datei als zentrale
Wissenseinheit von Photofant.
