# Phase 4 — Rebuild-Job + Vault↔Cache-Reconcile

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Kontrakt + Risiko „Vault↔Cache-Drift" · Phase 3: `KnowledgeService`
- Bestand: `jobs/queue.py` (3 Spuren, Registrierung), `jobs/rebuild_job.py`/`reconcile_job.py` + `maintenance/reconcile.py` (Muster), `features/wartung/`
- Konzept: Dok 030 §6 (Wartungs-Jobs)

## AK
- [ ] `RebuildKnowledgeCacheJob` baut den Cache aus dem Vault neu; nach Leeren + Job identisch zum Vorzustand.
- [ ] Reconcile: hand-geänderte Markdown-Datei (neuere `mtime`) wird übernommen; Cache-only-Zeilen ohne Vault-Datei entfernt (Markdown gewinnt).
- [ ] Job läuft über die bestehende Queue (Background-Spur), SSE-Fortschritt wie andere Jobs.
- [ ] In der bestehenden Wartungs-Sicht auslösbar (an vorhandenes Reconcile/Rebuild angehängt, kein neuer Screen), mit dezenter i-Erklärung.

## Umsetzung
- [ ] `jobs/knowledge_rebuild_job.py` + `jobs/knowledge_reconcile_job.py` (oder Integration in bestehendes `reconcile_job.py` — Bearbeiter entscheidet, begründen)
- [ ] Job-Typen in `queue.py` registrieren
- [ ] Wartungs-Trigger + i-Erklärung („Baut die Wissens-Schnellsuche neu aus deinen Notizen auf")
- [ ] Doc: `docs/code-map.md`, ggf. `docs/routes.md`
- [ ] **Gesamt-P22:** finale AK + Smoke-Checkliste der README gegenprüfen
