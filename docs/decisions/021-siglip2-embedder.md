# ADR-021 — SigLIP2 als Bild-Embedder (ersetzt CLIP ViT-L/14)

**Status:** Angenommen
**Datum:** 2026-07-07
**Betrifft:** Plan `2026-07-07_p35-siglip2-swap`, supersedes den CLIP-Teil von ADR-001/ADR-007/ADR-018 (Modellwahl), ergänzt ADR-022 (Naht)

---

## Kontext

Der Bild-Embedder trägt drei Funktionen: semantische Suche (Text→Bild und Bild→Bild),
CLIP-Signal in der Klassifizierungs-Fusion und die Duplikaterkennung. Bisher: CLIP ViT-L/14
(OpenAI-Original, 768-dim). SigLIP2 (Google, 2025) liefert bei vergleichbarer Rechenklasse
deutlich bessere Retrieval-Qualität und ist mehrsprachig (Gemma-Tokenizer) — ein spürbarer
Sprung für Text→Bild-Suche auf einer gemischtsprachigen Bibliothek.

## Optionen

- **`siglip2-so400m-patch16-384` (1152-dim):** bestes Retrieval, aber größer und langsamer.
  Verworfen wegen der Rechenlast auf einer RTX 3060 (Ziel-Hardware) — der Qualitätsvorsprung
  gegenüber der large-Variante rechtfertigt den VRAM-/Latenz-Aufschlag hier nicht.
- **`siglip2-base-patch16-*` (768-dim):** drop-in ohne Dimension-Migration (gleiche Index-Breite
  wie CLIP). Verworfen — der Qualitätssprung gegenüber CLIP ist zu klein, um den Swap zu lohnen.
- **`siglip2-large-patch16-384` (1024-dim, gewählt):** klar bessere Retrieval-Qualität, ~CLIP-L-
  Rechenklasse, mehrsprachig. Kostet eine einmalige Vektor-Dimension-Migration (768 → 1024) plus
  Re-Embed der Bibliothek — akzeptiert, weil der Qualitätsgewinn die einmaligen Kosten trägt.

## Entscheidung

`siglip2-large-patch16-384` als aktives `semantic_search`-Modell, bezogen als
`onnx-community/siglip2-large-patch16-384-ONNX` (fp32-ONNX, gleiches `onnx/`-Layout wie CLIP,
läuft auf dem bestehenden ONNX-Runtime-Kern — kein torch-Zwang).

- **Preprocessing** weicht von CLIP ab: Squash-Resize auf 384² (kein Center-Crop), Normalisierung
  mean/std 0.5 (nicht CLIP-/ImageNet-Stats) — siehe `preprocess_for_siglip`.
- **Text:** festes 64-Token-Padding (Gemma-Tokenizer), `attention_mask` nur wenn das ONNX-Text-
  Modell sie deklariert.
- **CLIP bleibt registriert** (nicht gelöscht) als Rollback und als lebender Beweis, dass die
  Austausch-Naht zwei Adapter trägt (ADR-022). Aktiv ist genau ein Modell — ein kohärenter
  Vektorraum verträgt keine Mischung.

## Konsequenzen

- Einmalige Migration der `vec0`-Tabelle von `float[768]` auf `float[1024]` + vollständiger
  Re-Embed (alle `clip_embedding`-BLOBs neu). Übergangs-Invariante: zwischen Migration und
  Abschluss des Re-Embeds sind alle Embeddings `NULL` — kein gemischter 768/1024-Zustand.
- Die Duplikat-Schwellwerte (`dupe_clip_threshold`, `training_near_dupe_clip_threshold`) sind
  CLIP-geeicht und passen nicht 1:1 — SigLIP2 (Sigmoid-Loss) verteilt Cosine-Ähnlichkeiten
  anders. An realem Set neu kalibriert, über die Einstellungen justierbar (keine neuen Keys).
- DB-Spalten `clip_embedding`/`clip_distance` und die `dupe_clip_*`-Settings behalten ihre Namen
  (inert — Speicher bleibt Speicher; Umbenennen brächte Migrations-Risiko ohne Swap-Nutzen).
