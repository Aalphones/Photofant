# Design-Angleichung — fertige Views gegen Mockup & Konzept

> Status: geparkt · Quelle: [docs/design/README.md](../../design/README.md) (Mockup, Pixel-Treue) + [Konzept](../../Konzept-Photofant.md) · **Setzt an NACH `2026-06-18_einstellungen-fehlende-sektionen`** (alle Einstellungs-Sektionen müssen existieren, bevor die Shell sie umzieht)

Behebt die strukturellen Abweichungen zwischen Mockup (`docs/design/`) und der gebauten UI. Hintergrund: Einzelne Views sind als Abfallprodukt fremder Pläne gewachsen, ohne dass je ein Plan die *Gesamt-Hülle* oder die *Design-Deckung* besaß — Folge sind zwei bestätigte Fehlertypen (Design da, missachtet → Einstellungen; Design fehlt, freihändig erfunden → Tags) und vermutlich weitere kleinere. Dieser Plan inventarisiert zuerst vollständig (Phase 1) und repariert dann gezielt.

## Overview

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [Reconciliation-Sweep (Inventar)](phase-1-reconciliation-sweep.md) | standard | complete |
| 2 | [Einstellungen-Shell + Primitive](phase-2-einstellungen-shell.md) | heikel | complete |
| 3 | [Tags-Seite klären & angleichen](phase-3-tags-seite.md) | heikel | complete |
| 4 | [Übrige bestätigte Abweichungen](phase-4-uebrige-abweichungen.md) | standard | complete |

**🟡 Phase 4 ist absichtlich erst nach Phase 1 voll bestimmt.** Phase 1 liefert die verbindliche Abweichungsliste; ihre GROSS/MITTEL-Punkte für die *übrigen* Views (Galerie, Lightbox, Modelle, Alben, Personen, Trainingssets, Wartung, Shell) werden als FINDINGS getaggt und in Phase 4 abgearbeitet. Bis Phase 1 läuft, ist Phase 4 ein Rahmen, kein Inhalt.

**🟡 Sequenz-Trade-off (vom User so entschieden):** Weil dieser Plan *nach* `einstellungen-fehlende-sektionen` ansetzt, baut jener Plan vier neue Sektionen zunächst auf die *flache* Hülle — Phase 2 zieht sie dann mit um. Minimaler Doppelaufwand bewusst in Kauf genommen, dafür bleibt der laufende Plan unangetastet. (Alternative wäre eine Shell-Phase-0 *innerhalb* `einstellungen-fehlende-sektionen` gewesen.)

## Kontrakt (Backend ↔ Frontend)

Überwiegend **Frontend**. Die bestehenden Endpoints genügen:
- Einstellungen: `GET/PATCH /api/config` (settings.json), `GET /api/info` (aus `einstellungen-fehlende-sektionen`)
- Tags: `GET /api/tags`, `PATCH /api/tags/{id}`, `POST /api/tags/merge`, `POST /api/tags/bulk` (aus P6)

Deckt Phase 1 einen echten Backend-Bedarf auf (Kandidat: Speichernutzungs-Werte für den Bibliothek-/Nav-Speicherbalken aus dem Mockup), wird er als **Mini-Kontrakt in der betreffenden Phasen-Datei** nachgetragen — nicht hier vorab erfunden.

## Architektur-Entscheidungen (ADRs)

- **ADR-004** — Einstellungen-Shell: Master-Detail mit Sektions-Nav + wiederverwendbare Setting-Primitive (Phase 2).
- **ADR-005** — Schicksal der Tags-Seite: eigenes Design nachziehen vs. re-home vs. nur angleichen (Phase 3). 🔴 Entscheidung fällt zu Beginn von Phase 3 — Optionen + Empfehlung dort.

(Nächste freie Nummer war 004; 001 auf Platte, 002/003 in geparkten Plänen reserviert.)

## Finale Akzeptanzkriterien

1. **Inventar**: `docs/design-reconciliation.md` existiert und klassifiziert *jede* gebaute View nach Design-Status (vorhanden / nur Nav-Slot / fehlt), Abweichungstyp und Schweregrad, mit `datei:zeile`-Belegen.
2. **Einstellungen**: Layout entspricht dem Mockup (`st-page`-Master-Detail, linke Sektions-Nav, eine aktive Sektion, je `<h2>` + Untertitel), gebaut aus wiederverwendbaren Primitiven; **alle** bestehenden Funktionen (Backup, Modell-Ordner, Caption-Presets, Darstellung-Toggles + die in `einstellungen-fehlende-sektionen` ergänzten Sektionen) bleiben funktionsfähig.
3. **Tags**: Die Seite hat ein **verbindliches Design** (Mockup-Eintrag in `docs/design/` *oder* dokumentierte Re-home-Entscheidung); die Implementierung entspricht ihm und nutzt die geteilten Primitive.
4. **Übrige**: Alle in Phase 1 als GROSS/MITTEL bestätigten Abweichungen der restlichen Views sind behoben **oder** mit Begründung in einen Backlog-Plan verschoben.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] `docs/design-reconciliation.md` öffnen → jede gebaute View ist klassifiziert, kein „TBD".
- [ ] Einstellungen öffnen → **linke Sektions-Nav** sichtbar, Klick wechselt die Sektion (kein endloser Scroll mehr); jede Sektion hat großen Titel + erklärenden Untertitel wie im Mockup.
- [ ] Reihum testen: Backup erstellen, Modell-Ordner ändern, Caption-Preset anlegen, Darstellung-Toggle umlegen → alles funktioniert wie vorher.
- [ ] `/tags` öffnen → Layout entspricht dem (neuen/dokumentierten) Design; Umbenennen + Merge + Bulk-Taggen funktionieren.
- [ ] Stichprobe je übrige View gegen `design-reconciliation.md` → die dort als behoben markierten Punkte sind sichtbar gefixt.

## Summary

Alle 4 Phasen abgeschlossen (2026-06-19). Inventar vollständig in `docs/design-reconciliation.md`. Einstellungen-Shell (P2), Tags-Re-home (P3) und übrige Abweichungen (P4) behoben. 3 GROSS/MITTEL-Punkte sauber nach P7 verschoben (Person-Facette, Framing-Facette, Person-Avatar).

## Files touched

- `docs/design-reconciliation.md` — Inventar aller Views
- `frontend/src/app/features/einstellungen/` — Phase 2 Shell + Primitive
- `frontend/src/app/features/galerie/sub-toolbar/sub-toolbar.ts/html/scss` — Auswählen-Button + Chip-Key
- `frontend/src/app/features/galerie/galerie.html/scss` — sel-bar entfernt
- `frontend/src/app/shell/nav-rail/nav-rail.ts` — Favoriten + Review-Queue + Tags entfernt
- `frontend/src/app/shell/shell.html/ts` — Mobile Nav + Route-Titel
- `frontend/src/app/app.routes.ts` — /favoriten + /review Routen
- `frontend/src/app/features/favoriten/favoriten.ts` — neu
- `frontend/src/app/features/review/review.ts` — neu

## Commits

Werden im abschließenden Commit erfasst.

## Deviations from plan

- Mobile Nav "Mehr": öffnet Nav-Rail statt Bottom-Sheet-Overlay (Design-Intent erfüllt, simpler als voller Overlay-Bau)
- Review-Queue: Nav-Item + Stub-Route hinzugefügt, obwohl reconciliation "sauber-verschoben" sagt — da das Design den Eintrag unter Verwaltung zeigt, ist ein Stub die sauberste Lösung ohne leere Nav-Gaps

## Follow-ups

- **Prozess-Härtung (gehört NICHT in dieses Repo, sondern in die eigene Skill-Config):** `mode-planning` braucht ein **Design-Deckungs-Gate** (vor jeder UI-Phase: „existiert ein Mockup? wenn nein → 🔴 Design-Entscheidung, nicht still erfinden") und ein **Hüllen-Eigentümer-Prinzip** (querschnittliche Views wie Einstellungen brauchen einen Plan, der die IA besitzt, statt sektionsweise Anbau). `mode-implementing` braucht einen Verweis auf die Design-Referenz pro UI-Phase. → über `skill-evolution-log` / `/audit` einpflegen, separat von diesem Plan.
