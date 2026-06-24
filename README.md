# Photofant

> *„vergisst nie"* — lokale, private Bildverwaltung, vollständig durchsuchbar.

Photofant verwaltet lokal gehaltene Bildsammlungen nach Google-Fotos-Vorbild: Import, Personen-Erkennung, automatisches Tagging und Captioning, semantische Suche, Bild-Editor und Trainingsset-Export. Verarbeitung und Datenhaltung laufen rein lokal über das Dateisystem — keine Cloud, keine Drittdienste zur Laufzeit.

Der Stack: Angular-Frontend, FastAPI-Backend, SQLite als Index. ML-Modelle (Gesichter, Tags, Captions) werden über die App bezogen und laufen lokal per ONNX Runtime; generative Features (Upscale, Edit) sind optional und GPU-gebunden.

## Status

Aktiv in Entwicklung — die Kern-Features stehen: Galerie & Lightbox, Personen-Erkennung mit Review-Queue, automatisches Tagging & Captioning, semantische Suche, Smart-Alben, Bild-Editor (CPU), generative Bearbeitung (Upscale/Edit/Inpainting, GPU-gebunden) inkl. ComfyUI-Anbindung, Modell-Management, Duplikaterkennung und Wartung (Backup, Reconcile).

Im Backlog: Trainingsset-Export, duale Duplikaterkennung, Person-Bulk-Import.

Die vollständige Spezifikation steht in [docs/Konzept-Photofant.md](docs/Konzept-Photofant.md), die UI-Prototypen in [docs/design/](docs/design/), eine Code-Landkarte in [docs/code-map.md](docs/code-map.md).

## Quickstart

**Voraussetzungen:** [uv](https://docs.astral.sh/uv/) · Node 20+ mit npm · Python 3.12

```cmd
# 1. Dependencies installieren (einmalig oder nach Pull)
install.cmd

# 2. App starten (zwei Fenster: Backend + Frontend Dev-Server)
start.cmd
```

- Backend: <http://localhost:8000> · API-Docs: <http://localhost:8000/docs>
- Frontend: <http://localhost:4200>


## Mitarbeit / Agenten

Einstiegspunkt für Konventionen und Projektstruktur: [AGENTS.md](AGENTS.md).
