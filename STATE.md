# STATE

**Aktiver Plan:** `docs/planning/2026-07-22_ml-jobs-worker-prozess/`
**Phase:** 2/4 — Erstmigration: Captioning + Tagging (complete, Code fertig)
**Nächster Schritt:** `/clear`, dann `/model sonnet` (Phase 3 ist als „standard" eingestuft —
die Cross-Process-Signalisierung und der Remote-Wait-Pfad stehen jetzt als Muster, Phase 3
wiederholt sie nur für vier weitere Job-Arten), danach `/implement` → Phase 3
„Rest-Migration — Embedding, Heuristics, Classification, Face, Clustering, Dupe-Scan".

**🟡 Phase 2 komplett, Laufzeit-Verhalten noch nicht gegengeprüft (private-Profil, User-Smoke):**
Captioning + Tagging laufen ab jetzt über den Worker-Prozess (`enqueue_remote`), die
Cross-Process-Pipeline-Signalisierung für FACE/CLASSIFICATION ist verdrahtet
(`worker/signals.py::emit_pipeline_signal`), `ruff` und `mypy --strict` sind grün (nur 3
vorbestehende Fehler in `caption_job.py`, unverändert seit vor diesem Plan). Noch nicht live
getestet: Worker-PID-Log beim Captioning/Tagging, FACE wird in beiden Job-Reihenfolgen genau
einmal ausgelöst, Lightbox bleibt während Captioning/Tagging flott, `session_manager` im
API-Prozess bleibt leer. Details + Deviations:
`docs/planning/2026-07-22_ml-jobs-worker-prozess/phase-2-captioning-tagging.md` → „Report-Back".

**🟡 Vorgezogener Teilfix (2026-07-24, außerhalb der Plan-Reihenfolge):** VRAM-Leck live
gemeldet — Tagging-/Captioning-Modelle (WD14, Florence-2/JoyCaption/Qwen2.5-VL) blieben nach
dem Import dauerhaft im VRAM, weil `main.py::_idle_eviction_loop` seit Phase 2 nur noch gegen
die leere API-Prozess-Instanz von `session_manager`/`generative_engine` läuft — die echten
Instanzen leben seit Phase 2 im Worker-Prozess, dort räumte niemand auf. Fix: Teil von Phase 3
Aufgabe 4 vorgezogen — `worker/process.py` hat jetzt seine eigene Idle-Eviction-Schleife plus
Shutdown-Cleanup. `main.py`s Schleife bleibt bestehen (wird noch für Embedding/Face gebraucht,
bis die in Phase 3 migrieren). Details: `phase-3-rest-migration.md` → Aufgabe 4. `ruff`/
`mypy --strict` grün auf der geänderten Datei; Laufzeit-Bestätigung (VRAM nach Import-Batch
wirklich frei nach `idleTimeoutSeconds`) noch offen — private-Profil, User-Smoke.

**🟡 Architektur-Lücke gefunden und für diese Phase mitgefixt:** `rerun_job.py` rief
Tagging/Captioning bisher direkt auf (nicht über die Job-Queue) — das hätte Florence-2/WD14
weiterhin im API-Prozess geladen, sobald jemand „Bilder erneut verarbeiten" nutzt, und damit
genau das Problem reproduziert, das dieser Plan beheben soll. Für Tags/Caption jetzt gefixt
(neuer `enqueue_remote_and_wait()`-Pfad); Embedding/Heuristics/Classification/Face haben
denselben Bug noch, behoben in Phase 3 (in FINDINGS.md getaggt, dort auch das Wie).

ADR-033 war beim Planen die nächste freie Nummer, ist inzwischen an vier andere Pläne vergeben
(033-036) — die reale Nummer für diesen Plan ist **ADR-037**
(`docs/decisions/037-ml-jobs-worker-prozess.md`).

## „Embedding-BLOBs aus der Asset-Tabelle auslagern" abgeschlossen (alle 3 Phasen)

Archiviert: `docs/archive/2026-07/2026-07-21_asset-embeddings-auslagern.md` (Report-Back
je Phase direkt im Dokument, kein separates README). Bild-Tabelle verliert die beiden
BLOB-Spalten (90,8 → soll 11 MB), alle Voll-Abfragen sollen 3-5× schneller werden. Zugriff
läuft komplett über `photofant/db/embeddings.py` (Phase 1), Vektoren liegen in der
Nebentabelle `asset_embedding` (Migration 0043, Phase 2), die alten Spalten sind per
Migration 0044 (Phase 3) rausgefallen. ruff grün, mypy ohne neue Meldung, Migrationskette
geprüft (`alembic heads` → `0044`).

**🟡 Noch offen (private-Profil, User-Smoke — nicht von mir gelaufen):** `alembic upgrade
head` auf der echten DB (Migrationen 0042, 0043, 0044 in einem Rutsch) plus die vier
Messwerte aus dem Plan (Ziel: Bild-Tabelle unter 15 MB). Vorher Speicher checken — Phase 3
legt vorübergehend eine zweite DB-Kopie an (bei 287 MB unkritisch, 320 GB frei).

## „Gesichter-Mehrfachauswahl" abgeschlossen (alle 8 Phasen)

Archiviert: `docs/archive/2026-07/2026-07-23_gesichter-mehrfachauswahl/README.md` (Summary/Files
touched/Commits/Deviations/Follow-ups in den Bottom-Sektionen dort). Der „Auswählen"-Button im
Gesichter-Tab ist jetzt echt: Checkbox-Overlay, Mehrfachauswahl, Bulk-Leiste mit Löschen /
Hochskalieren (echtes Face-Upscale, ADR-036) / Zu-Trainingsset-hinzufügen (Face-Crops als
eigenständige Mitglieder, ADR-035, `CollectionItem.face_id`).

## P39 „Wissen: mehr Tiefe, Design nachgezogen" abgeschlossen (alle 8 Phasen)

Archiviert: `docs/archive/2026-07/2026-07-22_wissen-tiefe-und-design/README.md` (Summary/Files
touched/Deviations/Follow-ups in den Bottom-Sektionen dort). Interview fragt Merkmale aktiv ab
statt sie aus Prosa zu raten, Web-Recherche bevorzugt Domänen-Quellen, Detail-Dialog zeigt
Zeitstempel/Album-Button/KI-Banner im Design, personen-verknüpfte Entities zeigen ihre erkannten
Fotos automatisch, KI-Ergänzung bezieht deren Captions/Tags als Hinweis ein.

**🟡 Offen aus Phase 3 (kein Follow-up-Ticket, nur hier notiert):** Ein Interview über eine
Person mit bereits bestehender Notiz schreibt die erkannten Merkmale noch nicht — nur beim
Neuanlegen. Details/Grund: Archiv-Pfad oben → `phase-3-merkmale-end-to-end.md` → „Report-Back".

## „Gesichter-Bereinigung" abgeschlossen (alle 4 Phasen)

Archiviert: `docs/archive/2026-07/2026-07-22_gesichter-bereinigung/README.md` (Summary/Files
touched/Commits/Follow-ups in den Bottom-Sektionen dort). Pro Person lassen sich Ausreißer-
Gesichter (falsch geclustert oder technisch unbrauchbar) finden und per neuem „Gesichter
bereinigen…"-Dialog gezielt löschen, sortiert nach einem on-demand berechneten Score
(ADR-033).

## P38 „Wissen: Web-Recherche + neue Oberfläche" abgeschlossen (alle 8 Phasen)

Archiviert: `docs/archive/2026-07/2026-07-20_p38-gemma-web-discovery/README.md` (Summary/Files
touched/Deviations/Follow-ups in den Bottom-Sektionen dort). Web-Recherche (Gemma + echte
Websuche, nur bei explizitem Klick, nur auf öffentlichen Entitäten), Merkmale als echte Felder
mit eigenem Owner, komplette neue Wissens-Oberfläche (Übersicht, Detail, zwei Wizards,
Personen-Karten-Chip, Lightbox-Wissen-Tab).

## Zwischendrin erledigt (nicht P38): Job-Pipeline überlebt Datei-Verschiebungen

Bilder blieben nach dem Import massenhaft ohne Gesichter/Beschreibung/Tags. Ursache: jeder
Verarbeitungs-Job bekam beim Einreihen einen festen Dateipfad mit — und die Datei zieht
mitten in der Verarbeitung um (Personen-Zuordnung, Favorit, Zusammenführen, Person löschen).
Toter Pfad → Job stirbt → nichts wiederholt ihn. Jobs bekommen jetzt nur noch die Bild-Nummer
und lösen den Pfad beim Start auf (`media/asset_paths.py`). Zusätzlich: Tagging und Einbetten
melden ihren Nachfolge-Schritten „durch" auch im Fehlerfall (vorher strandeten Gesichter und
Klassifizierung dauerhaft), und die Wartungsseite hat einen Nachzieh-Lauf plus die Kennzahl
„Unfertig". Voller Testlauf: 438 grün, 13 rot = unveränderte Vorbelastung unten.

**Offener Folgepunkt (User-Entscheidung vertagt):** Ist ein Modell nicht installiert (z.B. kein
Beschreibungs-Modell), wird dessen Erledigt-Häkchen nie gesetzt — die Kennzahl „Unfertig"
zeigt dann dauerhaft alle Bilder an, und der Nachzieh-Lauf reiht sie folgenlos immer wieder
ein. Kein Schaden, nur eine lügende Zahl. Fix-Option: beim Zählen die Schritte überspringen,
für die kein Modell aktiv ist (braucht eine Modell-Abfrage im Zählpfad, die Modelle laden kann).

## Offene Smoke-Tests (User)

- **„Gesichter-Mehrfachauswahl"** — alle 8 Phasen, noch nicht gegengeprüft. Vollständige
  Checkliste (Wackelstellen zuerst): `docs/archive/2026-07/2026-07-23_gesichter-mehrfachauswahl/
  README.md` → „Smoke-Checkliste". Kernpfad: **zuerst** `alembic upgrade head` laufen lassen
  (Migration 0042 — PK-Umbau, ungewöhnlichster Migrations-Schritt im ganzen Projekt — läuft in
  einem Rutsch bis 0044 durch, siehe „Embedding-BLOBs"-Smoke unten), danach im Gesichter-Tab
  „Auswählen" → mehrere Gesichter anklicken (Checkbox statt Lightbox), löschen, hochskalieren
  (Crop wird größer/schärfer, Cleanup-Score-Ansicht zeigt es danach nicht mehr als
  upscale-bedürftig), zu einem Trainingsset hinzufügen (auch ein Gesicht ohne Quell-Foto testen).
- **„Embedding-BLOBs aus der Asset-Tabelle auslagern"** — Code fertig, Migration nicht
  gelaufen. Nach `alembic upgrade head`: Bild-Tabelle unter 15 MB? Die vier Messwerte aus
  `docs/archive/2026-07/2026-07-21_asset-embeddings-auslagern.md` → „Messwerte" grob
  reproduzieren (Gesamtzahl zählen, Facette „Quelle"/„Bildausschnitt", Sortierung nach Datum
  spürbar schneller). Vorher Speicher checken (Phase 3 legt kurz eine zweite DB-Kopie an).
- **P39 „Wissen: mehr Tiefe, Design nachgezogen"** — alle 8 Phasen, noch nicht gegengeprüft.
  Vollständige Checkliste (Wackelstellen zuerst): `docs/archive/2026-07/
  2026-07-22_wissen-tiefe-und-design/README.md` → „Smoke-Checkliste". Kernpfad: Interview mit
  ausgefüllten Eckdaten übernimmt die Werte wörtlich; Web-Recherche zeigt bevorzugte Quellen;
  Person mit vielen Fotos zeigt sie automatisch und der KI-Vorschlag greift danach erkennbar
  auf deren Captions/Tags zurück.
- **Gesichter-Bereinigung Phase 4** — manueller Browser-Check, kein Mockup vorhanden
  (freihändig nach `split-dialog`-Muster gebaut): Menüpunkt „Gesichter bereinigen…" öffnet
  den Dialog, Sortierung nach Verdacht + Score-Badges (grün→amber→rot) + Tooltip mit
  Gründen sichtbar, Löschen fragt einmal nach und aktualisiert die Personen-Karte
  (Fotoanzahl/Portrait). Details: `docs/archive/2026-07/2026-07-22_gesichter-bereinigung/
  phase-4-frontend-ui.md` → „Akzeptanzkriterien".
- **P38 Phase 3+4** — Parser-Trefferquote (5-10 Läufe gegen reale Personen) + API-Live-Smoke,
  warten auf ein gebundenes Gemma-Modell auf dieser Maschine. Vollständige Checkliste:
  `docs/archive/2026-07/2026-07-20_p38-gemma-web-discovery/README.md` → „Smoke-Checkliste"
  (Wackelstellen zuerst nach Konfidenz-Ausweis sortiert) und `phase-4-api-routen.md` →
  „AK dieser Phase" (🟡-Punkte).
- **P38 Phase 8** — neu, noch nicht gegengeprüft: Personen-Karten-Chip/Nudge öffnet das
  Detail-Modal ohne Navigation; Lightbox-Wissen-Tab zeigt Ring/„Vollständiges Profil"/„Weitere
  Bilder von {Name}"/„Recherchieren"; „Interview starten"/„Recherchieren"/„Vollständiges Profil"
  schließen die Lightbox und öffnen `/wissen` mit dem richtigen Deep-Link (Detail-Modal bzw.
  vorbelegter Wizard). Details: `phase-8-personen-lightbox.md` → „Report-Back" (im Archiv-Pfad
  oben).
- **P35** GGUF-Gemma-Runtime → `docs/archive/2026-07/2026-07-20_p35-gemma-gguf-runtime/README.md`
- **P26** Empfehlungs-Engine → `docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`
- **Empfehlungs-Cache-Invalidierung** → `docs/archive/2026-07/2026-07-20_recommendation-cache-invalidation/README.md`
- **Lightbox-Tab-Panel** → `docs/archive/2026-07/2026-07-20_lightbox-tabbed-panel.md`

## Vorbelastung (unverändert)

- `tests/test_comfyui_run.py` — 9 Fehler auf unverändertem Stand (`run_comfyui_run_job()`
  fehlt ein Argument).
- `tests/test_comfyui_auto_import.py` (3×, `SimpleNamespace` ohne `toggles`) und
  `test_caption_config.py::test_validate_rejects_unimplemented_instruct_mode`.
  Gesamt 13 rote Tests, alle P38-fremd, zuletzt vor P38 Phase 4 geprüft.
- `uv run ruff check .` über das **ganze** Backend meldet 7 Altbestand-Fehler (alte
  Migrationen 0020/0024, `api/assets.py` B008, `inference/tools.py`,
  `jobs/comfyui_run_job.py`). Geänderte Dateien sind grün.
- `backend/photofant/api/persons.py:203` (Zeilennummer kann verschieben) — vorbestehender
  `mypy`-Fehler in `_person_portrait_face_ids` (`dict()` gegen `Sequence[Row[Any]]`).

## Backlog

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan steht.
- `docs/planning/2026-07-21_asset-embeddings-auslagern.md` — Galerie-Performance, letzter
  großer Hebel (Bild-Tabelle 90,8 → 11 MB, alle Voll-Abfragen 3-5× schneller). Bereit zum
  Start, hängt an nichts.
- `docs/planning/2026-07-22_ml-jobs-worker-prozess/` — Lightbox/API blockiert während
  Tagging/Captioning/Embedding & Co. laufen (GIL-Kontention, nicht ein vergessenes `to_thread`).
  Alle Modell-Inferenz-Jobs ziehen in einen dauerhaften Worker-Prozess um. 4 Phasen, bereit zum
  Start, hängt an nichts.
