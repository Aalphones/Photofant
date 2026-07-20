# ADR-029 — GGUF-Gemma als 2. Runtime, VRAM-Invariante per Cross-Unload

**Status:** Angenommen — Phase 1 umgesetzt (P35 Phase 1: `inference/gguf_engine.py`, `inference/adapters/gemma_gguf.py`)
**Datum:** 2026-07-20
**Betrifft:** Plan `2026-07-20_p35-gemma-gguf-runtime`; ergänzt ADR-028 (widerruft es nicht)

---

## Kontext

ADR-028 verwarf GGUF/llama.cpp explizit als **dritte** Inferenz-Runtime — mit dem
Vorbehalt „bleibt GGUF je nötig, ist es ein neuer Adapter hinter derselben Capability,
kein Job/keine Lifecycle-Mechanik ändert sich". Genau dieser Fall ist jetzt eingetreten:
ein bereits vorhandenes lokales GGUF-Gemma (12B, Q4_K_M, abliteriert) soll als
Text-Generator einhängen, ohne den torch-Pfad (Gemma safetensors, JoyCaption,
Qwen2.5-VL) anzufassen. Die einzige neue Frage: **wie teilen sich zwei unabhängige
Runtimes einen VRAM-Slot**, wenn beide für sich genommen „ein Modell auf einmal"
durchsetzen, aber nichts voneinander wissen?

## Optionen (VRAM-Koordination zwischen den Runtimes)

- **Abstrakter `vram_arbiter` mit registrierten Unload-Callbacks.** Sauberer ab
  **drei** Runtimes (ein zentraler Scheduler statt N² Verweise), aber für genau zwei
  ist es Abstraktion ohne Gegenwert — ein Modul, ein Registrierungs-Mechanismus,
  ein zusätzlicher Indirektionslayer für zwei Zeilen Effekt. Verworfen (Chesterton:
  Komplexität, die kein drittes Runtime-Bedürfnis heute rechtfertigt).
- **Gegenseitiges Cross-Unload (gewählt).** Jede Engine ruft vor dem eigenen Laden
  explizit die andere zum Entladen auf.

## Entscheidung

**Zwei gerichtete Aufrufe, kein Vermittler:**
- `GgufEngine.load(...)` ruft **vor** dem `Llama(...)`-Konstruktor
  `generative_engine.unload()`.
- `GenerativeEngine.load_transformers_model(...)` ruft **vor** dem Laden
  `gguf_engine.unload()`.
- Beide Importe sind **lazy** (innerhalb der Methode) — die beiden Module importieren
  sich sonst gegenseitig auf Modulebene und erzeugen einen Zyklus.
- Jede Runtime entlädt zusätzlich unabhängig per eigenem `evict_idle(timeout)`,
  angestoßen vom selben App-Idle-Loop (`main.py`) mit demselben
  `ai.idleTimeoutSeconds` — ein Timeout für den gesamten Heavy-Modell-Slot,
  konsistent mit ADR-028.

**Form gespiegelt, Inhalt nicht:** `GgufEngine` übernimmt die Form von
`GenerativeEngine` (`_PipelineEntry`-Äquivalent mit `last_used`, `threading.Lock`,
`evict_idle`, `unload`) — aber llama.cpp hat einen eigenen Objekt-Lebenszyklus
(`Llama`, kein torch-Device/-Dtype-Handling), daher eine **eigene** kleine
Engine-Klasse statt einer Erweiterung von `GenerativeEngine`.

**Vision-Naht mitgelegt, nicht konsumiert:** `GgufEngine.load(...)` nimmt einen
optionalen `mmproj_path`; ist er gesetzt, wird versucht, den passenden
Gemma-3-Vision-Chat-Handler von llama-cpp-python zu bauen. Trägt die installierte
Version ihn nicht, wird das mmproj **ignoriert + eine Warnung geloggt** — Text
läuft unverändert weiter. `VisionTextGenerator(TextGenerator)` ist in
`interfaces.py` definiert (Muster `TextEmbedder(Embedder)`); `GemmaGgufAdapter`
(text-only) und `GemmaGgufVisionAdapter` (zusätzlich `generate_with_image`) sind
**getrennte Klassen** — die Fähigkeit wird strukturell per `isinstance` geprüft,
nicht per Instanz-Flag auf einer gemeinsamen Klasse (dasselbe Muster wie
`CLIPEmbedder`/`DINOv2Embedder`). `resolve_gemma_gguf` wählt die Klasse anhand des
optionalen `mmproj`-Eintrags in `ModelRegistry.components` (derselbe JSON-Kanal,
den auch Komponenten-Modelle wie Flux nutzen).

## Konsequenzen

- Kein zentraler Arbiter-Layer; zwei Codezeilen sind die gesamte Koordination.
  Kommt eine dritte Heavy-Runtime dazu, ist das der Punkt, an dem sich ein
  `vram_arbiter` lohnt (N² Cross-Calls werden ab drei Teilnehmern unhandlich) —
  hier bewusst nicht vorgebaut.
- Jobs/Capability-Code ändert sich nicht (ADR-027/028 unberührt) — `resolve_generator`
  bekommt in Phase 2 eine Format-Weiche, aber der Vertrag (`TextGenerator`) bleibt
  exakt derselbe.
- 12B-Q4 statt der ursprünglich eingeplanten 4B-Variante — mehr VRAM-Bedarf (~8 GB),
  Koexistenz mit den Captionern enger als geplant, aber Q4 allein passt auf die
  3060 (12 GB). Kein Blocker, siehe Plan-Risiko.
- Die Vision-Naht kostet keinen Runtime-Umbau, wenn später eine echte Vision-Capability
  gebraucht wird — nur der scharfe Handler-Support in llama-cpp-python ist offen
  (Smoke-Checkliste #6 klärt das empirisch, kein Blocker für den Text-Kern).
