# ADR-014 — Wissens-Lookup-Auto-Trigger ohne Rekursions-/Tiefenschutz

**Status:** Angenommen — umgesetzt (P24 Phase 1)
**Datum:** 2026-07-09
**Betrifft:** Plan `2026-07-01_p24-photofant-integration`, Phase 1

---

## Kontext

Der P24-Plan sah vor, den automatischen Trigger „Person bestätigt ohne Entity →
`KnowledgeLookupJob`" mit einem Rekursions-/Tiefenschutz abzusichern: `ParentJobId`/`Depth`
auf dem Job, ein Setting `jobs.maxDepth`, dazu `knowledge.autoLookup` — beides laut Plan-Text
„von P22 reserviert" bzw. „keine neuen Keys nötig".

Beim Umsetzen von Phase 1 stellte sich heraus: **keins von beidem existiert.** `JobStatus`
(`jobs/queue.py`) hat kein `ParentJobId`-/`Depth`-Feld, kein `JobKind` in den aktuell 20+
Job-Arten trägt eins, und `jobs.maxDepth` sowie `knowledge.autoLookup` stehen nirgends in
`settings.py` oder im archivierten P22-Kontrakt. Die Plan-Annahme war schlicht falsch — P22
hat diese Infrastruktur nie gebaut.

## Optionen

- **Das unterstellte Gerüst nachbauen** (`ParentJobId`/`Depth` generisch auf `JobStatus`,
  `jobs.maxDepth`-Setting, Tiefenprüfung in jedem Enqueue-Pfad): verworfen — spekulative
  Infrastruktur für ein Szenario, das im aktuellen Job-Graphen nicht eintreten kann (s.u.).
  Keiner der bestehenden 20+ Job-Kinds hat ein solches Feld; ein Alleingang nur für
  `KNOWLEDGE_LOOKUP` wäre Inkonsistenz ohne Nutzen.
- **Generisches Gerüst jetzt vorbauen, für spätere Jobs (P27 Gemma):** verworfen fürs
  Jetzt — YAGNI. Wird gebraucht, sobald ein Job existiert, der tatsächlich einen Folge-Job
  desselben/verwandten Typs auslösen kann (frühestens P27s `KnowledgeImportJob`/
  `KnowledgeUpdateJob`). Dort neu bewerten, mit echtem Anwendungsfall vor Augen statt Vorrat.
- **Auf den bestehenden Dedup-Mechanismus verlassen (gewählt).**

## Entscheidung

`KnowledgeLookupJob` (`jobs/knowledge_lookup_job.py`) ist ein **Sackgassen-Job**: er prüft,
ob eine Entity existiert, und legt im Negativfall höchstens **eine** `knowledge_tasks`-Zeile
an (`TaskService.create_task`, dedupliziert bereits exakt über `kind`+`context`). Er ruft nie
einen weiteren Job auf — eine Endlosschleife kann in diesem Job-Graphen strukturell nicht
entstehen. Der Trigger-Punkt (`api/review_queue.py`, „confirm"-Zweig) prüft zusätzlich vorab,
ob die Person bereits verknüpft ist (`KnowledgeService.linked_entity_ref`), bevor er den Job
überhaupt anstößt.

`knowledge.auto_lookup` (Snake_Case, konsistent mit den übrigen `settings.py`-Keys — die
Plan-Notation `autoLookup` war informell) wurde als **echtes neues** Setting angelegt,
Default `true`.

## Konsequenzen

- Kein totes `ParentJobId`/`Depth`-Gerüst im Code, das niemand aufruft.
- Der Schleifenschutz-Punkt aus der P24-README bleibt AK-konform erfüllt: „genau eine
  Aufgabe, ohne Job-Endlosschleife" — durch Dedup + Sackgassen-Eigenschaft, nicht durch
  Tiefenzählung.
- **Re-evaluieren bei P27:** Sobald ein Job existiert, der selbst weitere Jobs (auch anderer
  Art) auslösen kann, ist die Sackgassen-Annahme nicht mehr gegeben — dann greift diese ADR
  nicht mehr und ein echter Tiefenschutz ist fällig.
