# ADR-013 — ComfyUI-Edit-Import erzeugt ein eigenes Asset (löst ADR-009 teilweise ab)

**Status:** Akzeptiert · 2026-07-01
**Querverweise:**
- [ADR-009](009-comfyui-default-auto-import.md) — **teilweise abgelöst**: der Import-Schritt selbst
  (Default-Endpunkt, Warten/Timeout/Cleanup) bleibt unverändert; nur das Ergebnis eines
  erfolgreichen Imports ändert sich von „neue `Version`" zu „neues `Asset`".
- P21 (Galerie: Stapel & Tab-Konsolidierung), Phase 1 — Auslöser dieser Entscheidung.

---

## Kontext

P21 baut eine Stapel-Gruppierung, die Original + alle Edit-Varianten eines Bildes zeigt,
inklusive automatischer Cross-Person-Wanderung: editiert man ein Foto von Person X und
die Gesichtserkennung auf dem Edit erkennt Person Y, soll das Edit automatisch bei
Person Y landen (Original bleibt bei X).

Untersuchung ergab: dieser Automatismus existierte nirgends. `import_comfyui_output`
(`comfyui/importer.py`) legte für **jeden** ComfyUI-Default-Import (Upscale/Edit/Inpaint,
ADR-009) immer eine `Version`-Zeile an — nie ein eigenes `Asset`. Gesichtserkennung
(`face_job.py`) läuft ausschließlich über `asset_id`; auf `Version`-Zeilen läuft sie nie.
Ohne eigenes Asset gibt es also nie eine Gesichtserkennung auf dem Edit, folglich auch
keine automatische Umhänge-Logik. `original_id` wurde im ganzen Code nur manuell gesetzt
(Lightbox-Ad-hoc-Vergleich, Duplikat-Review) — nie automatisch durch einen Edit-Import.

## Optionen

| Option | Beschreibung |
|---|---|
| **A — ComfyUI-Default-Edit wird eigenes Asset** | `import_comfyui_output` legt ein vollwertiges `Asset` an (eigener `content_hash`, volle Pipeline: Tags/Caption/Faces/Embedding/pHash), setzt `original_id` auf das Quell-Asset. Ermöglicht die im P21-Kontrakt vorausgesetzte automatische Cross-Person-Wanderung. |
| B — Bei ADR-009 bleiben (Version) | P21 verliert die automatische Wanderung; Cross-Person-Fälle bleiben rein manuell (Reimport + Lightbox-Verknüpfung). Einfacher, aber widerspricht dem in P21 abgenommenen Kontrakt. |

## Entscheidung

**Option A.** Der Default-Import (`upscale`/`edit`/`inpaint`, ADR-009) und der manuelle
Ergebnis-Import (`POST /api/comfyui/results/import`) erzeugen künftig ein eigenes `Asset`
statt einer `Version`. Beide teilen sich dieselbe neue Import-Funktion
(`comfyui/importer.py::import_comfyui_output`), die dieselbe Pipeline wie ein normaler
Foto-Import durchläuft (Hash, Instance, `ProcessingLedger`, pHash+Dupe-Review, Tagging/
Caption/Face/Embedding-Jobs), zusätzlich `original_id = <Quell-Asset>` setzt und die Datei
weiterhin in `personX/edits/` ablegt (nicht `photos/`) — das unterscheidet ein Edit optisch
im Dateisystem, ändert aber nichts an der DB-Semantik.

`materialize_assignment` (`media/person_folders.py`) legt Kopien für einen neuen Person-
Zuordnung bisher immer in `photos/` ab — für Assets mit gesetztem `original_id` wird das
auf `edits/` umgestellt, damit ein automatisch umgehängtes Edit auch physisch als Edit
erkennbar bleibt.

## Konsequenzen

- Jeder ComfyUI-Edit kostet ab sofort eine volle Pipeline-Runde (Tags/Caption/Face/
  Embedding) statt nur eines Thumbnails — bewusster Trade-off für echte Cross-Person-
  Wanderung und Stapel-Konsistenz. Bestehende `Version`-Zeilen vom Typ `comfyui`
  (vor diesem Wechsel importiert) bleiben unverändert; keine Migration rückwirkend.
- Editor-Dialog-Edits (Crop/Rotate/Freistellen, `type` ≠ `comfyui`) sind **nicht**
  betroffen — sie bleiben bewusst leichte `Version`-Zeilen ohne eigene Pipeline
  (Entscheidung siehe P21-README).
- `VersionDto`/`import_as_version`-Endpunkt bleiben unverändert für alle anderen
  Edit-Typen.
