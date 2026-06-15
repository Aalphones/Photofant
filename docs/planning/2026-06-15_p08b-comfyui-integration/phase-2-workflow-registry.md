# P8b · Phase 2 — Workflow-Template-Registry

> Rating: **heikel** (Template-Parsing + Bindung über Titel + Validierung sind der brüchige Kern) · Status: pending

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

- [ ] DB-Migration: `comfyui_workflow` + `inputs`/`params` (JSON-Spalten oder Subtabellen)
- [ ] Template-Speicher: Upload → Kopie nach `workflows/`, Pfad in DB
- [ ] Introspektion: API-Format-Parser (Nodes, `_meta.title`, `class_type`, Eingangs-Heuristik)
- [ ] Validator (Titel-Existenz + Eindeutigkeit, Feld-Existenz, SaveImage, Re-Import-Drift-Markierung)
- [ ] Routes CRUD + introspect + activate (mit Validierungs-Gate)
- [ ] Frontend: Settings-Workflow-Verwaltung (Anlegen, Auto-Vorschlag bestätigen/anpassen, Input/Param-Zeilen, Validierungs-Feedback, Status-Liste)
- [ ] Tests: Introspektion gegen ein Beispiel-Template; Validator-Fälle (fehlender Titel / doppelter Titel / fehlendes Feld / kein SaveImage / Drift bei Re-Import)
- [ ] Doc-Update: README-Kontrakt; Beispiel-Workflow-Config (§5) als Fixture ablegen

## Report-Back
