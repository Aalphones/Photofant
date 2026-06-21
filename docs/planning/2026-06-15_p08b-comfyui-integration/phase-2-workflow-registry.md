# P8b · Phase 2 — Workflow-Template-Registry

> Rating: **heikel** (Template-Parsing + Bindung über Titel + Validierung sind der brüchige Kern) · Status: **complete** (2026-06-21)

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Workflow-CRUD, introspect)
- [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) §2, §2a, §5 (Upscale-Beispiel)
- Phase 1 (Client, Settings-Gating)

## Akzeptanzkriterien

- Konfigurationsmodell nach §2.1 in der DB: `id, name, category, template_path, inputs[], params[]`. Template-JSON (**API-Format**, nicht UI-Format) in einen Photofant-verwalteten `workflows/`-Ordner kopiert; Bindungs-Config lebt in der DB.
- **Introspektion** (`POST /api/comfyui/workflows/introspect`): Template parsen, alle Nodes mit `_meta.title` + `class_type` listen; Bild-Eingänge erkennen (`LoadImage`, Mask-Loader, bekannte Custom-Loader); pro erkanntem Eingang einen **Input-Vorschlag** (`key`/`label`/`node_title` vorbefüllt). Titel als Dropdown (Freitext-Fallback).
- Inputs (1..x) nach §2a.3: `key, label, node_title` (**Name-Hook**), `field` (Default `image`), `kind` (`image`/`mask`), `required`, `lockable`. Params (0..x) nach §2a.4: `type` (`float`/`int`/`string`/`enum`), `default`, `min`/`max`/`step`/`options`.
- **Bindung über `_meta.title`**, Node-ID nur Fallback (§2.2).
- **Validierung (kein stummes Scheitern, §2a.5):** jeder `node_title` existiert **und** ist eindeutig (Konflikt → blockiert mit Hinweis); jedes `field` existiert im Zielnode; mind. ein `SaveImage` (sonst Warnung „kein Output in `output/`"). Jeder Fehler nennt erwartet/gefunden/nächster Schritt. Bei Re-Import eines geänderten Templates: nicht mehr passende Bindungen **markieren**, nicht still brechen.
- Verwaltung (§2a.6): Liste mit Status (aktiv/inaktiv/invalide), Aktionen bearbeiten/duplizieren/löschen/aktiv schalten. Aktivierung nur valide **und** Verbindung steht (Gating aus Phase 1). Nur aktive valide Workflows landen im Run-Dropdown (Phase 4).

## Checkliste

- [x] DB-Migration: `comfyui_workflow` (0019) mit JSON-Spalten für inputs/params
- [x] Template-Speicher: Upload → Kopie nach `{data_root_base}/.photofant/workflows/`, Pfad in DB
- [x] Introspektion: API-Format-Parser (`introspect.py`) — Nodes, `_meta.title`, `class_type`, Eingangs-Heuristik (IMAGE_LOADER_CLASSES, MASK_LOADER_CLASSES)
- [x] Validator (`validator.py`) — Titel-Existenz + Eindeutigkeit, Feld-Existenz, SaveImage, Re-Import-Drift (`check_drift`)
- [x] Routes CRUD + introspect + activate/deactivate/duplicate/revalidate (14 Endpoints)
- [x] Frontend: Settings-Workflow-Verwaltung — Upload, Workflow-Karten, Status (aktiv/inaktiv/invalide), Validierungsfehler, Input/Param-Zeilen mit Inline-Aktionen, Edit-Modus
- [x] Tests: 15 Tests (6 Introspection + 9 Validation) — fehlender Titel, doppelter Titel, fehlendes Feld, kein SaveImage, no_binding, node_id-Fallback, UI-Format-Reject
- [x] Doc-Update: README-Kontrakt aktuell; Beispiel-Fixture entfällt (Tests nutzen Inline-Templates)

## Report-Back

**Scope:** Workflow-Template-Registry mit CRUD, Introspektion, Validierung und Settings-UI.

**Backend:**
- Migration 0019: `comfyui_workflow` mit id, name, category, template_path, inputs/params (JSON), is_active, is_valid, validation_errors (JSON), timestamps
- `comfyui/introspect.py`: Erkennt API- vs UI-Format, IMAGE_LOADER_CLASSES (LoadImage, LoadImageMask, ...), generiert InputSuggestion-Objekte
- `comfyui/validator.py`: Prüft Titel-Existenz + Eindeutigkeit, Feld-Existenz, SaveImage-Pflicht; `check_drift()` für Re-Import
- `api/comfyui.py`: 14 Endpoints (Settings + Workflow-CRUD + introspect + activate/deactivate/duplicate/revalidate)

**Frontend:**
- Models: WorkflowInput, WorkflowParam, ComfyUIWorkflow, ValidationError, IntrospectionResult + WORKFLOW_CATEGORIES
- Service: 9 neue Methoden + snake_case→camelCase Mapper
- Store: 20+ Actions, erweiterte State/Reducer/Effects/Selectors
- UI: Workflow-Karten mit Status-Badge, expandierbares Detail-Panel, Input/Param-Verwaltung, Inline-Edit

**Tests:** 15 Unit-Tests (Introspektion + Validation), alle bestehenden 6 ComfyUI-Tests weiterhin grün.

**Abweichungen:** Keine. Beispiel-Fixture nicht als Datei abgelegt — Tests verwenden Inline-Templates.
