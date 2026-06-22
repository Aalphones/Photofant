# P11 — Duale Duplikaterkennung: DHash + CLIP parallel

**Status:** pending  
**ADR:** 007 (erweitert ADR-006)

DHash erkennt nur pixel-nahe Kopien (Kompression, leichte Helligkeit). CLIP erfasst
semantische Ähnlichkeit — gleiche Szene, andere Aufnahme, andere Bearbeitung.
Beide laufen parallel (OR-Logik): ein Paar landet in der Queue, wenn DHash **oder**
CLIP Ähnlichkeit meldet. Im UI werden beide Scores separat gezeigt.

---

## Overview

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Schema & Settings | standard | pending |
| 2 | Backend-Engine (Scan + Similar) | heikel | pending |
| 3 | API-Kontrakt (DTOs) | standard | pending |
| 4 | Frontend-Einstellungen | standard | pending |
| 5 | Frontend-Review-UI | standard | pending |

---

## Kontrakt (Cross-Modul-Ankerpunkt)

### DB-Schema nach Migration

```sql
-- review_item
phash_distance  INTEGER  NULL   -- DHash Hamming (0–64); NULL wenn nur CLIP ausgelöst hat
clip_distance   REAL     NULL   -- CLIP Cosine-Distance (0.0–1.0); NULL wenn nur DHash
```

### Backend → Frontend API (beide Endpoints)

```python
# DupePairDto (review.py + duplicates.py)
phash_distance:      int | None    # Hamming-Distanz, NULL bei CLIP-only
phash_similarity_pct: int | None  # (1 - d/64)*100, NULL bei CLIP-only
clip_distance:       float | None  # Cosine-Distance, NULL bei DHash-only
clip_similarity_pct: int | None   # (1 - d)*100, NULL bei DHash-only
triggered_by:        str          # "phash" | "clip" | "both"
```

### Settings (neu)

| Key | Typ | Default | Beschreibung |
|---|---|---|---|
| `dupe_phash_enabled` | bool | `true` | DHash-Suche aktiv |
| `dupe_threshold` | int | `10` | DHash Hamming-Schwelle (0–32, bleibt) |
| `dupe_clip_enabled` | bool | `true` | CLIP-Suche aktiv |
| `dupe_clip_threshold` | float | `0.15` | CLIP Cosine-Distance-Schwelle (0.05–0.30); entspricht 70–95% Ähnlichkeit |

### Frontend-Modell-Erweiterung

```typescript
// ProcessingConfig (config.model.ts)
dupePhashEnabled:   boolean   // neu
dupeClipEnabled:    boolean   // neu
dupeClipThreshold:  number    // neu, 0.05–0.30 (intern Cosine-Distance)
// dupeThreshold bleibt
```

```typescript
// PersonDupePair (@photofant/models)
phash_distance:       number | null
phash_similarity_pct: number | null
clip_distance:        number | null
clip_similarity_pct:  number | null
triggered_by:         'phash' | 'clip' | 'both'
```

---

## Finale Abnahme-Kriterien (Gesamt)

- [ ] Zwei Bilder, die nur per CLIP als ähnlich erkennbar sind (DHash-Distanz > 32), landen nach Scan in der Review-Queue mit CLIP-Score
- [ ] Zwei fast identische Bilder (DHash ≤ Schwelle) landen mit DHash-Score, CLIP-Score optional
- [ ] Einstellungsseite zeigt Toggles + Schwellen für beide Methoden, Beschriftungen erklären die Wirkung ohne Fachbegriffe
- [ ] Person-Duplikate-Dialog und Lightbox-Similar nutzen beide Methoden
- [ ] Deaktiviert man DHash, finden nur noch CLIP-Treffer statt — und umgekehrt
- [ ] Migration läuft sauber durch (`phash_distance` nullable, `clip_distance` neu)
- [ ] CLIP-Scan graceful degradiert wenn kein `clip_embedding` für ein Asset vorhanden (ignoriert es)

---

## Risiken

🟡 **CLIP-Pairwise O(N²):** Alle Embeddings laden + NumPy-Matmul. Bei N=10 000 Assets: ~30 MB Embeddings, ~400 MB Similarity-Matrix. Über ~5 000 Assets muss der Scan in Chunks arbeiten (1 000er-Blöcke). Chunking-Logik ist in Phase 2 einzuplanen.

🟡 **phash_distance NOT NULL heute:** Bestehende `ReviewItem`-Zeilen haben `phash_distance` immer gesetzt. Die Migration macht das Feld nullable — bestehende Rows bleiben unverändert (Wert bleibt, kein Backfill nötig). Code der `phash_distance` liest, muss auf `None` vorbereitet werden.

🟡 **CLIP nicht für alle Assets:** Wenn `auto_embed` früher aus war, haben einige Assets kein `clip_embedding`. CLIP-Scan ignoriert sie stillschweigend — kein Fehler, aber manche Paare können nur via DHash gefunden werden.

---

## Archiv-Footer

**Summary:** —  
**Files touched:** —  
**Commits:** —  
**Deviations:** —  
**Follow-ups:** —
