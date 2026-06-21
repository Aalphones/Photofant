# ADR-003 — ComfyUI Trigger-Integration (Fire-and-Forget, koexistierend)

**Status:** Akzeptiert · 2026-06-21  
**Querverweise:** [ADR-002](002-generatives-backend.md) (in-process Diffusers vs. ComfyUI als Backend)

---

## Kontext

Photofant benötigt generative Bildoperationen (Upscale, img2img, Inpainting). ADR-002 untersucht, ob diese in-process (torch/diffusers) oder über eine externe ComfyUI-Instanz laufen sollen. ADR-003 beschreibt einen **dritten Weg**, der unabhängig von ADR-002 existiert: Photofant triggert ComfyUI extern, ohne selbst torch/diffusers zu benötigen.

---

## Entscheidung

**ComfyUI-Integration als koexistierender generativer Pfad neben dem in-process-Backend (P9).**

Beide Pfade existieren gleichzeitig und gegaten unabhängig voneinander:

| Pfad | Aktivierung | VRAM-Owner | Modell-Owner |
|---|---|---|---|
| P9 (in-process) | `models.generativ`-Gruppe installiert | Photofant | Photofant |
| P8b (ComfyUI) | `comfyui.enabled = true && Verbindung ok` | ComfyUI | ComfyUI |

Kein Pfad ersetzt den anderen; beide können gleichzeitig aktiv sein.

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
- **Kein Auto-Zurückschreiben:** Photofant rührt `output/` nicht an. Bewusstes Speichern nach §8.2.
- **ComfyUI besitzt Modelle und VRAM:** Kein torch/diffusers-Stack auf Photofant-Seite für diesen Pfad.
- **Gating:** Trigger und Workflow-Dropdown sind disabled, solange `enabled = false` oder Verbindung nicht geprüft (`comfyui_ready = false`).
- **Offline-Garantie:** Nur Verkehr zur konfigurierten (default lokalen) Instanz; kein impliziter externer Call.
- **Koexistenz ohne Doppel-Anzeige:** P8b-Slots und P9-Generativ-Buttons sind in der UI klar getrennt. Keine generische „KI"-Schaltfläche, die beides zusammenwirft.

---

## Warum nicht ComfyUI als das Backend (anstelle P9)?

P9 läuft in-process und braucht keine externe Instanz. P8b benötigt eine laufende ComfyUI-Instanz — ideal für Nutzer, die ComfyUI ohnehin betreiben und dessen Workflow-Ökosystem (GGUF-Nodes, Custom Nodes, Prompt-Bausteine) nutzen wollen. Beide Szenarien sind real; deshalb koexistieren beide Pfade.

---

## Konsequenzen

- Phase 4 des ComfyUI-Plans (`kind = mask`-Slots) hängt an P9 Phase 4 (Masken-Editor). Bis dahin gegated.
- Template-Dateien liegen in einem Photofant-verwalteten `workflows/`-Ordner; die Binding-Konfiguration lebt in der DB.
- Output-Cleanup liegt bei ComfyUI; Photofant löscht oder verwaltet keine `output/`-Dateien.
