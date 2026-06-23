# P9 · Phase 4 — Flux-Edit & Inpainting

> Rating: **heikel** (img2img-Parameterraum + Masken-UI + Template-System) · Status: **complete**

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (flux-edit, inpaint, prompt-templates)
- [Konzept](../../Konzept-Photofant.md) §8.1, **§8.4 (Templates)**, §5 (prompt_template)
- `docs/design/js/editor-tools.jsx` (Flux-Tool-Referenz)

## Akzeptanzkriterien

- Flux-Edit (img2img): Prompt + Params (strength/steps/guidance/seed), Ergebnis als Version (`type = flux_edit`), Seed in `version.params` (Reproduzierbarkeit).
- Prompt-Templates: Migration + CRUD + UI (Liste im Editor-Tool, per Klick anwenden, `{person}` wird aus der Personen-Zuordnung ersetzt; ohne Person → Hinweis); single + bulk.
- Inpainting: Masken-Maler im Editor (Brush/Radierer auf Canvas-Overlay), Maske + Prompt → Job → Version (`type = inpaint`); single only.
- Erstnutzer-tauglich: Template-Defaults mitliefern (2–3 sinnvolle Beispiele), Params haben erklärte Defaults — Edit ohne Vorwissen möglich.

## Checkliste

- [x] img2img-Pfad über die GenerativeEngine (Flux-Komponenten aus Phase 2)
- [x] prompt_template-Migration + CRUD + `promptTemplates`-Slice
- [x] Flux-Tool-Panel (Prompt, Template-Picker, Params, Seed-Lock)
- [x] Masken-Layer im Editor + Inpaint-Endpoint
- [x] Bulk-Verdrahtung (ohne Inpaint)
- [x] Doc-Update: routes.md, docs/models.md (prompt_template)

## Report-Back
