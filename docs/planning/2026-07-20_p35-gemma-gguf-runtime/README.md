# P35 — Gemma-GGUF-Runtime (llama.cpp-Adapter hinter derselben Fähigkeit)

> Ergänzt (widerruft **nicht**) ADR-028. Dort steht: „bleibt GGUF nötig, ist es ein **neuer
> Adapter hinter derselben Capability** — kein Job und keine Lifecycle-Mechanik ändert sich, die
> Naht ist gebaut." Genau das wird hier gebaut. *(private, lean.)*

## Ziel
Ein vorhandenes lokales GGUF-Gemma (`D:\Models\OBLITERATUS\Gemma-4-12B-OBLITERATED`,
12B Q4_K_M) als Textgenerator einhängen, **ohne** die P27-Architektur anzufassen. Jobs fordern
weiter eine *Fähigkeit* (`TEXT_GENERATION` etc.), das Routing wählt nach Modell-Format den
richtigen Adapter. torch/transformers-Weg (ADR-028) bleibt vollständig funktionsfähig — GGUF ist
eine **zweite Runtime daneben**, nicht ein Ersatz.

## Zentrale Sicherheitsregel (unverändert)
Der Patch → Validator → Bestätigung → Service-Write-Pfad aus P22/P27 bleibt **komplett
unberührt**. GGUF ist nur eine neue Text-*Quelle* hinter `TextGenerator` — es ändert nichts daran,
wie oder was geschrieben wird. Offline-Garantie: das Modell ist ein In-Place-Bind, kein Download,
kein Laufzeit-Netz.

## Scope
**Drin:** `llama-cpp-python`-Dependency (eigene Extra-Group) · GGUF-Lifecycle-Engine
(`inference/gguf_engine.py`, analog `GenerativeEngine`: lazy-load, ein Modell resident,
idle-unload) · Adapter `inference/adapters/gemma_gguf.py` (`TextGenerator`) · **VRAM-Koordination**
zwischen den zwei Runtimes (genau ein Heavy-Modell resident über beide) · Format-Weiche im Routing
· Manifest-Eintrag + In-Place-Bind fürs 12B-GGUF · **Vision-Naht vorgesehen** (mmproj optional
ladbar + `VisionTextGenerator`-Protocol definiert) · ADR-029.
**Draußen (später billig nachrüstbar, weil die Naht steht):** eine tatsächliche Vision-*Fähigkeit*
(Caption-/Bildfrage-Job, UI-Aktion) — heute nutzt keine Capability Bild-Input · GGUF-Download über
die UI (nur In-Place-Bind, das Modell liegt schon).

## Kontrakt (Naht zwischen den Modulen)
- **`TextGenerator`-Protocol** ([inference/interfaces.py:108](../../../backend/photofant/inference/interfaces.py#L108))
  ist die Text-Naht. `GemmaGgufAdapter` erfüllt `model_id: str` + `generate(prompt, *, system, max_new_tokens) -> str`. Keine Job-/Capability-/Explainability-Änderung.
- **Vision-Naht (definiert, noch nicht konsumiert):** `VisionTextGenerator(TextGenerator)` — erweitert den Text-Vertrag um `generate_with_image(image, prompt, *, system, max_new_tokens) -> str`. Muster exakt wie `TextEmbedder(Embedder)` ([interfaces.py:82](../../../backend/photofant/inference/interfaces.py#L82)): ein Adapter kann Vision, ohne dass ein Aufrufer sie heute nutzt. Ein Konsument prüft die Fähigkeit per `isinstance(gen, VisionTextGenerator)` — genau wie der Code es bei `TextEmbedder` tut.
- **Format-Weiche:** `resolve_generator` ([inference/capabilities.py:62](../../../backend/photofant/inference/capabilities.py#L62))
  liest den Manifest-`format` des gebundenen Modells und gibt `resolve_gemma` (safetensors) **oder** `resolve_gemma_gguf` (gguf) zurück. Der Aufrufer (`generate`) merkt nichts.
- **VRAM-Invariante:** über **beide** Runtimes ist **genau ein** Heavy-Modell resident. Durchsetzung: gegenseitiges Cross-Unload vor dem Laden (Details Phase 1, festgelegt in ADR-029).

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | GGUF-Runtime + Adapter + VRAM-Koordination | heikel (2. Runtime, Concurrency/VRAM, ADR) | complete |
| 2 | Format-Routing + Manifest-Eintrag + In-Place-Bind | standard | pending |
| 3 | Docs (ADR-029, ADR-028-Nachtrag, code-map, models.md) + Test | mechanisch | pending |

## Finale AK (Gesamt)
- [ ] Ein Job mit Fähigkeit `TEXT_GENERATION` läuft gegen das gebundene GGUF-Modell und liefert Text — **ohne** Änderung am Job-Code.
- [ ] Während das GGUF-Modell resident ist, ist **kein** torch-Captioner resident und umgekehrt (VRAM-Invariante nachweisbar via `nvidia-smi`).
- [ ] Nach `ai.idleTimeoutSeconds` Leerlauf wird das GGUF-Modell entladen, VRAM fällt zurück.
- [ ] Das Umstellen zwischen safetensors-Gemma und GGUF-Gemma ist eine **Settings-/Bind-Änderung**, kein Code-Eingriff.
- [ ] torch/transformers-Pfad (ADR-028, JoyCaption/Qwen-VL/safetensors-Gemma) funktioniert unverändert.
- [ ] Offline gewahrt: das Modell ist ein In-Place-Bind auf den lokalen Pfad, kein Laufzeit-Netz.
- [ ] **Vision-Naht steht:** `VisionTextGenerator` ist definiert; die GGUF-Engine kann einen `mmproj` optional mitladen; der GGUF-Adapter erfüllt `VisionTextGenerator`, wenn ein mmproj gebunden ist. **Keine** Fähigkeit/Job nutzt Bild-Input — die Nachrüstung eines Vision-Jobs braucht **keinen** Runtime- oder Adapter-Umbau (nachweisbar: ein `isinstance`-Check reicht als Konsument).

## Smoke-Checkliste (du prüfst am Plan-Ende — Wackelstellen zuerst)
1. **[Wackelstelle] `llama-cpp-python` mit CUDA installierbar?** Nach Phase 1: `cd backend && uv run python -c "from llama_cpp import Llama; print('ok')"` — importiert es? Und lädt das 12B-Q4 auf die GPU (nicht CPU-Fallback)? Prüfen: beim ersten `generate` zeigt der llama.cpp-Log `offloaded N/N layers to GPU`.
2. **[Wackelstelle] VRAM-Wechsel sauber:** einen Text-Job auslösen (GGUF lädt), dann einen Bild-Caption-Job (torch) — `nvidia-smi` zeigt, dass GGUF entladen wird, bevor der Captioner lädt. Kein OOM.
3. **[Wackelstelle] Chat-Template greift:** Der abliterierte GGUF liefert auf einen Import-Prompt sinnvollen Text, nicht Rohsalat — d.h. llama.cpp findet das eingebettete Chat-Template.
4. Idle: Modell nach `ai.idleTimeoutSeconds` weg (VRAM-Anzeige fällt).
5. Manifest-Bind: das GGUF taucht in der Modell-Verwaltung als gebunden/aktiv auf; `ai.gemmaModel` zeigt darauf.
6. **[Wackelstelle, Vision-Naht] mmproj lädt?** Nach Phase 1/2: mit gebundenem `mmproj` einmal `generate_with_image` gegen ein Testbild — kommt eine bildbezogene Antwort (Naht scharf), oder wirft der Handler (Gemma-3-Vision noch nicht in dieser llama.cpp-Version)? Beides ist ein gültiges Ergebnis; der Text-Kern ist davon unberührt.

## Risiken & Konfidenz-Ausweis
- 🟡 **`llama-cpp-python` CUDA-Build auf Windows** (unsicherste Stelle) — `uv` muss ein CUDA-Wheel ziehen, sonst CPU-only = für 12B unbrauchbar langsam. Check: siehe Smoke #1; Plan B in Phase 1 (prebuilt-CUDA-Wheel-Index als Install-Quelle dokumentieren).
- 🟡 **VRAM-Koexistenz** — 12B-Q4 (~8 GB) + kurzzeitige Überlappung beim Runtime-Wechsel könnte die 3060 (12 GB) sprengen, wenn Cross-Unload nicht *vor* dem Laden greift. Check: Smoke #2. Mitigation: Cross-Unload synchron vor dem `Llama(...)`-Konstruktor.
- 🟡 **12B statt eingeplanter 4B** — mehr VRAM, langsamer. Kein Blocker (Q4 passt allein), aber Koexistenz enger als bei 4B.
- 🟡 **Gemma-3-mmproj-Handler in llama-cpp-python** (Vision-Naht) — der konkrete Chat-Handler für Gemma-3-Vision (nicht der LLaVA-Handler) ist umsetzungs-/versionsabhängig. Die Naht reicht nur den `mmproj_path` durch; **ob** llama.cpp Gemma-3-Vision heute lädt, klärt Smoke #6. Fällt es durch, bleibt die Naht (Protocol + optionaler Pfad) trotzdem korrekt — nur der scharfe Schalter wartet auf Handler-Support. Kein Blocker für den Text-Kern.
- **Konfidenz sonst:** Naht (`TextGenerator`/`TextEmbedder`-Muster), Routing-Punkt, Idle-Loop-Stelle, GGUF-Validierung sind alle im Code verifiziert — keine weiteren wackligen Stellen.

## Vision-Naht (entschieden: mit vorsehen)
Dein Modell bringt `mmproj-BF16.gguf` mit — es **kann Bilder sehen**. Entscheidung: die **Naht**
wird gelegt (mmproj optional ladbar, `VisionTextGenerator` definiert, Manifest führt den mmproj),
das **Feature** (Vision-Job/Capability/UI) bleibt Backlog. So kostet die spätere Bild-Funktion
keinen Runtime-Umbau, und dieser Plan bläht sich nicht zum Captioner auf.

## Chesterton
**Vor Nutzung verstehen:** `GenerativeEngine` ([inference/generative_engine.py](../../../backend/photofant/inference/generative_engine.py))
ist torch-spezifisch (`torch.cuda.empty_cache`, `model.to(device)`) — llama.cpp hat einen eigenen
Lebenszyklus (`Llama`-Objekt, kein torch), daher eine **eigene** kleine Engine-Klasse statt
Erweiterung. Der Ein-Slot-Grund aus ADR-028 (VRAM) bleibt gültig und wird auf zwei Runtimes
ausgedehnt. Der Idle-Loop ([main.py:60-62](../../../backend/photofant/main.py#L60)) und der
Shutdown-Unload ([main.py:102](../../../backend/photofant/main.py#L102)) sind die zwei Stellen, an
denen der neue Slot mitverwaltet wird.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_
