# P18 — Bildklassifizierung (WD14 + CLIP Regel-Engine)

> **Quelle/Konzept:** [`KONZEPT.md`](KONZEPT.md) (das ursprüngliche Konzept, hierher verschoben).

## Ziel

Bilder werden gegen frei definierbare **Kategorien** (Medium, Stil, Realismus,
Franchise, Charakter …) klassifiziert. Jede Kategorie hat **Labels**; pro Bild
wird je Kategorie eine Hauptklasse (single) oder mehrere Klassen (multi)
bestimmt. Die Entscheidung fusioniert zwei schon vorhandene Signale:

- **CLIP** — Label-Texte werden embedded und per Cosinus gegen das gespeicherte
  Bild-Embedding (`asset.clip_embedding`) bewertet (softmax je Kategorie).
- **WD14** — gespeicherte Tag-Scores (`asset_tag.score`) füttern die Labels, die
  per `wd14_tags` darauf zeigen.

**Der Retro-Lauf ist billig:** beide Signale liegen bereits in der DB. Es läuft
kein Modell über tausende Bilder neu. Fehlt für ein Label das WD14-Signal (Tag
lag unter der Tagging-Schwelle), fällt die Fusion still auf CLIP zurück.

Gefundene Klassen erscheinen in der **Lightbox**, sind in der **globalen Suche**
und im **Galerie-Filter** (je Kategorie eine Gruppe) verfügbar. Kategorien werden
in einem **neuen Einstellungen-Tab** verwaltet; bestehende Bilder lassen sich
nachträglich klassifizieren.

## Phasen

| # | Phase | Tier | Status |
|---|---|---|---|
| 1 | [Datenmodell & Seed-Katalog](phase-1-datenmodell-seed.md) | heikel | complete |
| 2 | [Engine: CLIP + WD14-Fusion, Job, Pipeline-Hook](phase-2-engine-fusion.md) | heikel | complete |
| 3 | [Backend-API: CRUD, Retro-Lauf, Filter/Facets/Suche](phase-3-backend-api-suche.md) | standard | complete |
| 4 | [Einstellungen-Tab (Frontend)](phase-4-einstellungen-tab.md) | standard | complete |
| 5 | [Galerie-Filter, Lightbox, globale Suche (Frontend)](phase-5-galerie-lightbox-suche.md) | standard | complete |
| 6 | [Docs & ADR-010](phase-6-docs-adr.md) | mechanisch | complete |

## Kontrakt (Cross-Modul — Drift-Anker über `/clear`-Grenzen)

### DB-Schema (Phase 1)

```
classification_category
  id             INTEGER PK
  name           TEXT NOT NULL UNIQUE          -- "Medium", "Stil"
  mode           TEXT NOT NULL                 -- 'single' | 'multi'
  position       INTEGER NOT NULL              -- Sortierung in UI + Filter
  enabled        BOOLEAN NOT NULL DEFAULT 1
  builtin        BOOLEAN NOT NULL DEFAULT 0    -- aus Konzept-Seed (löschbar, nur markiert)
  min_confidence FLOAT NULL                    -- optionaler Override der globalen Schwelle

classification_label
  id           INTEGER PK
  category_id  INTEGER FK -> classification_category(id) ON DELETE CASCADE  (indexed)
  name         TEXT NOT NULL                   -- "Anime"
  position     INTEGER NOT NULL
  clip_prompts JSON NULL                       -- list[str]; leer => Template aus settings.json
  wd14_tags    JSON NULL                       -- list[str]; WD14-Tag-Namen, die dieses Label speisen
  UNIQUE(category_id, name)

asset_classification
  asset_id     INTEGER FK -> asset(id)                 (PK-Teil, indexed)
  label_id     INTEGER FK -> classification_label(id) ON DELETE CASCADE  (PK-Teil)
  category_id  INTEGER FK -> classification_category(id)  (indexed, denormalisiert für Filter/Facets)
  confidence   FLOAT NOT NULL
  source       TEXT NOT NULL                   -- 'clip' | 'wd14' | 'fused'
  PRIMARY KEY (asset_id, label_id)
```

Ledger: **kein neues Feld** — der bereits vorhandene, ungenutzte
`ProcessingLedger.classified` (Migration `0009`) wird hierfür belegt: `True`,
wenn die Kategorien für den Content-Hash berechnet sind; vom Rerun zurückgesetzt.

### Engine-Signatur (Phase 2)

```python
# classification/engine.py
@dataclass
class ClassificationResult:
    category_id: int
    label_id: int
    confidence: float
    source: str            # 'clip' | 'wd14' | 'fused'

def classify_asset(session: Session, asset_id: int) -> list[ClassificationResult]:
    """Liest gespeichertes Embedding + Tag-Scores, fusioniert je Kategorie,
    wendet mode + Schwellen an. Kein commit (Caller besitzt die Tx)."""
```

Fusion je (Kategorie, Label):
```
clip_p  = softmax_über_kategorie( cosine(image_emb, mean(prompt_embeddings(label))) )
wd14_p  = max( stored_tag_score(t) for t in label.wd14_tags )   # oder None
fused   = gewichteter Schnitt der vorhandenen Signale (clip_weight, wd14_weight)
single-Kategorie: argmax(fused), falls fused >= min_confidence
multi-Kategorie:  alle Labels mit fused >= multi_min_confidence
```

### HTTP-Kontrakt (Phase 3)

```
# CRUD  (api/classification.py, prefix /classification)
GET    /classification/categories              -> [{...category, labels:[...]}]
POST   /classification/categories              {name, mode, position?}            -> category
PATCH  /classification/categories/{id}         {name?, mode?, position?, enabled?, min_confidence?}
DELETE /classification/categories/{id}
POST   /classification/categories/{id}/labels  {name, clip_prompts?, wd14_tags?}  -> label
PATCH  /classification/labels/{id}             {name?, clip_prompts?, wd14_tags?, position?}
DELETE /classification/labels/{id}

# Retro-Lauf  — KEIN neuer Endpoint: bestehenden Rerun nutzen
POST   /classify/rerun  {asset_ids: "all" | [int], steps: ["categories"]}        -> {job_id}
```

`ClassifyStep` (in `api/classify.py`) wird um `"categories"` erweitert.

`AssetDetailDto` bekommt:
```
classifications: list[{category_id, category_name, label_id, label_name, confidence}]
```

`GET /assets` Filter + Facets:
```
?classification=<label_id>&classification=<label_id>...   # OR innerhalb einer Kategorie, AND über Kategorien hinweg
Facets.classifications: [{category_id, name, items:[{label_id, name, count}]}]
freie q-Suche matcht zusätzlich asset_classification.label_name (Union zu Tag/Caption)
```

### Frontend-Typen (Phase 4/5)

```typescript
// models/classification.model.ts
interface ClassificationCategory { id; name; mode: 'single'|'multi'; position; enabled; builtin; min_confidence: number|null; labels: ClassificationLabel[]; }
interface ClassificationLabel    { id; category_id; name; position; clip_prompts: string[]; wd14_tags: string[]; }
interface AssetClassification    { category_id; category_name; label_id; label_name; confidence; }
```

Filter-State (`store/filters`): neues Feld `classificationLabelIds: number[]`,
Action `setClassificationLabelIds`, in `clearAllFilters` zurückgesetzt, in
`gallery.effects` an `assetService.listAssets({ classification })` durchgereicht.

## settings.json-Keys (Critical Rule 7 — vor Phase 2 von Sascha freigeben)

| Key | Default | Wirkung |
|---|---|---|
| `classification.clip_weight` | `0.5` | Gewicht des CLIP-Signals in der Fusion |
| `classification.wd14_weight` | `0.5` | Gewicht des WD14-Signals in der Fusion |
| `classification.min_confidence` | `0.3` | Untergrenze für single-label-Zuweisung |
| `classification.multi_min_confidence` | `0.45` | Schwelle für multi-label-Zuweisung |
| `classification.clip_prompt_template` | `"a photo of {label}"` | Fallback-Prompt, wenn ein Label keine eigenen `clip_prompts` hat |

## Finale Akzeptanzkriterien (Gesamtergebnis)

1. Ein neuer Einstellungen-Tab „Klassifizierung" listet Kategorien; je Kategorie
   lassen sich Labels anlegen/umbenennen/löschen, Modus (single/multi) umschalten.
   Der Konzept-Katalog ist als editierbarer Seed vorhanden.
2. „Bestehende Bilder klassifizieren" stößt einen Job an, der **ohne Modell-Neulauf**
   über die gespeicherten Embeddings + Tag-Scores klassifiziert; Fortschritt im Job-Dock.
3. Neu importierte Bilder werden nach Embedding+Tagging automatisch klassifiziert
   (Background-Queue, blockiert die UI nicht).
4. Die Lightbox zeigt eine Sektion „Klassifizierung" — je Kategorie die gefundenen
   Klassen mit Confidence.
5. Die globale Suche findet Bilder über Label-Namen (Autocomplete + Freitext),
   gleichrangig zu Tags/Captions.
6. Die Filter-Rail zeigt je Kategorie eine eigene Gruppe mit den Labels als
   Auswahl (mit Facet-Count); Auswahl filtert die Galerie korrekt
   (OR innerhalb Kategorie, AND über Kategorien).
7. `ruff`, `npm run lint`, `npm run build` grün; Doc-Code-Referenzen aktualisiert,
   ADR-010 vorhanden.

## Summary

Bilder lassen sich jetzt gegen frei definierbare Kategorien (Medium, Stil, Franchise,
Charakter …) klassifizieren, ohne ein zusätzliches Modell laufen zu lassen — die Fusion aus
CLIP-Embedding und WD14-Tag-Scores liest nur bereits gespeicherte Signale. Ein neuer
Einstellungen-Tab verwaltet Kategorien/Labels (Konzept-Katalog als editierbarer Seed), ein
Rerun-Step klassifiziert den Bestand retroaktiv, neue Importe laufen automatisch mit.
Ergebnis erscheint in der Lightbox, im Galerie-Filter (je Kategorie eine Gruppe) und in der
globalen Suche.

## Files touched

- Backend: `db/models.py` (+3 Tabellen), `alembic/versions/0029_classification.py`,
  `classification/{engine,scoring,seed}.py`, `jobs/{classification_job,classification_pipeline}.py`,
  `api/classification.py` (CRUD), `api/classify.py` (+`categories`-Step),
  `api/assets.py` (Filter/Facets/`AssetDetailDto.classifications`), `jobs/rerun_job.py`.
- Frontend: `models/classification.model.ts`, `store/classification/*`,
  `services/classification.service.ts`, `features/einstellungen/klassifizierung/*`,
  `features/galerie/lightbox/` (Klassifizierungs-Sektion), `features/galerie/filter-rail/`
  (Kategorie-Gruppen), `store/filters/*` (`classificationLabelIds`), Such-Autocomplete.
- Docs (Phase 6): `docs/models.md`, `docs/routes.md`, `docs/code-map.md`,
  `docs/decisions/010-bildklassifizierung-engine.md` (neu), `docs/glossary.md` (neu),
  `docs/PROJECT.md`.

## Commits

Phasen 1–5: siehe Commit-Log (`feat(classification): ...`, `feat(backend): classification
CRUD, ...`, `feat(frontend): P18 Phase 4 ...`, `feat(frontend): classification filter, ...`).
Phase 6 (Docs): `ffb7a92` — docs(backend): P18 Phase 6 - Docs & ADR-010 fuer Bildklassifizierung.

## Deviations from plan

- `docs/glossary.md` existierte im Projekt noch nicht (obwohl Teil der globalen
  Standard-Doc-Struktur) — in Phase 6 neu angelegt statt einer bestehenden Datei ergänzt.
- `docs/PROJECT.md`s Backlog-Tabelle war bereits vor P18 nicht mehr durchgängig aktuell
  (mehrere dort gelistete Pläne sind laut `STATE.md` längst archiviert); in Phase 6 bewusst
  nur der P18-Eintrag ergänzt, keine Generalüberholung der Tabelle.
- Ansonsten keine Abweichungen vom README-Kontrakt — Backend-CRUD, Engine-Signatur,
  HTTP-Kontrakt und Frontend-Typen wurden 1:1 wie spezifiziert umgesetzt (gegen den
  tatsächlichen Code in Phase 6 verifiziert).

## Follow-ups
- Text-getriggerte Smart-Alben (CLIP-Prompt als Smart-Trigger gegen Embeddings).
- „Mehr wie dieses" semantisch in der Lightbox (`search.py` kann `like_asset_id` schon).
- Unklassifiziert-Eimer: Bilder ohne Kategorie über Schwelle → Review-Bucket.
- Cluster-Vorschläge: unüberwachtes Clustern der Embeddings schlägt neue Kategorien vor.
