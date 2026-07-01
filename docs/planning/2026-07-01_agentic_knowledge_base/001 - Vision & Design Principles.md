# Photofant Architecture

## Dokument 001 -- Vision & Design Principles

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# 1. Vision

Photofant ist eine vollständig lokale, KI-gestützte Medienverwaltung.

Das Ziel besteht nicht darin, einen Chatbot zu entwickeln.

Das Ziel besteht darin, eine Anwendung zu entwickeln, welche Bilder,
Wissen und KI intelligent miteinander verbindet.

Photofant soll seine Inhalte verstehen.

Nicht nur erkennen.

Nicht nur taggen.

Sondern Beziehungen erkennen, Wissen aufbauen, Empfehlungen aussprechen
und den Nutzer bei kreativen Aufgaben unterstützen.

Dabei bleibt der Nutzer jederzeit Eigentümer seiner Daten und
entscheidet selbst über alle automatischen Änderungen.

------------------------------------------------------------------------

# 2. Grundprinzipien

## Offline First

Alle Kernfunktionen müssen vollständig lokal funktionieren.

Cloud-Dienste dürfen optional ergänzt werden.

Die Architektur darf niemals von einer Internetverbindung abhängig sein.

## User owns the data

Alle Daten gehören ausschließlich dem Nutzer.

Markdown ist die **Single Source of Truth**.

Knowledge Graph, Embeddings und Empfehlungen werden daraus erzeugt.

## Explainable AI

Jede Entscheidung muss nachvollziehbar sein.

Beispiele:

-   Warum wurde dieses Bild empfohlen?
-   Warum wurde diese Person erkannt?
-   Warum wurde dieser Workflow gewählt?

## User has final control

KI schlägt Änderungen vor.

Der Nutzer entscheidet.

Automatische Änderungen sind optional und jederzeit deaktivierbar.

## Lazy Loading

Kein KI-Modell bleibt dauerhaft geladen.

Modelle werden ausschließlich bei Bedarf geladen und nach einer
Leerlaufzeit wieder entladen.

## Modularität

Neue Modelle, Wissensdomänen und Workflows sollen ergänzt werden können,
ohne den Kern der Anwendung zu verändern.

------------------------------------------------------------------------

# 3. Philosophie

Photofant soll sich wie ein intelligenter Assistent verhalten.

Nicht wie ein Chatbot.

Der Nutzer arbeitet mit seiner Medienbibliothek.

KI unterstützt nur dort, wo sie echten Mehrwert liefert.

------------------------------------------------------------------------

# 4. KI-Prinzip

Die KI besitzt niemals dauerhaft Wissen.

Das Wissen befindet sich ausschließlich im Knowledge Vault.

Die KI erhält immer nur den aktuell benötigten Kontext.

------------------------------------------------------------------------

# 5. Knowledge First

Das wichtigste Element ist die Wissensbasis.

Sie besteht aus:

-   Markdown
-   Beziehungen
-   Quellen
-   Bildern
-   Knowledge Graph
-   Embeddings

Das LLM nutzt diese Informationen.

Es ersetzt sie nicht.

------------------------------------------------------------------------

# 6. Jobs statt Agenten

Photofant besitzt keine klassischen Agenten.

Photofant besitzt intelligente Jobs.

Beispiele:

-   Knowledge Import
-   Recommendation
-   Creative Workflow
-   Lore
-   Discovery

Ein Job besitzt:

-   Eingaben
-   Ausgaben
-   Explainability
-   Status

------------------------------------------------------------------------

# 7. Explainability

Jede KI-Entscheidung muss erklärbar sein.

Empfehlungen, Personenerkennung, Workflow-Auswahl und Knowledge-Updates
müssen begründet werden können.

------------------------------------------------------------------------

# 8. Ownership

Jede Information besitzt einen Eigentümer.

Mögliche Eigentümer:

-   User
-   Manual
-   Web
-   Agent
-   Inferred

Benutzereingaben besitzen immer höchste Priorität.

------------------------------------------------------------------------

# 9. Datenschutz

Alle Daten bleiben lokal.

Cloud-Dienste sind ausschließlich optional.

Keine Telemetrie.

------------------------------------------------------------------------

# 10. Erweiterbarkeit

Photofant unterstützt beliebige Wissensdomänen.

Beispiele:

-   Filme
-   Serien
-   Anime
-   Familie
-   Haustiere
-   Reisen
-   Geschichte
-   Fahrzeuge
-   Architektur

------------------------------------------------------------------------

# 11. Schichten

Media Layer

↓

Knowledge Layer

↓

Job Layer

↓

AI Layer

↓

Model Layer

Jede Schicht kennt ausschließlich die direkt darunterliegende Schicht.

------------------------------------------------------------------------

# 12. Zielbild

Photofant soll eine persönliche Wissens- und Medienbibliothek sein.

Nicht nur Bilder anzeigen.

Sondern Inhalte verstehen, Beziehungen erkennen, Kontext liefern und
kreativ unterstützen.

------------------------------------------------------------------------

# 13. Bewusste Nicht-Ziele

-   Kein autonomes KI-System
-   Kein Cloud-Zwang
-   Kein Chatbot
-   Keine Black Box
-   Kein komplexes Agenten-Framework

Photofant bleibt eine lokale Desktop-Anwendung, deren KI den Nutzer
unterstützt -- niemals ersetzt.
