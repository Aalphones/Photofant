# Photofant Architecture

## Dokument 080 -- Architectural Decision Record (ADR)

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# Zweck

Dieses Dokument hält die wichtigsten Architekturentscheidungen fest.

Es beantwortet nicht nur **was** entschieden wurde, sondern vor allem
**warum**.

Neue Architekturentscheidungen werden ausschließlich hier ergänzt.

------------------------------------------------------------------------

# ADR-001

## Entscheidung

Markdown ist die Single Source of Truth.

## Begründung

-   menschenlesbar
-   Git-freundlich
-   langlebig
-   unabhängig von Datenbanken

## Konsequenzen

Graph, Embeddings und Suchindizes sind jederzeit neu erzeugbar.

------------------------------------------------------------------------

# ADR-002

## Entscheidung

SQLite bleibt zentrale Datenbank.

## Begründung

-   bereits vorhanden
-   schnell
-   einfach wartbar
-   keine zusätzliche Infrastruktur

Eine Graphdatenbank wird bewusst nicht eingeführt.

------------------------------------------------------------------------

# ADR-003

## Entscheidung

Jobs statt Agenten.

## Begründung

Photofant besitzt bereits eine Job Queue.

Intelligente Jobs erweitern die bestehende Architektur ohne zusätzliches
Framework.

------------------------------------------------------------------------

# ADR-004

## Entscheidung

Alle Modelle verwenden Lazy Loading.

## Begründung

-   geringe GPU-Auslastung
-   Photofant kann dauerhaft laufen
-   RTX 3060 bleibt ausreichend

Kein Modell bleibt dauerhaft im VRAM.

------------------------------------------------------------------------

# ADR-005

## Entscheidung

Jobs kennen Fähigkeiten (Capabilities), keine Modelle.

## Begründung

Modelle bleiben austauschbar.

Neue Modelle können ergänzt werden, ohne Jobs anzupassen.

------------------------------------------------------------------------

# ADR-006

## Entscheidung

LLMs verändern niemals Daten direkt.

## Begründung

LLMs erzeugen ausschließlich Patches.

Persistenz erfolgt ausschließlich über Services.

Dadurch bleiben Änderungen nachvollziehbar.

------------------------------------------------------------------------

# ADR-007

## Entscheidung

Explainability ist Pflicht.

## Begründung

Jede Empfehlung und jede KI-Entscheidung muss erklärt werden können.

Die UI bietet deshalb "Warum?"-Informationen sowie
Korrekturmöglichkeiten.

------------------------------------------------------------------------

# ADR-008

## Entscheidung

Der Nutzer behält immer die Kontrolle.

## Begründung

Automatisierungen sind hilfreich, aber niemals verpflichtend.

Alle intelligenten Jobs können:

-   nachfragen
-   automatisch arbeiten
-   deaktiviert werden

Diese Einstellung ist pro Funktion konfigurierbar.

------------------------------------------------------------------------

# ADR-009

## Entscheidung

Private und öffentliche Wissensquellen werden getrennt behandelt.

## Begründung

Öffentliche Entitäten können recherchiert werden.

Private Entitäten entstehen über einen Interview-Wizard und werden
niemals automatisch mit Webdaten vermischt.

------------------------------------------------------------------------

# ADR-010

## Entscheidung

Discovery-Jobs laufen niemals ungefragt.

## Begründung

Der Nutzer startet bewusst Arbeitsphasen:

-   30 Minuten
-   60 Minuten
-   Bis Queue leer

Photofant arbeitet nicht selbstständig im Hintergrund.

------------------------------------------------------------------------

# ADR-011

## Entscheidung

Die Architektur bleibt generisch.

## Begründung

Filme sind nur eine Wissensdomäne.

Weitere Domänen können ergänzt werden:

-   Familie
-   Tiere
-   Architektur
-   Geschichte
-   Fahrzeuge
-   Spiele

Die Engine bleibt unverändert.

------------------------------------------------------------------------

# ADR-012

## Entscheidung

Vor jeder neuen Funktion werden vier Fragen beantwortet.

1.  Liefert sie echten Mehrwert?
2.  Passt sie zur bestehenden Architektur?
3.  Kann sie als eigenständiger Job umgesetzt werden?
4.  Erhöht sie die Komplexität unnötig?

Nur wenn diese Fragen positiv beantwortet werden, wird die Funktion
umgesetzt.

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste Sammlung der grundlegenden Architekturentscheidungen für
Photofant.
