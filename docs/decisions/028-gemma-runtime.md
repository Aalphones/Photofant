# ADR-028 — Gemma-Laufzeit: torch/transformers auf dem bestehenden Modell-Slot

**Status:** Angenommen — Phase 1 umgesetzt (P27 Phase 1: `inference/adapters/gemma.py`)
**Datum:** 2026-07-20
**Betrifft:** Plan `2026-07-01_p27-gemma-integration`; nutzt Bestand `inference/generative_engine.py`, `models/vram.py`, das Modell-Management-Feature; hängt an ADR-027 (AI-Layer)

> **ADR-Nummer:** Der Plan reservierte „ADR-014" — die Nummer war belegt
> (wissens-lookup-auto-trigger). Nächste echte freie nach ADR-027: **028**.

---

## Kontext

Gemma muss lokal auf einer RTX 3060 laufen, offline, und **neben** den vorhandenen
Heavy-Modellen (JoyCaption, Qwen2.5-VL, Generativ-Pipelines) koexistieren, ohne den VRAM
zu sprengen. Die Frage: welche Runtime?

Bestehende Lage: Die Heavy-Captioner laufen bereits über **torch/transformers**
(`GenerativeEngine.load_transformers_model`). JoyCaption ist ein LLaVA-VLM — im Kern ein
Causal-LM mit Bild-Teil; `AutoModelForCausalLM` ist die Default-Klasse. Lazy-Load,
Idle-Unload, „ein Modell auf einmal"-VRAM-Disziplin und Offline-Zwang (`HF_HUB_OFFLINE`)
sind dort fertig implementiert. ONNX-Modelle laufen separat über `session_manager`.

## Optionen

- **GGUF / llama.cpp (`llama-cpp-python`):** kleiner im VRAM (Q4), schneller bei reinem Text.
  Verworfen — eine **dritte** Inferenz-Runtime neben ONNX und torch, mit eigener
  VRAM-Buchhaltung außerhalb der bestehenden Mechanik, plus Binaries, die offline zu managen
  sind (der Plan verbietet Repo-Binaries). Das ist genau der „neue Lade-Pfad", den die
  Chesterton-Notiz des Plans ausschließt.
- **torch/transformers auf dem bestehenden `GenerativeEngine` (gewählt).**

## Entscheidung

**Gemma fährt über `GenerativeEngine.load_transformers_model` mit
`model_class_name="AutoModelForCausalLM"`** — derselbe Slot und Lebenszyklus wie die
Captioner. Kein neuer Lade-Pfad, keine zweite VRAM-Buchhaltung.

**Ein Unterschied, minimal-invasiv gelöst:** Ein reines Text-LM hat **keinen**
`AutoProcessor` (das ist ein Multimodal-Konzept). `load_transformers_model` bekam einen
`load_processor`-Schalter (Default `True`, Captioner unverändert); bei `False` lädt es einen
`AutoTokenizer` statt eines Processors. Additive, nicht-brechende Erweiterung.

**Gemma-Eigenheit:** Der Chat-Template kennt keine `system`-Rolle — eine System-Instruktion
wird in den User-Turn gefaltet.

**VRAM bei Druck:** Gemma teilt sich den Ein-Modell-Slot mit den Captionern (das Laden von
Gemma verdrängt einen residenten Captioner und umgekehrt) und wird per Idle-Loop entladen.
Reicht der VRAM für eine Variante nicht, ist 4-bit (bitsandbytes) der Weg — nicht eine
zweite Runtime. Modellbezug ausschließlich über das Modell-Management-Feature (Manifest-
Eintrag `gemma-3-4b-it`, `requires_license_ack`), kein Binary im Repo.

**Idle-Unload konfigurierbar:** `evict_idle` nimmt jetzt einen Timeout-Override; der
App-Idle-Loop reicht `ai.idleTimeoutSeconds` durch. Dieser Wert steuert den **gesamten**
generativen Modell-Slot (Gemma **und** Captioner — es ist genau ein resident) und bleibt per
Default bei 120 s, sodass sich das Captioner-Verhalten nur ändert, wenn der Nutzer es setzt.

## Konsequenzen

- Null neuer Lade-/VRAM-Pfad; Gemma ist der simpelste Gast im bestehenden Generativ-Haus.
- Bleibt GGUF je nötig (Performance/VRAM), ist es ein **neuer Adapter hinter derselben
  Capability** (ADR-027) — kein Job und keine Lifecycle-Mechanik ändert sich. Die Naht ist
  gebaut; diese Entscheidung ist kein Einbahn-Ticket.
- `ai.idleTimeoutSeconds` regelt den ganzen Generativ-Slot, nicht Gemma allein. Bewusster
  Trade-off zugunsten „eine Mechanik" statt eines Per-Modell-Timeouts; falls je ein
  getrenntes Timing gebraucht wird, ist das ein späterer, isolierter Schritt.

## Nachtrag (P35, ADR-029)

GGUF-Adapter als zweite Runtime umgesetzt (P35, ADR-029) — torch bleibt der
Default-Pfad, keine Entscheidung hier revidiert.
