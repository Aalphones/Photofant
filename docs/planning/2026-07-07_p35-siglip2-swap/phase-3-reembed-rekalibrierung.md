# Phase 3 — Re-Embed + Schwellwert-Rekalibrierung

**Komplexität:** standard · **Status:** pending

## Kontext (vor dem Bauen lesen)
- `backend/photofant/jobs/rerun_job.py` — `run_rerun_job(asset_ids="all", steps=["embedding"], ...)`. **Das ist der
  Re-Embed-Pfad** (resettet `embedding_done`, ruft `_run_embedding`). Kein neuer Job nötig.
- `frontend/src/app/ui/rerun-dialog/` + `store/…` — die „Neuverarbeitung"-UI, über die der Rerun ausgelöst wird
  (prüfen, dass der Schritt „Embedding" + Ziel „alle" wählbar ist; falls ja, keine Code-Änderung — nur Bedienung).
- `backend/photofant/settings.py` — `dupe_clip_threshold` (0.03), `training_near_dupe_clip_threshold` (0.05),
  `_LEGACY_/_MIGRATED_DUPE_CLIP_THRESHOLD` (Vorlage, falls ein Default-Shift als Settings-Migration nötig wird).
- `backend/photofant/jobs/dupe_scan_job.py`, `api/duplicates.py`, `api/review.py` — Konsumenten des Schwellwerts
  (nur lesend; **nicht** ändern, nur der Default/Settings-Wert wird justiert).

## Ablauf (kein neuer Code, außer ggf. Default-Anpassung)
Diese Phase ist überwiegend **Bedienung + Messung**, nicht Implementierung:
1. SigLIP2 in der Modelle-UI herunterladen + aktivieren (CLIP deaktivieren).
2. „Neuverarbeitung: Embedding, alle" auslösen → wartet auf Abschluss (Background-Worker).
3. „Duplikate scannen (vollständig)" auslösen; an bekannten echten Duplikaten prüfen, wo SigLIP2 sie in der
   Cosine-Distanz einsortiert → `dupe_clip_threshold` justieren, bis echte Dupes treffen und Fremdpaare draußen bleiben.
4. Analog `training_near_dupe_clip_threshold` an einem Trainingsset-Beispiel gegenprüfen.

## AK der Phase
- [ ] Nach dem Re-Embed hat jedes aktive Asset ein 1024-dim Embedding (Stichprobe: Log „Embedded asset N (1024 dims)",
      `SELECT count(*) FROM vec_asset_embedding` ≈ Zahl aktiver Assets).
- [ ] `dupe_clip_threshold` ist auf SigLIP2 justiert (neuer Default in `settings.py` **und** — falls User bereits
      einen Wert hat — via Settings-Migration analog zum bestehenden `_LEGACY`-Muster, sonst überschreibt der alte
      CLIP-Wert die Kalibrierung nicht). Begründung des neuen Werts im Report-Back.
- [ ] `training_near_dupe_clip_threshold` gegengeprüft/justiert.
- [ ] Klassifizierungs-Rerun eines Bildes läuft fehlerfrei (Fusion liest die neuen Embeddings).
- [ ] `ruff check .` grün; Tests grün.

## Doc-Updates
- [ ] `docs/decisions/021-siglip2-embedder.md` — Abschnitt „kalibrierte Schwellwerte" mit End-Werten + Begründung nachtragen.
- [ ] STATE.md auf `(kein aktiver Plan)` bzw. auf P36 zeigen lassen; Plan nach `docs/archive/2026-07/` verschieben.

## Deviations (während der Umsetzung entdeckt & gefixt)
Phase sollte laut Plan reine Bedienung sein — zwei echte Bugs haben das erste SigLIP2-Aktivieren
blockiert, beide gefixt:
1. **Manifest unvollständig:** `manifest.json` (`siglip2-large-patch16-384`) listete `onnx/text_model.onnx`
   nicht aber das zugehörige `onnx/text_model.onnx_data` (2.26 GB, ONNX-External-Data — der Text-Encoder
   war nur ein 533-KB-Graph-Gerüst ohne Gewichte). Gegen die echte HF-Dateiliste verifiziert und ergänzt.
2. **Keine Enable/Disable-Exklusivität:** Es gab keinen Mechanismus, der beim Aktivieren eines Modells
   Geschwister-Modelle derselben Rolle deaktiviert — CLIP und SigLIP2 standen nach dem Download beide auf
   `enabled=1` für `semantic_search`, der Resolver zog ungeordnet den ersten Treffer (CLIP). Neue Funktion
   `deactivate_role_siblings()` (`backend/photofant/jobs/download_job.py`) mit `EXCLUSIVE_ROLES = {"semantic_search"}`
   — an allen drei Registry-Schreibpfaden eingehängt (Managed-Download, Component-Register-Local,
   In-Place-Register-Local). `heavy_captioner` bewusst ausgenommen (mehrere Modelle gleichzeitig aktiv ist
   dort Absicht). ruff + mypy auf beiden geänderten Dateien grün (mypy-Fehler in `download_job.py:121`
   vorbestehend, nicht von diesem Fix verursacht — per `git stash` gegengeprüft).
Kaputter Halb-Download (`D:\Models\_Photofant\siglip2-large-patch16-384`, nur `vision_model.onnx` +
Gerüst-Textmodell) + verwaiste Registry-Zeile entfernt, damit ein sauberer Neu-Download möglich ist.

## Report-Back
