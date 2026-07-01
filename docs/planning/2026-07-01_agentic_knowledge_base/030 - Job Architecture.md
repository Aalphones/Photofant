# Photofant Architecture

## Dokument 030 -- Job Architecture

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# 1. Zweck

Dieses Dokument definiert die Job-Architektur von Photofant.

Photofant verwendet keine klassischen Agenten.

Stattdessen werden alle intelligenten Aufgaben als Jobs innerhalb der
bestehenden Job Queue ausgeführt.

Dadurch bleibt die Architektur einfach, nachvollziehbar und
ressourcenschonend.

------------------------------------------------------------------------

# 2. Grundprinzip

Jede Aktion beginnt mit einem Event.

Ein Event erzeugt einen oder mehrere Jobs.

Jobs können weitere Jobs planen.

Jobs dürfen niemals direkt andere Events auslösen.

``` text
PhotoImported
      │
      ▼
ImportPhotoJob
      │
      ▼
FaceRecognitionJob
      │
      ▼
KnowledgeLookupJob
      │
      ▼
RecommendationUpdateJob
```

------------------------------------------------------------------------

# 3. Aufbau eines Jobs

Jeder Job besitzt:

-   JobId
-   ParentJobId
-   JobType
-   Priority
-   Status
-   CreatedAt
-   StartedAt
-   FinishedAt

Optional:

-   Explainability
-   DecisionLog
-   Result

------------------------------------------------------------------------

# 4. Lebenszyklus

Pending

↓

Queued

↓

Running

↓

Completed

oder

Failed

oder

Cancelled

------------------------------------------------------------------------

# 5. Explainability

Jeder intelligente Job liefert zusätzlich eine Begründung.

Beispiel:

KnowledgeImportJob

Grund:

"Person wurde erstmals erkannt."

Oder

RecommendationJob

Grund:

"Empfohlen wegen gleicher Rolle und CLIP Score 0.94."

Diese Informationen werden später im Lore Panel angezeigt.

------------------------------------------------------------------------

# 6. Jobtypen

## Import

-   ImportPhotoJob
-   ImportMetadataJob

## Analyse

-   FaceRecognitionJob
-   CaptionJob
-   EmbeddingJob

## Knowledge

-   KnowledgeLookupJob
-   KnowledgeImportJob
-   KnowledgeUpdateJob
-   RelationshipUpdateJob

## UI

-   LoreJob
-   RecommendationJob

## Creative

-   CreativeWorkflowJob
-   UpscaleJob
-   InpaintJob

## Wartung

-   RebuildGraphJob
-   RebuildEmbeddingsJob
-   CuratorJob

------------------------------------------------------------------------

# 7. Jobs statt Agenten

Ein "Agent" ist lediglich ein intelligenter Job.

Beispiel:

KnowledgeImportJob

führt intern aus:

1.  Knowledge Lookup
2.  Quellen sammeln
3.  (später) Gemma verwenden
4.  Patch erzeugen
5.  Validator
6.  Markdown aktualisieren

Der Rest des Systems kennt nur den Job.

------------------------------------------------------------------------

# 8. Verwendung von KI

Jobs entscheiden selbst, ob KI benötigt wird.

Viele Jobs benötigen keinerlei LLM.

Beispiele:

-   SQL-Abfrage
-   Graphsuche
-   Relationship Update

Nur komplexe Aufgaben laden Gemma.

------------------------------------------------------------------------

# 9. Lazy Loading

Benötigt ein Job ein Modell:

Job

↓

ModelManager

↓

Modell laden

↓

Inference

↓

Idle Timer

↓

VRAM freigeben

Der Job kennt niemals konkrete Modelle.

------------------------------------------------------------------------

# 10. Job-Ketten

Jobs dürfen Folgejobs erzeugen.

Beispiel:

PersonConfirmedJob

↓

KnowledgeLookupJob

↓

KnowledgeImportJob

↓

RelationshipUpdateJob

↓

RecommendationUpdateJob

------------------------------------------------------------------------

# 11. Endlosschleifen verhindern

Folgende Regeln gelten:

-   Jobs erzeugen Jobs, niemals Events.
-   Jeder Job besitzt ParentJobId.
-   Jeder Job besitzt Depth.
-   Maximale Depth ist konfigurierbar.
-   Ein Job darf keine Instanz seines eigenen Typs erneut erzeugen.
-   Jobs arbeiten idempotent.

Dadurch bleiben rekursive Schleifen ausgeschlossen.

------------------------------------------------------------------------

# 12. Work Mode

Aufwändige Jobs werden ausschließlich auf Wunsch des Nutzers gestartet.

Beispiele:

-   Queue komplett abarbeiten
-   30 Minuten arbeiten
-   60 Minuten arbeiten
-   Bis Queue leer

Keine automatische nächtliche Verarbeitung.

------------------------------------------------------------------------

# 13. MVP

Vor Gemma existiert ein manueller Workflow.

KnowledgeLookupJob

↓

Knowledge Wizard

↓

Benutzer ergänzt Informationen

↓

Markdown erzeugen

Später ersetzt Gemma lediglich den Wizard.

Die Architektur bleibt identisch.

------------------------------------------------------------------------

# 14. Nicht-Ziele

Jobs:

-   speichern keine Daten direkt
-   ändern keine Markdown-Dateien direkt
-   kennen keine SQLite-Tabellen
-   kennen keine UI

Sie verwenden ausschließlich Services.

------------------------------------------------------------------------

# 15. Offene Entscheidungen

-   Priorisierung konkurrierender Jobs
-   Batch-Jobs
-   Abbruchstrategie langer Jobs
-   Retry-Verhalten
-   Zeitlimits einzelner Jobs

------------------------------------------------------------------------

# Changelog

## Version 1.0

Definition der intelligenten Job-Architektur als Weiterentwicklung der
bestehenden Photofant Job Queue.
