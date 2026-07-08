# P37 — DINOv2 Re-Ranking + visuelle Duplikate

> Ergänzt einen **zweiten, rein visuellen Embedder** (DINOv2) neben SigLIP2. Zweck: bei jeder Suche
> **mit einem Query-Bild** die SigLIP2-Kandidaten nach *visueller Erscheinung* neu sortieren
> (retrieve-then-rerank), und den Duplikat-Scan auf dieses visuelle Signal umstellen. SigLIP2 versteht
> den **Inhalt**, DINOv2 die **Erscheinung** (Bildaufbau, Perspektive, Farben, Stil). *(private, lean.)*

## Abhängigkeit
**P35 muss stehen** (swappbare Bild-Embedder-Naht + Rollen-Parameter `resolve_image_embedder(role=...)`).
**P36 ergänzt sich:** P37 hängt sein Re-Ranking in die Bild→Bild-Pfade, die P36 verdrahtet
(`like_asset_id` + `POST /api/search/by-image`). P37 kann vor oder nach P36 laufen — überschneidet sich
nur im Rerank-Aufruf innerhalb dieser Endpoints (in P37 Phase 3 beschrieben, robust gegen „P36 noch nicht da").

## Ziel
1. **DINOv2 als zweiter Embedder** auf P35s Naht — image-only (kein Text-Encoder), eigener Vektorraum,
   eigener Manifest-Eintrag mit `role: "visual_rerank"`. Ein Modelltausch bleibt „Adapter + Registry-Zeile + Manifest".
2. **Two-Stage Retrieval** für Bild→Bild: SigLIP2 liefert Top-100 Kandidaten, DINOv2 re-rankt auf Top-10.
3. **Duplikat-Scan auf DINOv2** als Primär-Signal (visuelle Erscheinung = was ein Duplikat ausmacht),
   Schwellwert an realem Set neu justiert.

## Die harte Grenze (Klartext, gilt für den ganzen Plan)
**DINOv2 kann keinen Text.** Re-Ranking greift ausschließlich, wenn ein **Query-Bild** existiert:
- `like_asset_id` (ähnlich zu Asset X) → Rerank ✅
- `POST /api/search/by-image` (Upload, P36) → Rerank ✅
- Duplikat-Scan (Bild gegen Bild) → DINOv2 als Primär-Signal ✅
- **Text-Semantiksuche** („roter Sportwagen") → **kein Rerank**, SigLIP2-Reihenfolge bleibt unangetastet.

Das ist keine Schwäche, sondern die Bauartgrenze: ohne visuellen Anker im DINOv2-Raum gibt es nichts zu vergleichen.

## Warum es sich lohnt (und was es kostet)
- **Nutzen:** SigLIP2 findet thematisch Passendes, ordnet aber innerhalb des Themas nicht nach „sieht aus wie".
  DINOv2 (self-supervised, State-of-the-Art für visuelle Ähnlichkeit/Copy-Detection) sortiert genau danach —
  gleicher Bildaufbau, Perspektive, Farben, Stil landen oben. Das trifft oft die subjektiv „richtigen" Top-Treffer.
- **Kosten (🟡, einmalig):** Reembed der Bibliothek läuft künftig durch **zwei** Modelle (doppelte GPU-Zeit),
  und der Vektor-Speicher wächst um einen zweiten Index. Background-Worker, blockiert nichts — aber spürbar beim
  ersten vollen Reembed.
- **Query-Zeit ist billig:** Re-Ranking berührt nur ~100 Kandidaten, deren DINOv2-Vektoren vorberechnet im Index
  liegen — ein Query-Embed + 100 Skalarprodukte. Kein spürbarer Latenz-Aufschlag.

## Zentrale Entscheidungen
- **ADR-023 — DINOv2 als visueller Re-Ranker** (`docs/decisions/023-dinov2-visual-rerank.md`):
  Variante **DINOv2 ViT-B/14 mit Registers (768-dim)**. Begründung: Re-Ranking von 100 Kandidaten ist zur
  Suchzeit vernachlässigbar teuer; der reale Kostenfaktor ist Reembed-Zeit + Vektor-Speicher, und die RTX 3060
  trägt bereits SigLIP2. Register-Variante liefert sauberere globale Features als das Original ohne Registers.
  Alternativen: **ViT-L/14 (1024-dim)** — besseres Retrieval, aber ~3× Parameter/Speicher, dokumentiert als
  Upgrade-Pfad falls Qualität > Ressourcen; **ViT-S/14 (384-dim)** verworfen (Qualitätssprung zu klein für den
  Mehraufwand eines zweiten Modells). ONNX-Verfügbarkeit ist **Phase-1-Check** — DINOv2 ist ein reines ViT und
  notfalls selbst exportierbar; kein fertiges Repo wird hier blind vorausgesetzt.
- **ADR-024 — Two-Stage Retrieval & Rerank-Naht** (`docs/decisions/024-two-stage-rerank.md`):
  SigLIP2-KNN (Kandidaten-Pool) → DINOv2-Cosine-Rerank (Ergebnis). Rerank ist eine **eigene, testbare Funktion**
  neben der Suche, kein Umbau der KNN-Schicht. Aktivierbar/abschaltbar per Setting; degradiert bei fehlendem
  DINOv2-Modell oder Text-Query sauber auf reines SigLIP2. Duplikat-Scan wird auf DINOv2 als Primär-Signal
  umgestellt (SigLIP2-Dupe-Schwellwert bleibt als Settings-Key inert für Rollback).

## Settings.json (vorab freigeben)
- `rerank.enabled` (Default **true**) — Two-Stage global an/aus.
- `rerank.candidatePoolSize` (Default **100**) — wie viele SigLIP2-Kandidaten in den DINOv2-Rerank gehen.
- `dupe_dino_threshold` (neuer Key) — Cosine-Distanz-Schwelle für den DINOv2-Duplikat-Scan; Default in Phase 4
  an realem Set bestimmt. Der alte `dupe_clip_threshold` bleibt bestehen (inert nach Umstellung, für Rollback).

## Kontrakt (Cross-Modul-Anker)
- **Image-only-Embedder:** DINOv2 erfüllt `embed(image) -> np.ndarray` (L2-normalisiert) + `dim`, aber
  **nicht** `embed_text`. Das `Embedder`-Protokoll (`inference/interfaces.py`) macht `embed_text` **optional**
  (eigenes `TextEmbedder`-Protokoll oder `embed_text` als optionale Methode — in Phase 1 entschieden). Ein Aufrufer,
  der Text braucht, prüft die Fähigkeit, statt blind zu rufen.
- **Resolver mit Rolle:** `resolve_image_embedder(role="visual_rerank")` liefert DINOv2 (P35s Rollen-Parameter).
  `role="semantic_search"` bleibt SigLIP2. Genau ein aktives Modell pro Rolle.
- **Zweiter Vektorraum:** Spalte `asset.dino_embedding` (BLOB, deferred) + `vec0`-Tabelle `vec_asset_dino`
  (`float[768]`, cosine). Getrennt von `vec_asset_embedding` (SigLIP2) — kein gemeinsamer Index, keine Kollision.
- **Rerank-Funktion:** `rerank_by_appearance(query_dino_vec, candidate_asset_ids) -> list[(asset_id, score)]`
  (in `search/rerank.py` o.ä.). Lädt die DINOv2-Vektoren der Kandidaten, sortiert nach Cosine zum Query.
- **Ledger:** ein zweites Fertig-Flag `ProcessingLedger.dino_embedding_done` (analog `embedding_done`), damit
  Reembed pro Modell steuerbar ist und der Fortschritt sichtbar bleibt.

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | DINOv2-Adapter + image-only-Naht + Manifest | heikel (Protokoll-Aufweichung + neues Preprocessing) | ✅ complete |
| 2 | Zweiter Vektorraum + Embedding-Job + Migration | heikel (zweiter Index + Ledger-Flag + Migration) | ✅ complete |
| 3 | Two-Stage Re-Ranking in der Bild→Bild-Suche | heikel (Rerank-Naht, Degradation bei Text/ohne Modell) | ✅ complete |
| 4 | Dupe-Scan auf DINOv2 + Schwellwert-Rekalibrierung | standard | pending |

## Finale AK (Gesamt)
- [ ] DINOv2 ist ein zweiter, über die Modelle-UI ladbarer Embedder (`role: "visual_rerank"`); Adapter besitzt
      Preprocessing/Dim selbst; `resolve_image_embedder(role="visual_rerank")` liefert ihn.
- [ ] `Embedder`-Protokoll trägt einen image-only-Embedder ohne `embed_text`, ohne dass Text-Aufrufer brechen.
- [ ] Jedes aktive Asset hat nach Reembed **zwei** Embeddings (SigLIP2 1024-dim + DINOv2 768-dim); `vec_asset_dino`
      ist gefüllt.
- [ ] Bild→Bild-Suche (`like_asset_id` und Upload) liefert Top-10, die nach DINOv2-Erscheinung neu sortiert sind;
      A/B gegen reines SigLIP2 zeigt sichtbar „ähnlicher aussehende" Top-Treffer.
- [ ] **Text-Suche ist unverändert** (kein Rerank, keine Regression gegenüber P35/P36).
- [ ] Rerank degradiert sauber: kein DINOv2-Modell aktiv **oder** `rerank.enabled=false` **oder** Text-Query
      → reines SigLIP2-Ergebnis, kein Crash.
- [ ] Duplikat-Scan läuft auf DINOv2; findet echte visuelle Duplikate zuverlässiger; `dupe_dino_threshold` justiert.
- [ ] Kein Laufzeit-Netzwerkzugriff außer Modell-Download über die Settings-UI; kein torch-Zwang für den Embedder.
- [ ] ADR-023 und ADR-024 liegen in `docs/decisions/`.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. **[Oberste Wackelstelle] Rerank verbessert sichtbar:** ein Asset mit vielen thematisch ähnlichen Bildern als
   Quelle (`like_asset_id`) → Top-10 mit Rerank vs. `rerank.enabled=false` vergleichen. Sitzen mit Rerank die
   *optisch* ähnlichsten (gleicher Aufbau/Perspektive/Farbe) weiter oben? Wenn nein → Preprocessing/Normalisierung
   prüfen (Smoke-Grund #2 in Konfidenz).
2. **[Wackelstelle] Duplikat-Qualität:** „Duplikate scannen (vollständig)" nach DINOv2-Umstellung → bekannte echte
   Duplikate treffen, Fremdpaare draußen? `dupe_dino_threshold` nachziehen.
3. **Text bleibt heil:** `POST /api/search/semantic {"query":"ein roter Sportwagen"}` → gleiche Qualität wie vor
   P37 (Rerank darf hier nicht greifen).
4. **Degradation:** DINOv2 in der Modelle-UI deaktivieren → Bild→Bild-Suche liefert reines SigLIP2-Ergebnis ohne Fehler.
5. Neues Bild importieren → Log zeigt **zwei** Embeddings („SigLIP2 1024 dims", „DINOv2 768 dims").

## Risiken
- 🟡 **DINOv2-Preprocessing weicht von SigLIP ab** — ImageNet-Normalisierung (mean/std, *nicht* 0.5/0.5) + andere
  Resize-Größe (typ. 224/256). Falsches Preprocessing = stumpfe Vektoren ohne Crash. Mitigation: gegen
  `preprocessor_config.json` des Repos verifizieren (Check in Phase 1).
- 🟡 **Doppelter Reembed-Aufwand + Speicher** — zwei Modelle durch die GPU, zweiter Vektor-Index. Einmalig,
  Background. Mitigation: separates Ledger-Flag, damit nur der DINOv2-Teil nachlaufen kann, ohne SigLIP2 neu zu rechnen.
- 🟡 **Rerank-Degradation muss lückenlos sein** — jeder Pfad ohne Query-Bild oder ohne DINOv2-Modell muss auf reines
  SigLIP2 zurückfallen, nie crashen. Mitigation: Fähigkeits-Check statt blindem Aufruf; explizite Tests je Zweig.
- 🟡 **ONNX-Export** — falls kein fertiger Community-Export brauchbar ist, muss DINOv2 selbst nach ONNX exportiert
  werden (opset, dynamische Achsen). Mitigation: Phase-1-Check vor Adapter-Finalisierung.

## Konfidenz — wo ich am unsichersten bin
1. **Ob ein brauchbarer DINOv2-ONNX-Export vorliegt** (mit/ohne Registers, Vision-only) — Check: HF/onnx-community
   in Phase 1 sichten, sonst Selbst-Export. Bestimmt, ob Phase 1 „Adapter" oder „Adapter + Export" ist.
2. **DINOv2-Preprocessing-Details** (Resize-Größe, ImageNet-Stats, CLS-Token vs. Pooling für das globale Embedding)
   — Check: `preprocessor_config.json` + Modell-Card lesen, bevor der Adapter finalisiert wird.
3. **Ob P35s `embed_text` sauber optional gemacht werden kann**, ohne bestehende SigLIP/CLIP-Aufrufer zu brechen
   — Check: `inference/interfaces.py` (P35-Endzustand) + alle `embed_text`-Aufrufer in Phase 1 zuerst lesen.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_
