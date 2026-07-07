# P36 — Reverse Image Search + Lightbox-Ähnliche

> Reverse Image Search über die globale Suche (Drag & Drop / Upload → Galerie zeigt ähnliche Bilder als Filter)
> und in der Lightbox eine Sektion „Ähnliche Bilder" (10 Vorschläge + „mehr" → öffnet die Galerie in der
> Reverse-Search zu genau diesem Bild). **Baut auf P35** (swappbarer Bild-Embedder). *(private, lean.)*

## Abhängigkeit
**P35 muss stehen** — P36 nutzt `resolve_image_embedder()` (P35s Naht), um ein **hochgeladenes** Bild
einzubetten. Backend für Bild-zu-Bild über *vorhandene* Assets existiert schon (`POST /api/search/semantic`
mit `like_asset_id`, heute ohne Frontend-Aufrufer) — P36 verdrahtet es und ergänzt den Upload-Pfad.

## p26-Kompatibilität (bewusste Vorgabe)
Die Lightbox-Sektion „Ähnliche Bilder" wird als **generische Related-Rail** gebaut, die Karten aus
`{ asset_id, thumbnail, score, reasons? }` rendert. P36 füllt `reasons = null` (rein visuelle Ähnlichkeit).
**P26** (Recommendation Engine) rendert später **dieselbe Rail** an **derselben Stelle** mit gefüllter
`reasons`-Begründungskette (Graph-Signale). So teilt sich der Screen einen Eigentümer statt zweier Container.

## Kontrakt (Cross-Modul-Anker)
- **`POST /api/search/by-image`** (neu, multipart): Feld `file` (Bild-Upload) + optional `limit` (Default aus
  `reverseSearch.similarLimit`). → dekodiert das Bild, `resolve_image_embedder().embed()`, `vector_index.search()`,
  filtert soft-deleted raus (wie `semantic_search`). Response: `{ hits: [{asset_id, score}] }`. 409
  `SEMANTIC_SEARCH_UNAVAILABLE` wenn kein Embedder aktiv (Muster aus `api/search.py`).
- **`POST /api/search/semantic` mit `like_asset_id`** (existiert): bleibt der Pfad für „ähnlich zu Asset X"
  (Lightbox + „mehr"-Sprung). Kein Umbau, nur Frontend-Anbindung.
- **Galerie-Filter „ähnlich zu":** `list_assets` (`api/assets.py`) bekommt einen Parameter `similar_ids`
  (geordnete id-Liste) → liefert genau diese Assets **in dieser Reihenfolge** (Ähnlichkeit absteigend).
  Der Store hält den Reverse-Zustand (Quell-Thumbnail + hits) als eigenen Filter-Modus, entfernbar per Chip.
- **Related-Rail-Item (Frontend-Typ):** `{ assetId: number; score: number; reasons: Reason[] | null }` —
  P26 erweitert `reasons`, P36 lässt es `null`.

## Settings.json (vorab freigeben)
- `reverseSearch.similarLimit` (Default **10**) — Anzahl Vorschläge in der Lightbox.
- `reverseSearch.maxUploadBytes` (Default z.B. 15 MB) — Obergrenze für den Upload, saubere Fehlermeldung darüber.
- `reverseSearch.minScore` (Default 0.0 = aus) — optionaler Ähnlichkeits-Floor für Treffer.

## Design-Lage (🟡 vor Umsetzung klären)
Kein bestätigtes Mockup für „Reverse-Drop in der globalen Suche" und „Lightbox-Ähnliche". P26 lief freihändig
(kein Mockup, freigegeben); Lightbox-Eigentümer ist P15. **Vor Phase 2/3:** `docs/design/` auf ein Such-/Lightbox-
Mockup prüfen — existiert eins, ist es verbindlich; existiert keins, freihändig nach p26-Kartenkonzept (vom User
so freigegeben: „gleich p26-kompatibel bauen").

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Backend: Upload-Embed-Endpoint + Galerie-`similar_ids` | standard | done |
| 2 | Globale Suche: Drag & Drop / Upload → Reverse-Filter | heikel (UI-Fluss + Filter-Modus) | pending |
| 3 | Lightbox „Ähnliche Bilder" (Related-Rail, p26-kompatibel) + „mehr"-Sprung | standard | pending |
| 4 | Text-Semantiksuche verdrahten (toter `/semantic`-Text-Pfad → Frontend) | standard | pending |

## Finale AK (Gesamt)
- [ ] Bild in die globale Suche ziehen **oder** hochladen → Galerie zeigt ähnliche Bilder (nach Ähnlichkeit sortiert),
      mit entfernbarem Chip „Ähnliche zu [Vorschau]".
- [ ] Drag-&-Drop-Zone ist ohne Erklärung erkennbar (sichtbare Affordance + Tooltip); Upload-Fehler (zu groß /
      kein Bild / kein Embedder aktiv) zeigen eine klare deutsche Meldung.
- [ ] Lightbox zeigt bis zu 10 ähnliche Bilder als Rail; Klick öffnet das Bild.
- [ ] „mehr"-Button öffnet die Galerie in der Reverse-Search zu genau dem offenen Bild.
- [ ] Die Rail-Komponente akzeptiert `reasons` (für P26) — P36 übergibt `null`, ohne dass die Struktur später bricht.
- [ ] **Text-Semantiksuche:** Freitext (z.B. „roter Sportwagen") liefert über `/api/search/semantic` thematisch
      passende Bilder in der Galerie; klar von der bestehenden exakten Tag-/Caption-Suche unterscheidbar.
- [ ] Kein Laufzeit-Netzwerkzugriff; Upload-Bild wird nur eingebettet, nicht importiert/gespeichert.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. **[Wackelstelle] Filter-Modus-Konsistenz:** Reverse-Filter setzen, dann anderen Filter/Suche wechseln → sauberer
   Übergang, kein „hängender" Reverse-Zustand, Chip verschwindet beim Zurücksetzen.
2. Fremdes Bild (nicht in der Bibliothek) hochladen → plausible ähnliche Treffer; sehr großes Bild → klare Fehlermeldung.
3. Lightbox öffnen → 10 Ähnliche; „mehr" klicken → Galerie in Reverse-Search zum selben Bild.
4. Bild aus der Bibliothek als Quelle (`like_asset_id`) → das Bild selbst taucht nicht unter seinen eigenen Ähnlichen auf.

## Risiken
- 🟡 **Filter-Modus-Verzahnung** — der Reverse-Zustand ist ein Sonderfall neben Text-/Tag-/Facetten-Filtern.
  Sauber als eigener, exklusiver Modus im `store/filters/` modellieren, sonst „geistert" er neben anderen Filtern.
- 🟡 **Upload-Sicherheit/-Größe** — Upload dekodieren ohne zu importieren; Größe/Typ prüfen, nichts auf Platte legen.
- 🟡 **Design ohne Mockup** — siehe Design-Lage; vor Phase 2/3 klären, nicht still erfinden.

## Konfidenz — wo ich am unsichersten bin
1. **Wie der Galerie-Store einen geordneten id-Filter am saubersten aufnimmt** — Check: `store/filters/` +
   `store/gallery/` + `api/assets.py` (`list_assets`, `q_mode`-Zweige) beim Umsetzen von Phase 1/2 zuerst lesen.
2. **Ob ein Such-/Lightbox-Mockup existiert** — Check: `docs/design/` sichten (Design-Lage oben).

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-up: P26 rendert seine Empfehlungskarten in die hier gebaute Related-Rail.
