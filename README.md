# Photofant

> *„vergisst nie"* — lokale, private Bildverwaltung, vollständig durchsuchbar.

Photofant verwaltet lokal gehaltene Bildsammlungen nach Google-Fotos-Vorbild: Import, Personen-Erkennung, automatisches Tagging und Captioning, semantische Suche, Bild-Editor und Trainingsset-Export. Verarbeitung und Datenhaltung laufen rein lokal über das Dateisystem — keine Cloud, keine Drittdienste zur Laufzeit.

Der Stack: Angular-Frontend, FastAPI-Backend, SQLite als Index. ML-Modelle (Gesichter, Tags, Captions) werden über die App bezogen und laufen lokal per ONNX Runtime; generative Features (Upscale, Edit) sind optional und GPU-gebunden.

## Status

Konzeptphase. Die vollständige Spezifikation steht in [docs/Konzept-Photofant.md](docs/Konzept-Photofant.md), die UI-Prototypen in [docs/design/](docs/design/).

## Quickstart

Noch kein lauffähiger Code — das Grundgerüst (install-/start-Skripte, Backend + Frontend) entsteht in Stage 0, siehe [docs/PROJECT.md](docs/PROJECT.md).

## Mitarbeit / Agenten

Einstiegspunkt für Konventionen und Projektstruktur: [AGENTS.md](AGENTS.md).
