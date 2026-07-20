# Phase 3 — KnowledgeUpdateJob (Ergänzungs-Vorschläge im Lore Panel)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Sicherheitsregel + Kontrakt
- Konzept: Dok 060 Phase 6 (Knowledge Update), Konzept-ADR-006
- Phase 1: AI-Layer · **P25:** Patch-UI + Explainability-Element (wiederverwenden!) · **P22:** Validator, `update_entity`
- Bestand: `jobs/queue.py`, Lore Panel (P25)

## AK
- [x] `KnowledgeUpdateJob` (Capability `KnowledgeUpdate`) schlägt zu einer bestehenden Entity Ergänzungen/Korrekturen als **Patch** vor (kein Direkt-Write).
- [x] Im Lore Panel: Aktion „Ergänzen (KI)" → Patch-Vorschlag mit Diff (alt→neu) + Begründung; **Ablehnen** lässt Markdown unverändert, **Annehmen** schreibt über den P25-Patch-Pfad + erzeugt Explainability-Eintrag.
- [x] Ownership gewahrt: user-Werte werden nicht durch inferred-Vorschläge überschrieben (Vorschlag markiert, nicht erzwungen).
- [x] Nutzt das **geteilte** Explainability-Element (P26 Phase 3) — keine zweite Implementierung.
- [x] `ai.autonomy` = „aus" → Aktion nicht angeboten.

## Umsetzung
- [x] `jobs/knowledge_update_job.py` + Registrierung
- [x] Lore Panel (P25) um „Ergänzen (KI)" + Diff-Vorschau erweitern; Annehmen = bestehender PatchJob-Pfad
- [x] Doc: `docs/code-map.md`

## Deviations
- Nur `body` wird vorgeschlagen (kein strukturiertes Aliase/Beziehungen-Feld) — dieselbe
  bewusste Einschränkung wie Phase 2 (FINDINGS: ein rohes Text-LM liefert dafür nichts
  Verlässliches). Für „Warum geändert?" reicht das geteilte Popover; die Diff-Vorschau
  vor der Bestätigung ist ein einfacher Alt/Neu-Block im Panel (kein zweites Popover-
  Implementat, nur andere Nutzung derselben Explainability-Payload-Form).
- Zwei neue Backend-Routen statt einer: `POST /knowledge/ai/update-suggestion` (Vorschlag
  anfordern) + `POST /knowledge/ai/update-suggestion/accept` (annehmen, `owner=inferred`
  serverseitig fix) — die bestehende `/entities/{id}/patch`-Route ist laut eigenem
  Kontrakt-Kommentar fix auf `owner=user` verdrahtet und für KI-Korrekturen nicht nutzbar.
