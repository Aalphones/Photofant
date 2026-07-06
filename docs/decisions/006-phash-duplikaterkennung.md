# ADR-006 — pHash (DHash) als Ähnlichkeits-Metrik für Duplikaterkennung

**Status:** Superseded by ADR-018
**Datum:** 2026-06-19  
**Betrifft:** Plan `2026-06-19_duplikaterkennung`, Phase 1

---

## Kontext

Photofant soll beim Import erkennen, ob ein Bild bereits im Bestand vorhanden ist — nicht nur als exakte Kopie (gleicher SHA-256), sondern auch als leicht bearbeitete Variante: heller/dunkler gemacht, beschnitten, verlustbehaftet re-exportiert, andere Auflösung. Der bestehende `content_hash` (SHA-256) deckt nur Byte-für-Byte-Identität ab, nicht visuelle Ähnlichkeit.

Anforderungen:
- Kein ML-Modell nötig (offline-first, minimaler Ressourceneinsatz)
- Schnell genug für 10 000-Bilder-Vergleiche als Hintergrundjob
- Tolerant gegenüber Helligkeitsänderungen, kleinen Crops, JPEG-Re-Exporten
- 64-Bit-Fingerabdruck (8 Byte/Asset, Index in DB-Spalte möglich)

---

## Optionen

### aHash (Average Hash)
Skaliert Bild auf 8×8, vergleicht jeden Pixel gegen den Durchschnitt.  
**Nachteil:** anfällig für globale Helligkeitsverschiebungen; Helligkeit +10 → viele Bit-Flips → hohe False-Positive-Rate bei harmlosen Edits.

### pHash (DCT-basierter Perceptual Hash)
Diskrete Kosinus-Transformation auf 32×32-Downscale, niedrige Frequenzen als Hash.  
**Vorteil:** robust gegen Helligkeits- und Kontraständerungen, JPEG-Artefakte.  
**Nachteil:** teurer als aHash/DHash; Bibliothek `imagehash` liefert pHash, aber DHash schneidet in der Praxis bei kleinen Edits besser ab.

### DHash (Difference Hash)
Skaliert auf 9×8, vergleicht je zwei benachbarte Pixel in jeder Zeile → 64 Bits.  
**Vorteil:** robust gegen globale Helligkeit (Differenz, kein Absolutwert); sehr schnell; wenig False-Positives bei üblichen Foto-Edits.  
**Nachteil:** empfindlicher als pHash gegenüber harten Crops (Bildausschnitt wechselt Inhalt) — bei Threshold ≤ 10 kein Problem.

### CLIP-Cosine-Ähnlichkeit
Semantisches Embedding (768 Dim); bereits als `clip_embedding` auf `asset` vorhanden.  
**Vorteil:** findet auch semantisch ähnliche, aber visuell verschiedene Bilder.  
**Nachteil:** zu weit — „zwei Frauen im Park" wäre ein Duplikat; kein geeignetes Signal für Dateivarianten. Außerdem: kein CLIP-Modell für alle Assets zwingend vorhanden.

---

## Entscheidung

**DHash** (`imagehash.dhash`, `hash_size=8` → 64 Bit).

- Robustester Kandidat für die Use Cases: Re-Export (JPEG Qualität 80 vs. 95), leichte Helligkeit, kleiner Crop
- Kein ML-Modell, keine GPU, kein externes Service
- Hamming-Distanz ≤ 10 (Default, konfigurierbar) filtert False-Positives zuverlässig heraus
- 8 Byte pro Asset als `INTEGER`-Spalte; O(N) Vergleich über alle Hashes möglich
- `imagehash`-Bibliothek nutzt Pillow (bereits Abhängigkeit) — kein neuer Framework-Lock

Die Spalte heißt `phash` (historischer Name im Konzept), der Algorithmus ist DHash.

---

## Konsequenzen

- `asset.phash` (INTEGER nullable): 64-Bit-DHash; NULL bis Berechnung gelaufen
- `asset.original_id` (INTEGER FK → asset.id nullable): gesetzt bei Entscheidung „A ist Original" / „B ist Original"
- `review_item`-Tabelle: hält unentschiedene Paare mit `phash_distance`
- Schwelle `dupe_threshold` in `settings.json` (Default 10, Range 0–20): steuert ab welcher Distanz ein Paar als Duplikat-Kandidat gilt
- Zukünftig: CLIP-Ähnlichkeit könnte als optionale zweite Stufe (nur wenn Threshold knapp) ergänzt werden — heute noch kein Bedarf

> Ergänzt durch ADR-007
