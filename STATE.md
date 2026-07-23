# STATE

**Aktiver Plan:** `docs/planning/2026-07-23_gesichter-mehrfachauswahl/`
**Phase:** 4/8 — Face-Upscale: ComfyUI-Auto-Import auf Face-Ziele erweitern (ADR-036) (✅ complete)
**Nächster Schritt:** Phase 5 — Face-Selection: eigener NgRx-State-Slice
(`phase-5-face-selection-state.md`, Komplexität `standard` → `/model sonnet` reicht).

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
