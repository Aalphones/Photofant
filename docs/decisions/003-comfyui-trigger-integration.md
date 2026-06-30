# ADR-003 — ComfyUI Trigger-Integration (Fire-and-Forget, koexistierend)

**Status:** Akzeptiert · 2026-06-21 — **erweitert durch [ADR-008](008-generativ-via-comfyui.md)** (2026-06-29) und [ADR-009](009-comfyui-default-auto-import.md) (2026-06-30)
**Querverweise:** [ADR-002](002-generatives-backend.md) (in-process Diffusers — **ersetzt durch ADR-008**) · [ADR-008](008-generativ-via-comfyui.md) (ComfyUI übernimmt alle generativen Aufgaben) · [ADR-009](009-comfyui-default-auto-import.md) (Default-Workflows importieren automatisch)

---

## Kontext

Photofant benötigt generative Bildoperationen (Upscale, img2img, Inpainting). ADR-002 untersucht, ob diese in-process (torch/diffusers) oder über eine externe ComfyUI-Instanz laufen sollen. ADR-003 beschreibt einen **dritten Weg**, der unabhängig von ADR-002 existiert: Photofant triggert ComfyUI extern, ohne selbst torch/diffusers zu benötigen.

---

## Entscheidung

**ComfyUI-Integration als generativer Pfad — mit P16 der einzige.**

~~Beide Pfade existieren gleichzeitig und gegaten unabhängig voneinander~~ (ADR-002/P9
wurde mit P16 entfernt, siehe [ADR-008](008-generativ-via-comfyui.md)):

| Pfad | Aktivierung | VRAM-Owner | Modell-Owner | Status |
|---|---|---|---|---|
| ~~P9 (in-process)~~ | ~~`models.generativ`-Gruppe installiert~~ | ~~Photofant~~ | ~~Photofant~~ | **entfernt (P16)** |
| P8b/P16 (ComfyUI) | `comfyui.enabled = true && Verbindung ok` | ComfyUI | ComfyUI | **einziger Generativ-Pfad** |

ComfyUI deckt jetzt drei Aufgaben ab: **Fire-and-Forget** (generischer Workflow-Trigger,
wie in diesem ADR beschrieben) **und** die drei festgelegten generativen Aufgaben
(Upscale, Image Edit, Inpaint) über Default-Workflow-Zuordnung aus den Einstellungen.

---

## Architektur: Fire-and-Forget

1. Photofant schickt Bild per `POST /upload/image` an ComfyUI.
2. Photofant patcht das Workflow-Template (deepcopy, niemals das Original mutieren) und feuert `POST /prompt`.
3. ComfyUI rechnet, schreibt Ergebnis in sein `output/`-Verzeichnis.
4. Photofant schickt `{ job_id, prompt_id }` zurück — **kein Auto-Zurückschreiben**.
5. Import ist ein bewusster, separater Schritt (`POST /api/assets/{id}/versions/import`, `type = comfyui`).

---

## Festgehaltene Regeln

- **API-Format-Pflicht:** Nur ComfyUI-API-Format-JSON (nicht das UI-Workflow-JSON) ist patch- und queuebar.
- **Kein Auto-Zurückschreiben im generischen Pfad:** Photofant rührt `output/` bei `POST /api/comfyui/workflows/{key}/run` nicht an. Bewusstes Speichern nach §8.2. Ausnahme: ADR-009 erlaubt Auto-Import nur fuer die drei Default-Workflows.
- **ComfyUI besitzt Modelle und VRAM:** Kein torch/diffusers-Stack auf Photofant-Seite für diesen Pfad.
- **Gating:** Trigger und Workflow-Dropdown sind disabled, solange `enabled = false` oder Verbindung nicht geprüft (`comfyui_ready = false`).
- **Offline-Garantie:** Nur Verkehr zur konfigurierten (default lokalen) Instanz; kein impliziter externer Call.
- **Koexistenz ohne Doppel-Anzeige:** P8b-Slots und P9-Generativ-Buttons sind in der UI klar getrennt. Keine generische „KI"-Schaltfläche, die beides zusammenwirft.

---

## Warum nicht ComfyUI als das Backend (anstelle P9)?

~~P9 läuft in-process und braucht keine externe Instanz. P8b benötigt eine laufende ComfyUI-Instanz —
ideal für Nutzer, die ComfyUI ohnehin betreiben und dessen Workflow-Ökosystem nutzen wollen. Beide
Szenarien sind real; deshalb koexistieren beide Pfade.~~

> **Überholt (P16, ADR-008):** Diese Abwägung hat sich erledigt. ComfyUI ist ab P16 der einzige
> generative Pfad. Nutzer, die generative Features nutzen wollen, betreiben zwingend eine
> ComfyUI-Instanz. Das Workflow-Ökosystem (GGUF-Nodes, Custom Nodes) ist damit vollständig verfügbar.

---

## Konsequenzen

- ~~Phase 4 des ComfyUI-Plans (`kind = mask`-Slots) hängt an P9 Phase 4 (Masken-Editor). Bis dahin gegated.~~ (P16: Inpaint-Maske via Alpha-Embedding, unabhängig von P9)
- ~~Template-Dateien liegen in einem Photofant-verwalteten `workflows/`-Ordner; die Binding-Konfiguration lebt in der DB.~~ (P16: Workflows als Dateien in `.photofant/workflows/`, keine DB-Konfiguration mehr)
- Output-Cleanup liegt im generischen Pfad bei ComfyUI; Photofant löscht oder verwaltet dort keine `output/`-Dateien. ADR-009 begrenzt Cleanup auf erfolgreich importierte Default-Run-Ergebnisse.
