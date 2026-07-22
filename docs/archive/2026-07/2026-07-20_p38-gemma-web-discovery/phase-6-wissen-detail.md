# Phase 6 — Wissen-Detail (Modal) nach Design

**Komplexität:** standard (viel Struktur, keine offenen Entscheidungen; Daten liegen alle vor).
**Voraussetzung:** Phase 5 (die Übersicht, aus der das Modal geöffnet wird) und Phase 2
(Merkmale mit Owner).

Das ist der Bildschirm, auf dem das Merkmals-Modell aus Phase 2 zum ersten Mal sichtbar wird:
Werte mit Herkunfts-Pille, ein großer Ring, verknüpfte Fotos daneben.

## Design-Referenz
- `design/README.md` Abschnitt „2. Wissen-Detail (Modal)".
- `design/styles.css` Zeile 1417-1459 (`.kw-scrim` … `.kw-photo-cell`).
- Tokens identisch zur App (siehe Phase 5) — Werte wörtlich übernehmen.

## Kontext (lesen vor dem Start)
- `frontend/src/app/features/wissen/entity-wizard-dialog/entity-wizard-dialog.{ts,html,scss}` —
  das **Modal-Vorbild des Projekts**: Scrim, Escape-Behandlung, Fokus, Schließen-Knopf. Struktur
  von dort übernehmen, Aussehen aus dem Design.
- `frontend/src/app/models/knowledge.model.ts` — `EntityDto` (mit `attributes`/`completeness` aus
  Phase 2), `LoreDto`, `ResolvedRelationshipDto`, `MediaRefDto`, `DomainDto`, `EntityType.fields`.
- `frontend/src/app/services/knowledge.service.ts` — `getLore({ personId })` liefert in **einem**
  Aufruf Entity, aufgelöste Beziehungen, verknüpfte Medien und Quellen. Das ist die Datenquelle
  dieses Modals; keine Einzelabfragen zusammenstückeln.
- `frontend/src/app/features/galerie/lightbox/lore-panel/lore-panel.{ts,html}` — dort werden
  `LoreDto`-Sektionen bereits gerendert (Beziehungen, Quellen, Medien). Benennung und
  Aufbereitung von dort übernehmen, damit zwei Oberflächen dieselben Daten nicht unterschiedlich
  nennen.
- `frontend/src/app/services/person.service.ts` — `linkEntity(personId, entityId)` und der
  Unlink-Weg (im Personen-Feature bereits verdrahtet, `person-card.ts` Zeile 228-230).
- `frontend/src/app/ui/completeness-ring/` (Phase 5).

## Aufgabe 1 — Komponente + Hülle
Neu: `features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.{ts,html,scss}`,
Selektor `pf-knowledge-detail-dialog`.

Eingänge: `personId = input<number | null>(null)`, `entityId = input<string | null>(null)`
(eins von beidem ist gesetzt — Person aus dem Grid, Entity aus der Notizen-Sektion).
Ausgänge: `close`, `openInterview`, `openWebSearch`, `openLightbox` (Asset-ID),
`linkRequested`, `unlinkRequested`.

Hülle: Scrim `position: fixed; inset: 0; z-index: 120;` mit
`background: oklch(0.08 0.005 256 / .7)` und `backdrop-filter: blur(6px)`; Modal
`width: min(880px, 94vw); max-height: 88vh; overflow-y: auto;` auf `--bg-2`, 1px `--line-2`,
`--radius-l`, `--shadow-pop`, Innenabstand `26px 28px 28px`. Schließen über Scrim-Klick,
X-Knopf (oben rechts, 16px Abstand) und Escape — alle drei, nicht zwei von drei.

## Aufgabe 2 — Kopf
`display: flex; align-items: center; gap: 16px; padding-right: 30px;`
- `pf-completeness-ring` mit `[size]="72"`, darin das Portrait.
- Name 19px/700 (`letter-spacing: -.01em`), darunter Sub-Zeile 11.5px `--text-3`:
  `„{N} % vollständig · {Domäne} · aktualisiert am {Datum}"`.
- Rechts (`margin-left: auto`) drei Knöpfe im `.kw-btn`-Stil: **„Interview"**,
  **„Web-Suche"**, **„Verknüpfung lösen"**.
  - „Web-Suche" nur, wenn die Autonomie auf `auto` steht **und** die Domäne nicht privat ist —
    dieselbe Bedingung wie in Phase 5, hier zusätzlich der Domänen-Check.
  - „Verknüpfung lösen" nur, wenn tatsächlich eine Person-Verknüpfung besteht. Der Knopf trägt
    ein `title`: „Trennt Person und Notiz. Die Notiz bleibt erhalten und taucht danach unter
    „Nicht verknüpfte Notizen" auf." — ohne diesen Satz klingt „lösen" nach löschen.

## Aufgabe 3 — Vorschlags-Banner
Wenn für diese Entity ein KI-Vorschlag vorliegt (der bestehende Update-Vorschlag aus P27,
`KnowledgeUpdateProposal`), Banner nach `design/styles.css` Zeile 1428-1431:
`--accent-weak`-Fläche, 1px `--accent-line`, `--radius`, Innenabstand `12px 14px`, Text 12.5px,
rechts zwei kleine Knöpfe „Übernehmen" / „Verwerfen". Nach dem Übernehmen wechselt der Banner
auf den `done`-Zustand (grüne Fläche `oklch(0.55 0.15 150 / .12)`), statt zu verschwinden —
so sieht man, dass etwas passiert ist.

Kein neuer Backend-Weg: „Übernehmen" ruft das bestehende `acceptUpdateSuggestion`.

## Aufgabe 4 — Zwei-Spalten-Körper
`display: grid; grid-template-columns: 1fr 240px; gap: 20px; margin-top: 18px;`
Unter 860px Breite auf eine Spalte (`grid-template-columns: 1fr`).

### Linke Spalte, Sektion „Profil"
Fließtext-Bio aus `entity.body`, 13px, `line-height: 1.6`, `--text-2`. Leer → ein Satz in
`--text-3`: „Noch keine Beschreibung — das Interview schreibt sie."

### Linke Spalte, Sektion „Merkmale"
**Eine Zeile je definiertem Merkmal des Typs** (`DomainDto.entity_types[].fields`), nicht nur je
gesetztem — fehlende Merkmale sind der Punkt der Anzeige. Zeile:
`display: flex; align-items: center; gap: 10px; font-size: 12.5px;`
- Label: feste Breite 110px, `--text-3`.
- Wert: `flex: 1`, `--text`; nicht gesetzt → „—" in `--text-3`.
- Owner-Pille rechts, 10px/700, Großbuchstaben, `letter-spacing: .03em`, `padding: 2px 7px`,
  `border-radius: 5px`:

| Owner | Beschriftung | Stil |
|---|---|---|
| `user`, `manual` | „Manuell" | `--accent-weak` / `--accent` |
| `web` | „Web" | `--semantic-weak` / `--semantic` |
| `inferred` | „KI-Schätzung" | `--surface-2` / `--warn` |
| nicht gesetzt | „fehlt" | transparent, `--text-3`, 1px gestrichelt `--line-2` |

Die Beschriftungen sind bewusst deutsch und laienverständlich — nicht `user`/`inferred`
durchreichen, das versteht außerhalb des Codes niemand.

### Linke Spalte, Sektion „Beziehungen"
Chips aus `LoreDto.relationships`: `padding: 6px 10px 6px 6px`, `border-radius: 10px`,
`--surface` + 1px `--line`; darin Avatar (falls das Ziel eine Person mit Portrait ist), Name
12px/600 und Typ 10.5px `--text-3`. Klick springt auf die Ziel-Entity (Modal lädt neu).

### Linke Spalte, Sektion „Quellen"
Je Quelle eine Zeile mit Icon + Text, 12px `--text-2`, Icon in `--text-3`. Icon nach Herkunft:
Interview → `sparkle`, Web → `globe`, manuell → `edit`. URLs als Link mit
`target="_blank" rel="noopener noreferrer"`.

### Rechte Spalte — „Verknüpfte Fotos"
`display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;` (unter 860px: 4 Spalten).
Zellen quadratisch (`aspect-ratio: 1`), `border-radius: 8px`, Innen-Rand über
`box-shadow: inset 0 0 0 1px rgba(255,255,255,.08)`, beim Überfahren 2px `--accent-line`.
Quelle: `LoreDto.related_media` gefiltert auf `kind === 'asset'`. Klick gibt `openLightbox`
mit der Asset-ID nach oben.

**Die Box „Album-Vorschlag" aus dem Design wird nicht gebaut** — siehe README, „Aus dem Design
bewusst nicht übernommen". Nicht als leerer Rahmen anlegen.

## Aufgabe 5 — Leerer Zustand
Kein Wissen zu dieser Person: schmales Modal (`width: min(420px, 92vw)`), mittig, Innenabstand
`40px 28px` — Avatar, Hinweistext (12.5px, `--text-3`, `line-height: 1.55`, `max-width: 300px`):
„Zu dieser Person ist noch nichts gespeichert." Darunter „Interview starten" und — nur wenn es
unverknüpfte Notizen gibt — „Bestehende Notiz verknüpfen".

## AK dieser Phase
- [x] Modal öffnet aus dem Personen-Grid und aus der Notizen-Sektion, schließt über Scrim,
      X und Escape.
- [x] Kopf zeigt 72px-Ring, Name 19px/700 und die Sub-Zeile mit Prozent, Domäne und Datum.
      **Abweichung (User-Entscheidung vor Phase-Start):** Datum entfällt — `EntityDto` trägt
      kein `updated_at` (FINDINGS.md), ein Backend-Zusatz hätte den Scope dieser reinen
      Frontend-Phase gesprengt. Sub-Zeile zeigt „{N} % vollständig · {Domäne}", konsistent mit
      Phase 5s „Nicht verknüpfte Notizen".
- [x] Merkmals-Liste zeigt **alle** für den Typ definierten Merkmale; fehlende mit „—" und
      gestrichelter „fehlt"-Pille.
- [x] Owner-Pillen tragen die deutschen Beschriftungen und die vier Farbvarianten aus der
      Tabelle oben.
- [x] Zwei-Spalten-Layout (1fr / 240px) klappt unter 860px auf eine Spalte um.
- [x] Klick auf ein verknüpftes Foto öffnet die Lightbox mit genau diesem Bild
      (`galleryActions.openAssetLightbox` — lädt das Asset auch nach, falls es in der
      Galerie-Store gerade nicht geladen ist).
- [x] „Verknüpfung lösen" trennt die Zuordnung; die Notiz erscheint danach in der Übersicht
      unter „Nicht verknüpfte Notizen" — nichts ist gelöscht.
- [x] Leerer Zustand zeigt den schmalen Modal-Zuschnitt mit den beiden Knöpfen.
- [x] Keine „Album-Vorschlag"-Box vorhanden.

## Doc-Updates
- [x] `docs/code-map.md` — `features/wissen/knowledge-detail-dialog/` ergänzt.

## Report-Back

**Umgesetzt:** `features/wissen/knowledge-detail-dialog/` (neu, `pf-knowledge-detail-dialog`),
verdrahtet in `wissen.ts`/`.html` (zwei neue Signale `detailEntityId`/`linkingPersonForEntity`,
`detailRefreshKey`, `<pf-lightbox />` eingebettet, zweite `link-entity-dialog`-Instanz im Modus
`entity` für „Bestehende Notiz verknüpfen"). `KnowledgeService.getEntityLore()` neu (Gegenstück
zu `getLore({personId})` für die unverknüpfte Notiz, nutzt die bereits vorhandene Backend-Route
`GET /entities/{id}/lore`).

**Zwei Entscheidungen vorab mit dem User geklärt (beide dokumentiert, s.o. bzw. Findings):**
1. Datum in der Kopfzeile weggelassen statt Backend-Zusatz.
2. KI-Ergänzungs-Banner (Aufgabe 3) feuert **nicht** automatisch beim Öffnen — ein Gemma-Lauf
   startet erst auf expliziten Klick auf eine schmale „Gemma nach einer Ergänzung fragen?"-Zeile
   (im Design nicht als eigenes Element vorgesehen, aber notwendig, um konsistent mit dem
   Opt-in-Prinzip des gesamten Plans zu bleiben — sonst würde jedes Öffnen einer nicht-user-
   owned Entity einen echten LLM-Lauf auslösen).

**Weitere Abweichungen vom Pixel-Vorbild (Datenmodell trägt die Information nicht):**
- **Quellen-Icons:** `entity.sources` enthält laut Backend-Kontrakt nur URLs (nur die
  Web-Recherche schreibt strukturierte Einträge) — es gibt kein Herkunfts-Feld. Die
  Drei-Icon-Regel (Interview/Web/manuell) ist daher heuristisch: URL → Web-Icon, Text mit
  „Interview" → Interview-Icon, sonst → Manuell-Icon (`pencil` statt `edit` — dieser Icon-Name
  existiert im Projekt nicht, `pencil` ist das Äquivalent).
- **Beziehungs-Chips ohne Avatar:** das Design zeigt ein Portrait, „falls das Ziel eine Person
  mit Portrait ist" — `ResolvedRelationshipDto.target` (`EntityRefDto`) trägt aber keine
  Person-/Portrait-Referenz, nur `id`/`title`/`type`/`completeness`. Chips zeigen deshalb
  durchgehend ein generisches Personen-Icon statt eines echten Avatars.

**Kleiner Nebenfund behoben:** `AttributeDto` und `EntityFieldDefDto` waren in `models/index.ts`
seit Phase 2 im Modell definiert, aber nicht aus dem Barrel exportiert — ergänzt (dieser Import
war der erste externe Konsument).

**Nicht in der Backend-Route enthalten, kein Blocker:** Wenn eine Person `linkEntity`/
`unlinkEntity` betrifft, ruft `wissen.ts` weiterhin volle Store-Reloads (`loadEntities`/
`loadPersons`/`loadTasks`) statt gezielter Patches — gleiches Muster wie Phase 5s
`onLinkNoteToPerson`, hier nur auf die neue Gegenrichtung übertragen.

**Konfidenz:** kein Live-Smoke in dieser Session (privates Profil) — `npx tsc --noEmit` und
`ng build` sind grün, keine neue Bundle-Regression. Wackelstellen für den User-Smoke: die drei
Escape/Scrim/X-Schließwege, die Zwei-Spalten-Umbruchgrenze bei 860px, und ob
„Verknüpfung lösen"/„Bestehende Notiz verknüpfen" tatsächlich beide Richtungen sauber
durchspielen (Notiz taucht danach wirklich unter „Nicht verknüpfte Notizen" auf bzw.
verschwindet von dort).
