# Photofant Architecture

## Dokument 050 -- User Workflows & UX

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# 1. Ziel

Die Benutzeroberfläche wird aus den Arbeitsabläufen des Nutzers
entwickelt.

Nicht aus einzelnen Fenstern.

Jeder Workflow beschreibt:

-   Auslöser
-   beteiligte Jobs
-   Nutzerinteraktion
-   Ergebnis

------------------------------------------------------------------------

# 2. Grundprinzipien

-   Der Nutzer bleibt jederzeit in Kontrolle.
-   KI arbeitet im Hintergrund.
-   Jede KI-Entscheidung ist erklärbar.
-   Fortschritt ist sichtbar.
-   Komplexität wird nur bei Bedarf gezeigt.

------------------------------------------------------------------------

# 3. Workflow: Foto importieren

Nutzer:

Foto importieren

↓

Jobs:

-   ImportPhotoJob
-   FaceRecognitionJob
-   CaptionJob
-   EmbeddingJob
-   KnowledgeLookupJob

↓

UI:

Importfortschritt

↓

Ergebnis:

Foto erscheint in der Galerie.

Neue Personen oder offene Aufgaben werden dezent angezeigt.

------------------------------------------------------------------------

# 4. Workflow: Neue Person erkannt

Die Person existiert nicht im Knowledge Vault.

UI:

🆕 Neue Person erkannt.

Optionen:

-   Knowledge Wizard öffnen
-   Später erledigen
-   Ignorieren

Der Wizard erzeugt zunächst manuell eine Entity.

Später übernimmt Gemma diesen Dialog.

------------------------------------------------------------------------

# 5. Workflow: Lore Panel

Beim Öffnen eines Bildes erscheint rechts ein Kontextbereich.

Beispiele:

-   Kurzbiografie
-   Rollen
-   Beziehungen
-   Franchises
-   Eigene Bilder
-   Quellen
-   Verwandte Entitäten

Keine Chat-Oberfläche.

Informationen stehen direkt zur Verfügung.

------------------------------------------------------------------------

# 6. Workflow: Empfehlung

Unterhalb des Lore Panels erscheinen Empfehlungen.

Jede Empfehlung besitzt:

-   Vorschaubild
-   Score
-   Warum empfohlen?

Beispiel:

✓ gleiche Person

✓ gleiche Rolle

✓ gleicher Film

✓ CLIP Ähnlichkeit 0.94

Der Nutzer kann jede Empfehlung nachvollziehen.

------------------------------------------------------------------------

# 7. Workflow: Korrektur

Jede automatisch erzeugte Information besitzt:

"Das stimmt nicht"

↓

PatchJob

↓

Knowledge Update

↓

Graph Update

↓

Empfehlungen aktualisieren

Der Nutzer muss keine Markdown-Dateien manuell bearbeiten.

------------------------------------------------------------------------

# 8. Workflow: Creative

Der Nutzer beschreibt eine Aufgabe.

Beispiel:

"Erstelle mich im Iron-Man-Anzug."

↓

CreativeWorkflowJob

↓

Capability wählen

↓

ComfyUI Workflow

↓

Ergebnis

Die technische Umsetzung bleibt verborgen.

------------------------------------------------------------------------

# 9. Workflow: Work Mode

Der Nutzer entscheidet bewusst, wann Hintergrundaufgaben laufen.

Beispiele:

-   30 Minuten arbeiten
-   60 Minuten arbeiten
-   Bis Queue leer
-   Jetzt starten

Keine automatische Nachtverarbeitung.

------------------------------------------------------------------------

# 10. Workflow: Explainability

Jede KI-Entscheidung besitzt:

Warum?

Welche Daten wurden verwendet?

Welcher Job?

Welches Modell?

Wie sicher ist das Ergebnis?

Diese Informationen sind über ein kleines Symbol erreichbar.

------------------------------------------------------------------------

# 11. Workflow: Interview Mode

Private Personen werden nicht recherchiert.

Der Wizard führt einen natürlichen Dialog.

Beispiele:

Wer ist diese Person?

Welche Beziehung besteht?

Welche wichtigen Ereignisse gibt es?

Aus den Antworten entsteht automatisch eine Markdown-Entity.

------------------------------------------------------------------------

# 12. Work Queue

Alle offenen Aufgaben erscheinen gesammelt.

Beispiele:

-   Neue Person
-   Fehlende Wissensseite
-   Empfehlung prüfen
-   Beziehung bestätigen

Der Nutzer entscheidet, wann sie abgearbeitet werden.

------------------------------------------------------------------------

# 13. Designprinzipien

Die Oberfläche soll ruhig bleiben.

Keine Popups.

Keine Chatfenster für Standardaufgaben.

KI tritt nur in Erscheinung, wenn sie echten Mehrwert liefert.

------------------------------------------------------------------------

# 14. Offene Entscheidungen

-   Layout des Lore Panels
-   Darstellung der Explainability
-   Mobile Optimierungen
-   Mehrere gleichzeitige Work Queues

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste Definition der Benutzer-Workflows als Grundlage für die UX von
Photofant.
