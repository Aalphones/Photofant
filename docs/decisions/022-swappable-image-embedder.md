# ADR-022 — Swappbare Bild-Embedder-Naht (Capability-Resolver)

**Status:** Angenommen
**Datum:** 2026-07-07
**Betrifft:** Plan `2026-07-07_p35-siglip2-swap`, ergänzt ADR-021 (erstes Modell auf dieser Naht), forward-kompatibel zu ADR-013 (P27 ModelManager)

---

## Kontext

Vor P35 war der Modellname hart im Code verdrahtet: `resolve_clip_embedder()` mit
`_MANIFEST_ID = "clip-vit-l-14"`, direkt gerufen aus Suche, Klassifizierung und Embedding-Job.
Der Name sickerte in die Konsumenten — ein Modelltausch hätte einen Code-Sweep über alle
Aufrufstellen bedeutet. Dok 040 §2 verlangt das Gegenteil: Jobs kennen nur *Fähigkeiten*
(„Bild einbetten"), nicht Modelle.

## Optionen

- **Beim CLIP-Namen bleiben, pro Modell eine neue `resolve_*`-Funktion:** verworfen — jeder Tausch
  fügt eine Funktion hinzu und die Konsumenten müssten wählen, welche sie rufen. Der Name bleibt
  im Konsumenten.
- **Sofort den vollen P27-ModelManager (ADR-013) bauen:** verworfen als zu groß für diesen Plan.
  P35 baut nur die Embedding-Scheibe; P27 verallgemeinert später über alle Modellrollen.
- **Capability-Resolver + Adapter-Registry (gewählt):** Konsumenten fragen nach einer Rolle,
  die Registry entscheidet, welches konkrete Modell antwortet.

## Entscheidung

Neu: `inference/image_embedder.py` mit einer Adapter-Registry und einem Resolver:

```python
_IMAGE_EMBEDDER_ADAPTERS: dict[str, type[Embedder]] = {
    "clip-vit-l-14":              CLIPEmbedder,
    "siglip2-large-patch16-384":  SigLIPEmbedder,
}

def resolve_image_embedder(role: str = "semantic_search") -> Embedder | None: ...
```

- Der Resolver findet die **aktivierte** `ModelRegistry`-Zeile mit passender `role`, schlägt die
  Adapter-Klasse per `manifest_id` nach und instanziiert sie mit dem Registry-Pfad.
- **`role` ist Parameter** (Default `semantic_search`), nicht hart verdrahtet — forward-compat für
  P37 (`visual_rerank` = DINOv2) ohne Aufreißen der Naht.
- **Jeder Adapter besitzt seinen Kontrakt selbst:** Preprocessing, Text-Tokenisierung und `dim`
  (neue Property im `Embedder`-Protokoll). Kein Konsument und kein zentrales Preprocessing kennt
  Modell-Interna.
- **Startup-Guard:** `warn_on_embedding_dim_mismatch()` vergleicht `vector_index.EMBEDDING_DIM`
  gegen `resolve_image_embedder().dim` und warnt laut bei Mismatch (Migration + Re-Embed nötig),
  statt still einen Dim-Fehler in Suche/Dupe-Scan zu produzieren. Kein Crash.
- **Konsumenten** (Suche `api/search.py`/`api/assets.py`, Klassifizierung `classification/engine.py`
  + `scoring.py`, `jobs/embedding_job.py`) rufen nur noch `resolve_image_embedder()`. Der Modellname
  fällt komplett aus dem Konsumenten-Code. `resolve_clip_embedder()` entfällt.

## Swap-Runbook — der nächste Modelltausch

Ein Bild-Embedder-Tausch berührt genau diese Stellen (an SigLIP2 belegt):

1. **Adapter-Datei** `inference/adapters/<modell>.py`: `Embedder` implementieren
   (`embed`, `embed_text`, `dim`) — `CLIPEmbedder`/`SigLIPEmbedder` als Vorlage. Modell-eigenes
   Preprocessing gehört in `inference/preprocessing.py` (`preprocess_for_<modell>`), nicht in den
   Konsumenten.
2. **Registry-Zeile** in `_IMAGE_EMBEDDER_ADAPTERS` (`inference/image_embedder.py`): eine Zeile
   `"<manifest_id>": <AdapterKlasse>`. Alte Adapter drin lassen (Rollback, Koexistenz).
3. **Manifest-Eintrag** in `models/manifest.json`: `id` == manifest_id, `role: "semantic_search"`,
   `hf_repo` + `hf_allow_patterns`. Preprocessing/Tokenizer gegen `preprocessor_config.json` +
   `tokenizer_config.json` des heruntergeladenen Ordners verifizieren.
4. **Nur bei anderer Dimension:** `vector_index.EMBEDDING_DIM` anheben, `vec0`-Tabelle migrieren
   (768 → neue Breite) und die Bibliothek re-embedden. Übergangs-Invariante wahren: keine
   gemischten Dimensionen im Index (alle Embeddings gleichzeitig `NULL`, dann neu). Bei gleicher
   Dimension entfällt dieser Schritt — reiner Adapter-/Registry-/Manifest-Tausch.
5. **Aktivieren** über die Modelle-UI (genau ein `semantic_search`-Modell enabled — kohärenter
   Vektorraum).

## Konsequenzen

- Ein gleich-dimensionaler Modelltausch ist ein Drei-Zeilen-Eingriff ohne Code-Sweep über die
  Konsumenten. Ein dimensions-ändernder Tausch kostet zusätzlich Migration + Re-Embed — vom
  Startup-Guard sichtbar gemacht, nicht still verschluckt.
- DB-Spalten (`clip_embedding`, `clip_distance`) und `dupe_clip_*`-Settings behalten ihre Namen
  (inert, nicht Teil der Tausch-Oberfläche) — Umbenennen brächte Migrations-Risiko ohne Nutzen.
- Der Resolver ist bewusst schmal (nur Embedding-Rolle). P27 (ADR-013) verallgemeinert das Muster
  später über alle Modellrollen; diese Naht ist die erste Scheibe davon.
