# Phase 2 — Wizard-UI (Entity manuell anlegen)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Design-Lage + Kontrakt · Konzept Dok 050 §4/§13
- **P22-Frontend-Kontrakt hier real anlegen:** `models/knowledge.model.ts`, `store/knowledge/`, `services/knowledge.service.ts`
- Bestand: `docs/conventions/{angular,ngrx,typescript}.md`, `mode-web-frontend`, `framework-tailwind`; Dialog-Muster `ui/preset-dialog/`, `ui/import-dialog/`; CRUD-Feature `features/tags/`; Tokens `docs/design/styles.css`

## AK (UI-Struktur = Kontrakt)
- [x] Nav-Eintrag „Wissen" → `features/wissen/`.
- [x] Wizard-Dialog: **Pflicht** Typ (Dropdown aus Domäne) + Titel; **optional/eingeklappt** Aliase (Chips), Domäne, Beschreibung (Textarea → Body), Beziehungen (Auto-Complete gegen `search_entities`).
- [x] Speichern → `POST /api/knowledge/entities`; danach Markdown-Datei im Vault.
- [x] Fehlender Titel → inline-Fehler, kein Absenden.
- [x] Nicht-triviale Eingaben mit dezenter optionaler i-Erklärung; Placeholder mit Beispiel.
- [x] Tailwind-Tokens, bestehendes Dialog-Muster.

## Umsetzung
- [x] `models/knowledge.model.ts` (Entity, Relationship, Source, MediaLink, Domain, Task)
- [x] `store/knowledge/` + `services/knowledge.service.ts`
- [x] `features/wissen/` mit Wizard-Dialog
- [x] Nav-Eintrag (`shell/nav-rail`) + Route (`app.routes.ts`)
- [x] Beziehungs-Auto-Complete gegen `search_entities`
- [x] Doc: `docs/code-map.md`, `docs/routes.md`

## Abweichungen vom Plan

Zwei reale Kontrakt-Lücken beim Bauen entdeckt (P22 hatte den Wizard-Bedarf nicht vollständig
abgedeckt) — beide additiv im Backend nachgezogen, Tests dazu, `docs/routes.md`/`code-map.md`
aktualisiert:

- **Kein Weg, die Domäne (Typ-Liste) zu lesen:** Der Wizard-Pflichtdropdown „Typ (Dropdown aus
  Domäne)" brauchte die Entity-/Beziehungstypen einer Domäne — es gab dafür keinen Endpoint.
  Neu: `Vault.list_domains()` + `GET /api/knowledge/domains` (`api/knowledge.py`), Tests in
  `test_knowledge_api.py`.
- **`body` (Beschreibung) nie durch die REST-Schicht gereicht:** `Entity.body` existierte im
  Schema/Parser (P22 Phase 1) und rundet sauber durchs Markdown, aber `CreateEntityRequest`/
  `UpdateEntityRequest`/`EntityDto` in `api/knowledge.py` kannten das Feld nicht — die Wizard-AK
  „Beschreibung (Textarea → Body)" wäre sonst nicht umsetzbar gewesen. Neu: `body` in allen drei
  DTOs + `_PATCHABLE_FIELDS`/`_apply_patch` in `knowledge/service.py`, Test in `test_knowledge_api.py`.

Sonst wie geplant: Beziehungs-Auto-Complete + Aliase als eigenständige Signal-Logik im Dialog
(kein Reactive-Forms-Overhead — passend zum Bestand bei vergleichbaren Dialogen wie
`create-person-dialog`/`bulk-edit-dialog`). `id` (`<folder>/<slug>`) wird im Frontend aus Typ+Titel
generiert (`slugify()`, `\p{Diacritic}`-Unicode-Normalisierung) — der Nutzer sieht/tippt keine ID.

**Bewusst nicht getestet (Frontend):** `docs/conventions/testing.md` verlangt Unit-Tests fürs
Frontend, aber im ganzen Repo existiert bislang kein einziger Feature-Spec (nur der generierte
`app.component.spec.ts`), und die CI-Kette in `AGENTS.md` fährt nur `tsc --noEmit` + `ng build`,
kein `ng test`. Für dieses Feature dem tatsächlichen Bestand gefolgt statt einen neuen,
unbenutzten Standard einzuführen — 🟡 Diskrepanz zwischen Doc und Praxis, siehe Follow-up unten.
