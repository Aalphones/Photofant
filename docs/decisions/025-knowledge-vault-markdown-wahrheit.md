# ADR-025 — Wissensbasis: Markdown ist die Wahrheit, SQLite ist Cache

**Status:** Angenommen — Fundament umgesetzt (P22 Phase 1: Vault + Entity-Schema + Parser)
**Datum:** 2026-07-08
**Betrifft:** Plan `2026-07-01_p22-knowledge-engine`, hält den geteilten Kontrakt für P23–P27

---

## Kontext

Photofant bekommt eine generische Wissensbasis (Konzept „Agentic Knowledge Base", Dok 010/020).
Wissen sind Entities (Filme, Schauspieler, Charaktere …) mit Beziehungen. Die Frage ist, **wo das
Wissen kanonisch lebt**: in der SQLite-DB (wie alles andere in Photofant) oder in Dateien.

## Optionen

- **SQLite als Quelle der Wahrheit** (wie Assets/Faces): verworfen — Wissen soll für Menschen lesbar,
  von Git versioniert, von Hand editierbar und von einem LLM verstehbar sein. Eine DB-Zeile ist nichts
  davon; ein Export wäre ein zweites, driftanfälliges Format.
- **Nur Markdown, keine DB:** verworfen — Titel-/Alias-Suche und Graph-Abfragen über hunderte Dateien
  wären langsam und müssten jede Query den ganzen Vault lesen.
- **Markdown = Wahrheit, SQLite = reiner Cache (gewählt).**

## Entscheidung

**Die Markdown-Dateien im Vault sind die einzige Quelle der Wahrheit. SQLite ist ein jederzeit aus dem
Vault neu aufbaubarer Cache.**

- **Vault-Layout:** `knowledge/<type-plural>/<slug>.md` (eine Datei = eine Entity),
  `knowledge/domains/<domain>.yaml` (erlaubte Typen), `knowledge/prompts/` (leer, später P27).
- **Entity-Frontmatter** trägt die strukturierten Felder (`id`, `type`, `title`, `aliases`, `status`,
  `owner`, `confidence`, `domain`, `media_links`, `relationships`, `sources`), der Body darunter ist
  freier Markdown-Artikel. Round-Trip Entity → Markdown → Entity ist verlustfrei (inkl. Body).
- **Domänen-agnostisch:** die Engine kennt keinen Typ wie „Actor" hart. Entity- und Beziehungstypen
  stehen ausschließlich in der Domänen-Datei; die mitgelieferte Beispiel-Domäne ist „Movies". Der
  Typ→Ordner-Bezug (`Actor` → `actors/`) steht explizit in der Domäne — kein automatisches
  Pluralisieren (bricht bei nicht-englischen Domänen).
- **Ownership** schützt Nutzerdaten: Priorität `user > manual > web > inferred`; ein Schreibzugriff mit
  niedrigerer Priorität überschreibt keinen höheren Wert (MVP: Ablehnung). User-Werte haben immer
  `confidence 1.0`.
- **ID-Stabilität:** `id` (`<type>/<slug>`) ist unveränderlich; Titel/Slug dürfen sich ändern →
  Umbenennung ist ein Datei-Move plus Cache-Update, nie ein ID-Wechsel.

## Konsequenzen

- Der Cache (Tabellen `knowledge_*`, ab Phase 2) darf jederzeit gelöscht und aus dem Vault identisch
  neu aufgebaut werden. Bei Vault↔Cache-Drift gewinnt Markdown (Reconcile-Job, Phase 4).
- Jede Persistenz läuft über den `KnowledgeService` (Phase 3), Markdown-first — nie direkt DB/Datei.
- Ein LLM (P27) verändert nie eine Datei direkt, sondern liefert einen Patch, der validiert und dann
  geschrieben wird.
- Embeddings/Graph werden nie gespeichert, sondern aus dem Markdown erzeugt — ein Neuaufbau ist immer
  möglich.

## Anmerkung zur Nummer

Der Plan (2026-07-01) reservierte hierfür „ADR-010" — diese Nummer war jedoch längst durch
`010-bildklassifizierung-engine` belegt (der Plan-Text beruhte auf einem veralteten Blick auf
`docs/decisions/`). Diese Entscheidung bekommt daher die nächste real freie Nummer **025**. Das im Plan
zusätzlich reservierte „ADR-011" (intelligente Jobs erweitern die Job-Queue statt Agenten-Framework)
wird erst in **P24** real angelegt und dort mit der dann freien Nummer versehen.
