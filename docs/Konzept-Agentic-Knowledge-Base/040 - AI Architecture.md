# Photofant Architecture

## Dokument 040 -- AI Architecture

**Version:** 1.0\
**Status:** 🟢 Final

------------------------------------------------------------------------

# 1. Zweck

Dieses Dokument beschreibt, wie KI-Komponenten in Photofant integriert
werden.

KI ist niemals das Zentrum der Anwendung.

KI ist ein Werkzeug, das von Jobs bei Bedarf verwendet wird.

------------------------------------------------------------------------

# 2. Grundprinzip

Jobs kennen keine Modelle.

Jobs kennen ausschließlich Fähigkeiten (Capabilities).

``` text
KnowledgeImportJob
        │
        ▼
KnowledgeImport Capability
        │
        ▼
ModelManager
        │
        ▼
Gemma 3
```

Dadurch können Modelle später ausgetauscht werden.

------------------------------------------------------------------------

# 3. Architektur

``` text
Job
 │
 ▼
Capability
 │
 ▼
ModelManager
 │
 ├── Gemma
 ├── CLIP
 ├── Florence
 ├── Flux / ComfyUI
 ├── Embedding Model
 └── OCR
```

------------------------------------------------------------------------

# 4. ModelManager

Der ModelManager besitzt folgende Aufgaben:

-   Modelle laden
-   Modelle entladen
-   VRAM verwalten
-   Warteschlangen koordinieren
-   Fähigkeiten auf Modelle abbilden
-   Status überwachen

Jobs greifen niemals direkt auf Modelle zu.

------------------------------------------------------------------------

# 5. Lazy Loading

Alle Modelle werden ausschließlich bei Bedarf geladen.

Ablauf:

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

Dadurch kann Photofant dauerhaft laufen ohne GPU dauerhaft zu belegen.

------------------------------------------------------------------------

# 6. Capability Registry

Capabilities beschreiben, WAS benötigt wird.

Beispiele:

-   FaceRecognition
-   TextGeneration
-   VisionAnalysis
-   KnowledgeImport
-   CaptionImage
-   Embedding
-   SemanticSearch
-   ImageGeneration
-   Upscale
-   Inpaint

Der Job fordert ausschließlich eine Capability an.

------------------------------------------------------------------------

# 7. Tool Registry

Capabilities bestehen aus Tools.

Beispiele:

-   ReadMarkdown
-   WriteMarkdown
-   SearchKnowledge
-   SearchImages
-   CreateEmbedding
-   RunWorkflow
-   PatchEntity
-   DownloadSources
-   ValidatePatch

Tools kapseln sämtliche Implementierungsdetails.

------------------------------------------------------------------------

# 8. Modelle

## Gemma

Verwendung:

-   Knowledge Import
-   Knowledge Update
-   Interview Mode
-   Lore
-   Zusammenfassungen

Nicht verwenden für:

-   SQL
-   Graphsuche
-   Empfehlungen
-   einfache Filter

------------------------------------------------------------------------

## CLIP

-   Embeddings
-   semantische Bildsuche
-   Bildähnlichkeit

------------------------------------------------------------------------

## Florence

-   Captioning
-   Objekterkennung

------------------------------------------------------------------------

## Flux / ComfyUI

-   Bildgenerierung
-   Inpainting
-   Outpainting
-   Upscaling
-   kreative Workflows

------------------------------------------------------------------------

## Embedding Modell

Erzeugt Vektoren für Markdown.

Der Vektorindex kann jederzeit neu erzeugt werden.

------------------------------------------------------------------------

# 9. Creative Workflows

ComfyUI wird ebenfalls als Capability betrachtet.

Der Job sagt:

"Ich benötige ImageGeneration."

Der ModelManager wählt anschließend:

-   Workflow
-   Modelle
-   Parameter

Der Job kennt keine Nodes.

------------------------------------------------------------------------

# 10. Prompt Library

Prompts liegen nicht im Code.

Sie werden als Markdown gespeichert.

Beispiele:

prompts/

knowledge-import.md

knowledge-update.md

creative.md

interview.md

recommendation.md

------------------------------------------------------------------------

# 11. Interview Mode

Private Entitäten werden nicht recherchiert.

Stattdessen führt Gemma einen Dialog.

Antworten werden in Markdown überführt.

Dadurch können auch Familienmitglieder oder Haustiere Teil der
Wissensbasis werden.

------------------------------------------------------------------------

# 12. Explainability

Jeder KI-Aufruf liefert zusätzlich:

-   verwendetes Modell
-   verwendete Capability
-   Prompt-Version
-   Bearbeitungsdauer
-   Confidence
-   Begründung

Diese Informationen können in der UI angezeigt werden.

------------------------------------------------------------------------

# 13. Nicht-Ziele

Die KI:

-   kennt keine Datenbank
-   schreibt keine Dateien
-   kennt keine UI
-   verändert keine Daten direkt

Sie liefert ausschließlich Ergebnisse oder Patches.

------------------------------------------------------------------------

# 14. Offene Entscheidungen

-   gleichzeitiges Laden mehrerer Modelle
-   Modell-Prioritäten
-   globale Idle-Zeit
-   GPU-Auslastungsstrategie
-   Prompt-Versionierung

------------------------------------------------------------------------

# Changelog

## Version 1.0

Erste Definition der KI-Architektur mit ModelManager, Capability
Registry und konsequentem Lazy Loading.
