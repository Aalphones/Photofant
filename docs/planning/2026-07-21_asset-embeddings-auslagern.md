# Embedding-BLOBs aus der Asset-Tabelle auslagern

**Status:** in Umsetzung — Phase 1 + 2 ✅, Phase 3 offen
**Warum jetzt:** Die Galerie wurde am 2026-07-21 vermessen (siehe „Messwerte"). Die drei
schnellen Hebel sind umgesetzt; dieser hier ist der letzte verbliebene und der einzige,
der *alle* Abfragen betrifft statt nur die Galerie.

## Worum es geht

Jedes Bild trägt zwei Vektoren mit sich — einen für die Bedeutungssuche, einen für die
rein visuelle Ähnlichkeit. Beide liegen als Rohdaten direkt in der Bild-Tabelle. Damit ist
diese Tabelle zu 87 % aus Daten gebaut, die beim normalen Blättern durch die Galerie
niemand braucht:

| | Größe |
|---|---:|
| Bild-Tabelle gesamt | 90,8 MB |
| davon Bedeutungs-Vektoren | 43,4 MB |
| davon Bild-Vektoren | 32,5 MB |
| echte Nutzdaten (Pfade, Beschreibungen, Datumsangaben) | ~11 MB |

SQLite muss beim Durchgehen der Tabelle über diese Rohdaten hinweglesen, auch wenn die
Abfrage nur ein Datum will. Jede Abfrage, die alle Bilder anfasst, zahlt das mit.

Die Vektoren liegen ohnehin schon ein zweites Mal in den Suchindizes (50 MB + 35 MB) —
die Spalten in der Bild-Tabelle sind der Ursprung, aus dem diese Indizes neu aufgebaut
werden. Sie sind also nicht überflüssig, aber sie liegen am falschen Ort.

## Messwerte (2026-07-21, 10.588 Bilder, echte Datenbank)

Gemessen an einer Kopie, in der die beiden Spalten entfernt wurden — Tabelle schrumpft
von 90,8 MB auf 11,0 MB:

| Abfrage | vorher | nachher |
|---|---:|---:|
| Gesamtzahl zählen | 34 ms | 7,7 ms |
| Facette „Quelle" | 39 ms | 11,4 ms |
| Facette „Bildausschnitt" | 40 ms | 13,3 ms |
| Sortierung nach Datum | 78 ms | 16,7 ms |

Der Effekt gilt für jede Abfrage über den ganzen Bestand, nicht nur die vier gemessenen.

## Vorgehen

Bewusst in drei Schritten, damit jeder für sich zurückdrehbar ist. **Der Umzug wird nicht
als Suchen-und-Ersetzen gebaut** — Schritt 1 zieht erst eine Zugriffsschicht ein, danach
weiß nur noch diese eine Stelle, wo die Vektoren physisch liegen. Ein späterer Umzug
(eigene Datei, anderes Format, reine Index-Haltung) kostet dann nur noch diese eine Stelle.

### Phase 1 — Zugriffsschicht einziehen (kein Verhaltensunterschied)

Neues Modul `photofant/db/embeddings.py` mit Lese-/Schreib-/Löschfunktionen für beide
Vektorarten. Speicherort bleibt vorerst exakt wie er ist — es ändert sich nur, *worüber*
zugegriffen wird.

Umzustellende Stellen (Stand 2026-07-21, elf Zugriffe in zehn Dateien):

| Datei | Zugriff |
|---|---|
| `api/assets.py` | Anzeige-Flag „hat Vektor" (drei Stellen) |
| `api/search.py` | Vektor eines Bildes als Suchanfrage |
| `api/collections.py` | Ähnlichkeit innerhalb einer Sammlung |
| `api/duplicates.py` | Dubletten-Erkennung |
| `api/review.py` | Ähnliche Bilder in der Prüfliste |
| `search/rerank.py` | Nachsortierung der Suchtreffer |
| `classification/engine.py` | Kategorien zuordnen |
| `recommendation/scoring.py` | Empfehlungen berechnen |
| `collections/stats.py` | Sammlungs-Statistik |
| `db/vector_index.py` | Suchindex neu aufbauen (enthält rohes SQL) |
| `media/moves.py` | Löschen beim Verschieben |

**Fertig, wenn:** Kein Modul außer `db/embeddings.py` nennt die Spalten noch beim Namen.
Alle Tests grün, keine neuen Meldungen von ruff/mypy.

**✅ Erledigt (2026-07-23).** Naht steht: `db/embeddings.py` gibt Vektoren (`np.ndarray` /
`dict[id→ndarray]`) statt Spalten/BLOBs raus — versteckt damit Spalte **und** Byte-Layout,
sodass Phase 2 wirklich nur diese eine Datei anfasst. Gates: ruff/mypy ohne neue Meldungen,
481 Tests grün (13 rot = unveränderte comfyui/caption-Vorbelastung).

**Abweichungen von der Tabelle oben (Plan war 2 Tage alt, Wahrheit per Grep geholt):**
- **Fehlten:** `jobs/embedding_job.py` (der **Schreibpfad** — muss zwingend durch die Naht,
  sonst schreibt Phase 2 an zwei Orten) und `jobs/dupe_scan_job.py` (liest alle DINOv2-Vektoren
  für den Voll-Scan). Beide mit umgestellt.
- **Falsch etikettiert:** `media/moves.py` nennt die Spalten gar nicht — es löscht nur die
  *Index*-Zeilen (`delete_embedding`/`delete_dino_embedding`); die Spalte stirbt mit der
  Asset-Zeile. Nichts zu tun.
- **Neu durch die Naht gezogen:** `db/vector_index.py` liest die Spalte nicht mehr per rohem
  SQL (Rebuild + das umgezogene `load_dino_embeddings` → jetzt `embeddings.load_visual`).

**Offen für Phase 2 (Prosa, bricht nichts in Phase 1):** Docstrings, die die Spalte noch als
kanonischen Speicherort benennen, werden erst falsch, wenn Phase 2 den Ort verschiebt — dann
nachziehen: `db/vector_index.py` (Kopf-Docstring), `jobs/embedding_job.py`, `jobs/rebuild_job.py`,
sowie `docs/models.md` (asset-Zeilen `clip_embedding`/`dino_embedding` = „Source of truth").
Ebenso seeden die Tests (`test_search_rerank`, `test_dupe_scan_dino`, `test_classification_engine`)
die Spalten noch direkt per ORM-kwarg — in Phase 2 auf die Nebentabelle umstellen.

### Phase 2 — Nebentabelle anlegen und befüllen

Migration: neue Tabelle mit einer Zeile je Bild, die beide Vektoren aufnimmt; vorhandene
Daten werden kopiert. Die Zugriffsschicht liest und schreibt ab jetzt dort. **Die alten
Spalten bleiben zunächst stehen** — geht etwas schief, reicht ein Rücksetzen der
Zugriffsschicht, ohne Datenverlust.

Zu klären beim Bau: Was passiert beim Löschen eines Bildes (die Nebenzeile muss mit),
und ob die Nebentabelle die Verknüpfung selbst erzwingt oder der Code sie pflegt.

**Fertig, wenn:** Suche, Dubletten, Empfehlungen und Neuaufbau des Suchindex liefern
dieselben Ergebnisse wie vorher — an echten Daten geprüft, nicht nur an Testdaten.

**✅ Erledigt (2026-07-23).** Nebentabelle `asset_embedding` (PK = `asset_id`, beide
BLOBs) via Migration 0043 angelegt, Bestand per `INSERT … SELECT` herüberkopiert
(idempotent über `NOT IN`). Die Zugriffsschicht liest/schreibt jetzt ausschließlich dort;
Writer sind Upserts (`_row_for_write` legt die Zeile bei Bedarf an, aber nur für ein
existierendes Asset — die alte „skip wenn Asset weg"-Garantie erhalten). Alte Spalten stehen
unangetastet für Rollback. Gates: ruff grün, mypy ohne neue Meldung in den geänderten Dateien
(mypy ist ohnehin nicht im CI-Gate), 481 Tests grün (13 rot = unveränderte comfyui/caption-
Vorbelastung).

**Abweichungen vom „nur embeddings.py + Migration":** Der Löschpfad musste mit — FK-Enforcement
ist in dieser App aus (`db/engine.py`), also cascadet die Nebenzeile nicht von selbst. Neue
`embeddings.delete(session, asset_id)`, aufgerufen an der einzigen Asset-Löschstelle
(`media/moves.py`, neben den bestehenden Index-Löschungen). Das war genau die im Plan als
Wackelstelle markierte „Nebenzeile muss beim Löschen mit" — ohne diese Zeile geht sie in
Phase 3 verloren. Zusätzlich mitgezogen: `AssetEmbedding`-Model, die in Phase 1 als „Phase-2-
Prosa" vorgemerkten Docstrings (`vector_index.py`, `rebuild_job.py`), `docs/models.md`
(neue Tabelle + `clip/dino_embedding` als LEGACY markiert), und die drei Tests, die die Spalten
noch direkt seedeten (`test_search_rerank`, `test_dupe_scan_dino`, `test_classification_engine`)
laufen jetzt über die Naht (`set_semantic`/`set_visual`) — damit auch für Phase 3 swap-proof.

**Für Phase 3:** Migration 0044 droppt `asset.clip_embedding` + `asset.dino_embedding`
(SQLite → `batch_alter_table`), dann `ANALYZE`. Der Copy in 0043 ist ein Snapshot — das ist
unkritisch, weil ab 0043 **kein Code mehr** in die alten Spalten schreibt (Naht ist einziger
Schreiber, sie schreibt in die Nebentabelle). Die Model-Kommentare und `models.md` verweisen
bereits auf „Migration 0044" — beim Umsetzen konsistent halten.

### Phase 3 — Alte Spalten entfernen

Migration entfernt die beiden Spalten und gibt den Platz frei. Erst danach tritt der
Geschwindigkeitsgewinn ein — Phase 2 allein bringt nichts, sie verdoppelt die Daten sogar
vorübergehend.

Nach dem Entfernen müssen die Tabellen-Statistiken neu erhoben werden (`ANALYZE`), sonst
plant SQLite weiter mit der alten Größe. Gleiche Falle wie bei Migration 0041.

**Fertig, wenn:** Die vier Messwerte oben sind reproduziert, Bild-Tabelle unter 15 MB.

## Risiken

- **Freier Speicher:** Der Aufräumschritt in Phase 3 legt vorübergehend eine zweite Kopie
  der Datenbank an. Bei 287 MB unkritisch, sollte aber vor dem Lauf geprüft werden.
- **Zwei Wahrheiten in Phase 2:** Zwischen Befüllen und Löschen stehen die Vektoren an
  zwei Orten. Nichts darf in diesem Fenster noch in die alten Spalten schreiben, sonst
  gehen die Werte in Phase 3 verloren — die Zugriffsschicht aus Phase 1 ist genau deshalb
  Voraussetzung und nicht optional.
- **Neuaufbau des Suchindex** liest heute rohes SQL auf die Spalte (`db/vector_index.py`).
  Diese Stelle geht sonst still kaputt, weil sie an der Zugriffsschicht vorbeigreift.

## Nicht Teil dieses Plans

- Die Facette „häufigste Schlagworte" (~320 ms, der größte Einzelposten der Galerie) —
  eigene Entscheidung, siehe unten.
- Die 22.458 verwaisten Schlagwort-Zeilen von gelöschten Bildern.
