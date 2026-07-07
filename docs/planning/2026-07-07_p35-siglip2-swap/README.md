# P35 — Bild-Embedder swappbar machen + CLIP → SigLIP2

> Ersetzt den Bild-Embedder CLIP ViT-L/14 durch **SigLIP2-large-patch16-384** — und baut im selben
> Zug die **Austausch-Naht**, damit der *nächste* Modelltausch kein Code-Sweep mehr ist, sondern
> „neuer Adapter + eine Registry-Zeile + Manifest-Eintrag". Der Kern bleibt ONNX Runtime; SigLIP2 liegt
> als `onnx-community`-Export im gleichen Layout wie CLIP vor. *(private, lean.)*

## Ziel
Zwei Ziele, ein Plan:
1. **Swappbarkeit (der eigentliche Auftrag):** Konsumenten (Suche, Klassifizierung, Dupe-Scan, Embedding-Job)
   kennen künftig **kein Modell mehr**, nur die Fähigkeit „Bild einbetten". Ein Modelltausch berührt genau
   drei Stellen: Adapter-Datei, Registry-Eintrag, Manifest — plus (nur bei anderer Dimension) eine Migration.
2. **SigLIP2 als erstes Modell auf dieser Naht.** Nach dem Swap ist die Bibliothek neu embedded und die
   Ähnlichkeits-Schwellwerte auf SigLIP2s Verteilung justiert.

## Warum es heute wehtut (Chesterton — was existiert und warum)
- **`inference/adapters/clip.py` → `resolve_clip_embedder()`** — hat `_MANIFEST_ID = "clip-vit-l-14"`
  **hart verdrahtet** und wird an 4 Stellen direkt gerufen (`api/search.py`, `classification/engine.py`,
  `jobs/embedding_job.py`, in `clip.py` selbst). **Das** ist der Schmerzpunkt: der Modellname sickert in die
  Konsumenten. Dok 040 §2 verlangt das Gegenteil (Jobs kennen nur Capabilities).
- **Die ~30 weiteren `clip_*`-Fundstellen sind inert** — sie lesen die DB-Spalte `asset.clip_embedding` oder
  den Settings-Wert `dupe_clip_threshold`. Ein Modelltausch ändert **keine** davon (Speicher bleibt Speicher).
  Sie sind kein Teil der Tausch-Oberfläche und werden **nicht** angefasst.
- **`inference/interfaces.py`** — hält (vermutlich) das `Embedder`-Protokoll. Wird um eine `dim`-Property
  erweitert, damit jeder Adapter seine Vektor-Dimension selbst deklariert statt einer globalen Konstante zu vertrauen.
- **`db/vector_index.py` `EMBEDDING_DIM = 768`** — Dimension der `vec0`-Tabelle (Schema-Wahrheit). Bleibt eine
  Konstante (die Tabelle ist dimensions-typisiert), aber ein **Startup-Guard** vergleicht sie mit `embedder.dim`
  und warnt laut bei Mismatch (= Migration + Re-Embed nötig), statt still zu korrumpieren.
- **`rerun_job.py` `steps=["embedding"], asset_ids="all"`** — setzt `ProcessingLedger.embedding_done` zurück
  und ruft `_run_embedding` je Asset. **Genau der Re-Embed-Pfad** — wiederverwenden, nicht neu bauen.

## Die Austausch-Naht (der Kern dieses Plans)
Neu: **`inference/image_embedder.py`** — ein capability-basierter Resolver + Adapter-Registry:
```
_IMAGE_EMBEDDER_ADAPTERS: dict[str, type[Embedder]] = {
    "clip-vit-l-14":              CLIPEmbedder,
    "siglip2-large-patch16-384":  SigLIPEmbedder,
}

def resolve_image_embedder(role: str = "semantic_search") -> Embedder | None:
    # 1. finde in ModelRegistry das *aktivierte* Modell mit manifest role == <role>
    # 2. schlage die Adapter-Klasse per manifest_id in der Registry nach
    # 3. instanziiere mit dem registry-Pfad; None wenn keins aktiv
```
- **CLIP bleibt registriert** (nicht gelöscht): beweist, dass die Naht trägt (zwei Adapter koexistieren),
  und dient als Rollback. Aktiv ist, welches `semantic_search`-Modell in der Modelle-UI aktiviert ist —
  kohärenter Vektorraum ⇒ genau eins aktiv.
- **`role` ist Parameter, nicht hart verdrahtet** (forward-compat für P37): Konsumenten rufen ohne Argument
  (`semantic_search` = Default). P37 fügt einen zweiten, rein visuellen Embedder (DINOv2) mit
  `role="visual_rerank"` hinzu und ruft `resolve_image_embedder(role="visual_rerank")` — **ohne** die Naht
  aufzureißen. Eine Zeile Weitsicht jetzt spart den Sweep später.
- **Jeder Adapter besitzt seinen Kontrakt selbst:** Preprocessing, Text-Tokenisierung **und** `dim`.
  Kein Konsument und kein zentrales Preprocessing kennt Modell-Interna.
- **Konsumenten rufen nur `resolve_image_embedder()`.** Modellname fällt aus Such-/Klassifizierungs-/
  Dupe-Code komplett raus.

## Zentrale Entscheidungen
- **ADR-021 — SigLIP2 als Bild-Embedder** (`docs/decisions/021-siglip2-embedder.md`): Variante
  `siglip2-large-patch16-384` (1024-dim, ~CLIP-L-Rechenklasse, klar bessere Retrieval-Qualität, mehrsprachig).
  Alternativen: so400m (1152-dim, bestes Retrieval, aber größer/langsamer) verworfen wegen Rechenlast auf
  RTX 3060; base (768-dim, drop-in ohne Migration) verworfen wegen zu kleinem Qualitätssprung.
- **ADR-022 — Swappbare Bild-Embedder-Naht** (`docs/decisions/022-swappable-image-embedder.md`):
  Capability-Resolver (`resolve_image_embedder()`) + Adapter-Registry statt hartverdrahteter Modell-ID;
  Adapter besitzen Preprocessing/Dim/Tokenizer selbst; Dim-Guard beim Start. **Enthält das Swap-Runbook**
  (die 3–5 Schritte für den nächsten Tausch) — damit spätere Sessions die Naht nicht neu erfinden.
  Forward-kompatibel zu P27s ModelManager (ADR-013): P35 baut nur die Embedding-Scheibe, P27 verallgemeinert.
  DB-Spalten `clip_embedding`/`clip_distance` + Settings `dupe_clip_*` bleiben benannt (inert, nicht Teil der
  Tausch-Oberfläche) — Umbenennen brächte Migrations-Risiko ohne Swap-Nutzen.

## Settings.json (vorab freigeben)
- **Keine neuen Keys.** Die Rekalibrierung justiert bestehende Werte: `dupe_clip_threshold` (heute 0.03) und
  `training_near_dupe_clip_threshold` (heute 0.05) — neue Defaults in Phase 3 an realem Set bestimmt,
  über die bestehende Einstellungen-UI einstellbar.

## Kontrakt (Cross-Modul-Anker)
- **`Embedder`-Protokoll** (`inference/interfaces.py`): `embed(image) -> np.ndarray` (L2-normalisiert),
  `embed_text(text) -> np.ndarray`, **neu** `dim: int` (property). Alle Adapter erfüllen es.
- **Resolver:** `resolve_image_embedder(role="semantic_search") -> Embedder | None`
  (`inference/image_embedder.py`) ist die **einzige** Bezugsquelle für Konsumenten. `resolve_clip_embedder()`
  entfällt. Der `role`-Parameter (Default `semantic_search`) hält die Naht offen für weitere Modell-Rollen
  (P37: `visual_rerank`).
- **Dimension:** `vector_index.EMBEDDING_DIM` = Schema-Wahrheit der Tabelle (1024 nach Phase 2).
  Startup-Guard: `EMBEDDING_DIM == resolve_image_embedder().dim` sonst laute Warnung.
- **Übergangs-Invariante:** Zwischen Migration (Phase 2) und Abschluss des Re-Embeds (Phase 3) sind **alle**
  `clip_embedding`-BLOBs `NULL` und `embedding_done=False`. Kein gemischter 768/1024-Zustand — sonst crasht
  `np.stack` im Dupe-Scan und `_serialize` in der Suche.

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Austausch-Naht + SigLIP2-Adapter + Manifest | heikel (Naht-Design + neues Preprocessing/Tokenizer) | pending |
| 2 | Vektor-Dimension-Migration (768 → 1024) | heikel (Migration + Übergangs-Invariante) | pending |
| 3 | Re-Embed + Schwellwert-Rekalibrierung | standard | pending |

## Finale AK (Gesamt)
- [ ] **Swap-Naht:** kein Konsument (`api/search.py`, `classification/engine.py`, `jobs/embedding_job.py`,
      `jobs/dupe_scan_job.py`) nennt noch einen Modellnamen; alle beziehen den Embedder über
      `resolve_image_embedder()`. CLIP und SigLIP2 sind beide registriert.
- [ ] **Swap-Runbook** in ADR-022: die konkreten Schritte für den nächsten Modelltausch, an SigLIP2 belegt.
- [ ] Ein frisch importiertes Bild erhält ein 1024-dim SigLIP2-Embedding; `vec_asset_embedding` ist `float[1024]`.
- [ ] Semantische Suche liefert für Text **und** `like_asset_id` plausible Treffer.
- [ ] Nach „Neuverarbeitung: Embedding, alle" hat jedes aktive Asset ein SigLIP2-Embedding, kein 768-Rest.
- [ ] Duplikat-Scan findet echte Duplikate weiter zuverlässig; Schwellwert auf SigLIP2 justiert.
- [ ] Klassifizierung (CLIP+WD14-Fusion) läuft fehlerfrei auf den neuen Embeddings.
- [ ] Kein Laufzeit-Netzwerkzugriff außer dem Modell-Download über die Settings-UI; kein torch-Zwang für den Embedder.
- [ ] ADR-021 und ADR-022 liegen in `docs/decisions/`.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. **[Oberste Wackelstelle] Schwellwert-Rekalibrierung:** nach Re-Embed „Duplikate scannen (vollständig)"
   auslösen → tauchen bekannte echte Duplikate noch als Kandidaten auf, ohne Fremdpaare? Sitzt der
   97 %-Wert (`dupe_clip_threshold`) nicht mehr → in den Einstellungen nachziehen.
2. **[Wackelstelle] SigLIP-Text-Preprocessing:** `curl POST /api/search/semantic {"query":"ein roter Sportwagen"}`
   → thematisch passende Treffer? (Prüft Tokenizer/64-Token-Padding.)
3. **Swap-Naht belegen:** in der Modelle-UI CLIP aktivieren statt SigLIP2, ein Bild embedden → Adapter wechselt
   ohne Code-Änderung (Log zeigt 768 dims + Dim-Guard-Warnung). Danach zurück auf SigLIP2.
4. Neues Bild importieren → Log „Embedded asset N (1024 dims)"; Klassifizierung-Rerun ohne Exception.

## Risiken
- 🟡 **Schwellwert-Verschiebung** — SigLIP2 (Sigmoid-Loss) verteilt Cosine-Ähnlichkeiten anders als CLIP.
  CLIP-geeichte Dupe-Schwellwerte passen vermutlich nicht 1:1. Mitigation: Phase 3 kalibriert an realem Set,
  Werte in Settings, Prozent-Anzeige macht Fehlgewichtung sichtbar. **Der Kern-Punkt.**
- 🟡 **SigLIP-Preprocessing weicht von CLIP ab** — Squash-Resize auf 384² (kein Center-Crop) + Normalisierung
  mean/std 0.5 (nicht CLIP-/ImageNet-Stats). Falsches Preprocessing = stumpfe Embeddings ohne Crash.
  Mitigation: gegen `preprocessor_config.json` des HF-Repos verifizieren (Check in Phase 1).
- 🟡 **Text-Encoder-Kontrakt** — SigLIP2 nutzt festes 64-Token-Padding, ggf. keine `attention_mask`.
  Adapter fragt die tatsächlichen ONNX-Inputs ab (Muster aus `clip.py` erhalten).
- 🟡 **Re-Embed-Dauer** — ganze Bibliothek läuft neu durch die GPU (Background-Worker, blockiert nichts).

## Konfidenz — wo ich am unsichersten bin
1. **SigLIP-Preprocessing-Details** (Resize-Modus, Normalisierung, Textlänge) — Check: `preprocessor_config.json`
   + `tokenizer_config.json` im heruntergeladenen Ordner lesen, bevor Phase 1 den Adapter finalisiert
   (erst nach Download prüfbar → erster Schritt in Phase 1).
2. **Neue Dupe-Schwellwerte** — nur empirisch an realem Set bestimmbar (Smoke #1).
3. **`Embedder`-Protokoll-Ist-Zustand** — ob `inference/interfaces.py` heute schon ein sauberes Protokoll hält
   oder CLIP nur duck-typed war. Check: Datei in Phase 1 zuerst lesen.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-ups: **P36** Reverse Image Search und **P37** DINOv2 Re-Ranking bauen hierauf auf.
