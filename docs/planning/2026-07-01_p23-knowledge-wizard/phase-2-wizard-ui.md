# Phase 2 — Wizard-UI (Entity manuell anlegen)

**Komplexität:** standard · **Status:** pending

## Kontext
- README → Design-Lage + Kontrakt · Konzept Dok 050 §4/§13
- **P22-Frontend-Kontrakt hier real anlegen:** `models/knowledge.model.ts`, `store/knowledge/`, `services/knowledge.service.ts`
- Bestand: `docs/conventions/{angular,ngrx,typescript}.md`, `mode-web-frontend`, `framework-tailwind`; Dialog-Muster `ui/preset-dialog/`, `ui/import-dialog/`; CRUD-Feature `features/tags/`; Tokens `docs/design/styles.css`

## AK (UI-Struktur = Kontrakt)
- [ ] Nav-Eintrag „Wissen" → `features/wissen/`.
- [ ] Wizard-Dialog: **Pflicht** Typ (Dropdown aus Domäne) + Titel; **optional/eingeklappt** Aliase (Chips), Domäne, Beschreibung (Textarea → Body), Beziehungen (Auto-Complete gegen `search_entities`).
- [ ] Speichern → `POST /api/knowledge/entities`; danach Markdown-Datei im Vault.
- [ ] Fehlender Titel → inline-Fehler, kein Absenden.
- [ ] Nicht-triviale Eingaben mit dezenter optionaler i-Erklärung; Placeholder mit Beispiel.
- [ ] Tailwind-Tokens, bestehendes Dialog-Muster.

## Umsetzung
- [ ] `models/knowledge.model.ts` (Entity, Relationship, Source, MediaLink)
- [ ] `store/knowledge/` + `services/knowledge.service.ts`
- [ ] `features/wissen/` mit Wizard-Dialog
- [ ] Nav-Eintrag (`shell/nav-rail`) + Route (`app.routes.ts`)
- [ ] Beziehungs-Auto-Complete gegen `search_entities`
- [ ] Doc: `docs/code-map.md`
