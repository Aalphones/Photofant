# Phase 3 — Tags-Seite klären & angleichen

> Rating: heikel · Status: pending

Die Tags-Verwaltungs-Seite wurde nach Konzept §10 gebaut, hat aber **kein Mockup** — das Design reserviert nur einen Nav-Slot (`app.jsx:63 { id:"tags" }`), zeichnet den Screen aber nie. Folge: die Optik wurde freihändig erfunden. Diese Phase macht das Design verbindlich und gleicht die Implementierung an. Entscheidung → **ADR-005**.

## 🔴 Entscheidung zu Beginn der Phase (ADR-005)

Welches Schicksal bekommt die Tags-Seite?

- **(A) Design nachziehen** — einen sauberen Tags-View-Entwurf erstellen, der zum System passt (eigener Mockup-Eintrag in `docs/design/`), dann Impl daran ausrichten. *Empfohlen, wenn die Seite eigenständig bleiben soll — der Nav-Slot zeigt, dass das die ursprüngliche Absicht war.*
- **(B) Re-home** — Tag-Verwaltung (Umbenennen/Merge/Counts) in die Einstellungen (eigene Sektion) oder einen anderen bestehenden Screen falten, eigenständige `/tags`-Route entfernen. Passt zur Design-Logik, die Tag-*Bearbeitung* in Lightbox + Filter-Facette verortet.
- **(C) Adoptieren & nur angleichen** — Seite bleibt, bekommt aber einen **nachträglichen, verbindlichen README-Eintrag in `docs/design/`** (damit sie nicht „erfunden" bleibt) und wird auf die Phase-2-Primitive umgestellt. *Geringster Aufwand; legitimiert den Status quo.*

**Empfehlung: (C)** — der Nav-Slot belegt die Absicht, die Seite existiert und funktioniert, das Konzept fordert das Feature. Statt wegzuwerfen oder neu zu erfinden: Design-Eintrag nachziehen + an die Systemsprache angleichen. (A) nur, wenn dir das aktuelle Layout grundsätzlich missfällt; (B) nur, wenn du die eigenständige Seite gar nicht willst.

## Kontext (vorher lesen)

- [README.md](README.md)
- [Konzept](../../Konzept-Photofant.md) §10 — Tag-Verwaltung (Counts, Umbenennen, Merge/alias_of, Bulk)
- `docs/design/README.md` + `docs/design/styles.css` — Design-Tokens & System-Sprache (Chips `.tg`, Listen, Bulk-Bar) als Referenz für den Look
- `frontend/src/app/features/tags/tags.ts` · `tags.html` · `tags.scss` — Ist-Zustand
- Phase-2-Primitive (falls (B)/(C) auf sie zugreift)

## Akzeptanzkriterien

- **ADR-005** angelegt: gewählte Option + Begründung.
- Es existiert ein **verbindliches Design** für die Tag-Verwaltung — als Mockup/README-Eintrag in `docs/design/` (A/C) oder als dokumentierte Re-home-Entscheidung (B).
- Die Implementierung **entspricht** diesem Design und nutzt die Systemsprache (Tokens, Chips, Listen-Primitive aus Phase 2).
- Funktionserhalt: Umbenennen, Merge (alias_of-Auflösung in Suche/Filter), Bulk-Taggen über die Bulk-Bar — alle weiterhin funktionsfähig.
- Bei (B): `/tags`-Route entfernt, Nav-Eintrag entfernt/umgeleitet, kein toter Link.

## Checkliste

- [ ] 🔴 ADR-005 entscheiden + schreiben
- [ ] Design verbindlich machen (Mockup/README-Eintrag *oder* Re-home-Doku)
- [ ] Implementierung angleichen (Layout/Primitive) bzw. re-homen
- [ ] Funktions-Smoke: Umbenennen / Merge / Bulk
- [ ] Doc-Update: `docs/routes.md` (bei Routen-Änderung), `docs/design/README.md` (View-Liste)

## Report-Back
