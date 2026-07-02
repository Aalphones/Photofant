# ADR-017 — Inference Session Pool: N separate Sessions statt gemeinsamer Executor

**Status:** Akzeptiert · 2026-07-02
**Querverweise:** P19 (Inference Session Pool), Phase 1.

## Kontext

Ein ONNX `InferenceSession`-Objekt ist nicht re-entrant — zwei Threads dürfen nicht gleichzeitig
`session.run()` auf derselben Instanz aufrufen. Heute existiert pro Modelltyp genau ein
Worker-Task (WD14-Tagging, Florence2-Captioning), also läuft nie mehr als ein Thread gleichzeitig
gegen dieselbe Session. Sobald mehrere Worker-Tasks pro Modelltyp parallel laufen sollen (P19-Ziel:
N Tagging- + M Captioning-Worker, konfigurierbar), reicht die bestehende Singleton-Session pro
`model_path` nicht mehr aus.

## Optionen

| Option | Beschreibung |
|---|---|
| **A — N separate Sessions pro Modelltyp (Pool)** | Bis zu `pool_size` `InferenceSession`-Instanzen pro `model_path`, exklusiv an einen Worker verliehen (`acquire_exclusive_session`/`release_exclusive_session`, blockierend via `threading.Condition`). |
| B — neue Session pro Job, kein Pooling | Jeder Job lädt/entlädt seine eigene Session. Kein Blockieren, aber Ladezeit (Modell von Disk/VRAM) pro Bild bei Batch-Imports — bei hunderten Bildern inakzeptabel. |

## Entscheidung

**Option A.** Der Pool lebt in `SessionManager` als eigene Datenstruktur (`_pools: dict[str,
_PoolState]`), getrennt von der bestehenden Singleton-`_sessions`-Cache — zwei Methodennamen
(`acquire_exclusive_session`/`release_exclusive_session` vs. `acquire_session`/`release_session`)
verhindern, dass ein Adapter versehentlich die falsche Semantik nutzt. CLIP, Buffalo-L und
`media/ops.py` bleiben unverändert auf dem Singleton-Pfad, weil sie je nur einen Worker haben und
keinen Pool brauchen.

Die Pool-Kapazität wächst lazy: der erste Aufruf lädt die erste Instanz, jeder weitere Aufruf bis
`pool_size` lädt nach; ist die Kapazität erschöpft, blockiert `acquire_exclusive_session` bis eine
Instanz per `release_exclusive_session` frei wird. Ein separates `threading.Condition` (nicht
`asyncio`) wird genutzt, weil der Aufruf bereits in einem OS-Thread aus `asyncio.to_thread` läuft.

## Konsequenzen

- Pool-Größe = konfigurierte Worker-Anzahl (`tagging_workers`/`captioning_workers`, Phase 2) —
  VRAM-Verbrauch skaliert linear mit N. Ein zu hoher Wert auf kleiner GPU führt zu CUDA-OOM beim
  Laden der N-ten Instanz (Phase 3/4: sichtbare Fehlermeldung im Job-Dock statt stillem Crash).
- `evict_idle`/`evict_all`/`shutdown` müssen jetzt zwei Strukturen abdecken (Singleton-Cache +
  Pool) — beide werden in jeder dieser drei Methoden behandelt, damit kein Session-Typ beim
  Shutdown vergessen wird.
- Kein echter GPU-Parallelbetrieb (CUDA Streams / ONNX `cuda_stream`-Option) — der Pool überlappt
  nur CPU-seitiges Preprocessing/DB-I/O zwischen den Workern; GPU-Kernel serialisieren intern
  weiter (Follow-up, nicht Teil von P19, siehe Plan-README).
