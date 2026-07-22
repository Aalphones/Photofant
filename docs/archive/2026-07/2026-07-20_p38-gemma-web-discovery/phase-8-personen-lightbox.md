# Phase 8 — Personen-Karte + Lightbox-Wissen-Tab

**Komplexität:** standard (beide Zielorte existieren und werden erweitert, nicht neu gebaut).
**Voraussetzung:** Phase 5-7 (Übersicht, Detail, Wizards — alles, wohin diese Phase verlinkt).

Die letzte Phase verdrahtet Wissen dorthin, wo der Nutzer ohnehin ist: auf die Personen-Karte
und in den Bild-Betrachter. Beide Orte haben heute schon eine Wissens-Anbindung, die dünn ist.

## Design-Referenz
- `design/README.md` Abschnitte „5. Lightbox-Tab „Wissen"" und „6. Personen-Karten-Integration".
- `design/styles.css` Zeile 660-664 (`.person-know-chip`, `.person-know-nudge`).

## Kontext (lesen vor dem Start)
- `frontend/src/app/features/personen/person-card/person-card.html` Zeile 80-89 — der
  **bestehende** Verknüpfungs-Chip (`person-card__entity-chip`) mit Titel der Entity. Er wird zum
  Wissens-Chip mit Prozentwert umgebaut, nicht danebengesetzt.
- `frontend/src/app/features/personen/person-card/person-card.ts` Zeile 262-266 —
  `onEntityChipClick` navigiert heute nach `/wissen?entity=…`. Ziel wird ab jetzt das
  Detail-Modal aus Phase 6.
- `frontend/src/app/features/galerie/lightbox/lightbox.html` Zeile 353-391 — der **bestehende**
  Wissen-Tab mit `pf-lore-panel` und den Empfehlungen.
- `frontend/src/app/features/galerie/lightbox/lore-panel/lore-panel.{ts,html,scss}` — die
  Sektionen, die dort schon gerendert werden; Zeile 150-234 das Muster „KI-Ergänzung anfordern,
  auf Job warten, Ergebnis zeigen".
- `frontend/src/app/features/galerie/lightbox/related-rail/` — die vorhandene Kartenliste für
  „Ähnliche Bilder"; für das Thumbnail-Raster des Designs ist sie **nicht** das richtige Mittel
  (andere Form), aber ihr Klick-Weg (`cardClick` → Bild wechseln) ist die Vorlage.
- `frontend/src/app/models/knowledge.model.ts` — `LoreDto`, `EntityDto.completeness`.

## Aufgabe 1 — Personen-Karte: Chip und Nudge
`person-card.html`, direkt unter dem Avatar-Bereich (dort, wo heute der Entity-Chip sitzt):

**Mit verknüpfter Entity** — gefüllter Chip (`design/styles.css` Zeile 660-662):
```
display: inline-flex; align-items: center; gap: 5px; margin-top: 6px; height: 22px;
padding: 0 8px; border-radius: 6px; font-size: 10.5px; font-weight: 600;
background: var(--accent-weak); color: var(--accent); border: 1px solid var(--accent-line);
```
Inhalt: `sparkle`-Icon + „{N} %". Beim Überfahren `oklch(0.685 0.135 248 / .25)`.
`title`: „Wissen zu {Name} — {N} % ausgefüllt".

**Ohne verknüpfte Entity** — Nudge (Zeile 663-664): gleiche Maße, aber
`background: transparent; color: var(--text-3); border: 1px dashed var(--line-2);`
Text „Wissen anlegen?", beim Überfahren `--text-2`.

Beide öffnen das Detail-Modal aus Phase 6 für diese Person. Dafür braucht `personen.ts` ein
Signal `detailPersonId` und rendert `pf-knowledge-detail-dialog` — die Personen-Ansicht bekommt
damit denselben Zugang wie die Wissen-Ansicht, statt den Nutzer wegzunavigieren.

Der Prozentwert kommt aus `person.linked_entity.completeness` (Phase 2). Ist das Feld `0`, weil
für den Typ keine Merkmale definiert sind, zeigt der Chip statt „0 %" den Entity-Titel wie
bisher — eine Null-Prozent-Anzeige wäre schlicht gelogen.

## Aufgabe 2 — Lightbox-Tab „Wissen" auffüllen
`lightbox.html`, im bestehenden `@if (activeTab() === 'knowledge')`-Block. Das `pf-lore-panel`
bleibt; ergänzt wird **innerhalb des Panels** (`lore-panel.html`):

1. **Vollständigkeits-Zeile** oben in der Entity-Sektion: `pf-completeness-ring` mit
   `[size]="40"` neben Name und „{N} % ausgefüllt".
2. **Sektions-Aktion „Vollständiges Profil"** — kleiner Textknopf rechts in der Sektions-
   Kopfzeile, führt in die Wissen-Ansicht mit geöffnetem Detail für diese Person
   (`/wissen` mit Query-Parameter `person`; `wissen.ts` liest ihn beim Start und öffnet das
   Modal). Bestehende `psec-title`-Struktur der Lightbox als Vorlage.
3. **Ohne zugeordnete Person:** Hinweistext „Auf diesem Bild ist noch keine Person zugeordnet —
   das machst du im Tab „Gesichter"." Der bestehende Leer-Zustand des Panels wird darauf
   umformuliert, kein zweiter danebengestellt.
4. **Ohne Wissen zur Person:** Knopf „Interview starten" → öffnet den Wizard aus Phase 7 mit
   vorbelegter Person.

## Aufgabe 3 — „Ähnliche Bilder" im Wissen-Tab
Unterhalb der Wissens-Sektionen ein 3-spaltiges Thumbnail-Raster **aller anderen Fotos derselben
Person** (Design: „Ähnliche Bilder"). Datenquelle: `LoreDto.related_media` gefiltert auf
`kind === 'asset'` und ohne das gerade offene Bild.

Raster wie in Phase 6 (`repeat(3, 1fr)`, `gap: 6px`, quadratisch, `border-radius: 8px`). Klick
wechselt das Bild in der Lightbox (Weg wie `related-rail`'s `cardClick`).

⚠️ Der bestehende **Empfehlungs-Block** im selben Tab (`showRecommendations()`, P26/P36) bleibt
unangetastet und steht **darunter**. Er beantwortet eine andere Frage („was passt sonst noch")
als das neue Raster („wo ist diese Person noch"). Die beiden bekommen deshalb klar
unterschiedliche Überschriften: **„Weitere Bilder von {Name}"** für das neue Raster,
„Empfehlungen" bleibt wie es ist. Zwei Bilderreihen mit ähnlicher Überschrift wären der sichere
Weg in die Verwirrung.

## Aufgabe 4 — „Recherchieren" im Lore-Panel
Im Knopf-Container `.lore-actions` (`lore-panel.html` Zeile 112-145), nach „Ergänzen (KI)":
```html
@if (canRequestDiscoveryFor(lore)) {
  <button class="lore-correct" type="button" (click)="openWebSearch(ent.id)"
          title="Sucht öffentlich verfügbare Angaben — du entscheidest danach, was übernommen wird">
    <pf-icon name="search" [size]="11" />
    Recherchieren
  </button>
}
```
`canRequestDiscoveryFor` ist wahr, wenn (a) eine Entity vorhanden ist, (b) die Autonomie-
Einstellung `discovery === 'auto'` ist und (c) die Domäne der Entity **nicht** privat ist. Für
(c) einmalig im Konstruktor `listDomains()` laden und die privaten Namen in einem
`signal<Set<string>>` halten (`lore.entity.domain` ist der Domänen-**Name**, nicht das Objekt).

Der Knopf startet hier **keinen** eigenen Ablauf — er öffnet den Web-Suche-Wizard aus Phase 7
mit vorbelegter Entity. Ein zweiter, abweichender Recherche-Weg im Panel wäre genau die Art von
Doppelpflege, die später auseinanderläuft.

**Owner-Hinweis** im Bio-Block, wenn der Text zuletzt per Web-Recherche kam (`ent.owner === 'web'`):
eine Zeile „🌐 Aus einer Web-Recherche übernommen." in `.lore-web-hint` — kleine Schrift,
gedämpfte Farbe, Werte aus den bestehenden `.lore-suggestion__status`-Regeln übernehmen, keine
neue Farbpalette erfinden.

## Aufgabe 5 — P27-README amendieren (zwei Zeilen, nicht neu schreiben)
`docs/planning/2026-07-01_p27-gemma-integration/README.md`:
- Bei der AK-Zeile „Offline-Garantie gewahrt: …" ergänzen: „*(Ausnahme ab P38: die
  Web-Recherche macht bei explizitem Klick echte Netzwerkzugriffe — ADR-031. Alle anderen
  P27-Funktionen bleiben strikt offline. Die Regel „Gemma schreibt nie ohne Bestätigung" gilt
  weiterhin ausnahmslos.)*"
- Beim Scope-„Draußen"-Punkt „Discovery → Phase 8" ergänzen: „*(Web-Recherche für öffentliche
  Entitäten ist vorgezogen als P38 — vollautomatische Hintergrund-Discovery ohne User-Trigger
  bleibt weiterhin Phase 8.)*"

## AK dieser Phase
- [x] Personen-Karte zeigt bei verknüpfter Entity den gefüllten Chip mit Prozentwert, sonst den
      gestrichelten Nudge „Wissen anlegen?"; beide öffnen das Detail-Modal **auf derselben Seite**,
      ohne Navigation.
- [x] Ist für den Entity-Typ kein Merkmal definiert, zeigt der Chip den Titel statt „0 %".
- [x] Lightbox-Wissen-Tab zeigt Ring + Prozentwert und den Sprung „Vollständiges Profil", der die
      Wissen-Ansicht mit geöffnetem Detail für diese Person aufruft.
- [x] Ohne zugeordnete Person zeigt der Tab genau **einen** Hinweistext, der auf den
      Gesichter-Tab verweist.
- [x] „Weitere Bilder von {Name}" rendert als 3-spaltiges Raster und wechselt bei Klick das Bild;
      der Empfehlungs-Block darunter funktioniert unverändert.
- [x] „Recherchieren" erscheint nur bei `discovery === 'auto'` und nur auf nicht-privaten
      Entitäten; er öffnet den Wizard aus Phase 7, keinen eigenen Ablauf.
- [x] Owner-Hinweis „🌐 Aus einer Web-Recherche übernommen." erscheint an einer Entity, deren
      Beschreibung zuletzt so entstanden ist.
- [x] P27-README trägt die ergänzte Zeile (nur eine von zwei geplanten war noch offen — siehe
      Report-Back).
- [x] `npx tsc --noEmit` grün, Produktions-Build läuft durch (gleiche vorbestehende
      Bundle-Budget-Warnung wie Phase 5-7, keine Regression).

## Doc-Updates
- [x] `docs/code-map.md` — Lightbox- und Personen-Zeile um die Wissens-Anbindung ergänzt.
- [x] `docs/glossary.md` geprüft — „Owner"/„Vollständigkeit" stehen bereits seit Phase 2, nichts
      nachzutragen.

## Report-Back

**Deep-Link-Entscheidung (FINDINGS-Frage geklärt):** Zwei unterschiedliche Wege, je nach Ausgangsort —

- **Personen-Seite:** volle Parität mit der Wissen-Ansicht, alles **lokal auf derselben Seite**
  gemountet (Detail-Modal, Interview-Wizard, Web-Suche-Wizard, „Web-Recherche starten", Lightbox
  für „Verknüpfte Fotos"). Kein Wegnavigieren an irgendeiner Stelle.
- **Lightbox-Lore-Panel:** „Interview starten", „Recherchieren" und „Vollständiges Profil"
  schließen die Lightbox und navigieren nach `/wissen` mit Query-Parametern
  (`?person=<id>`/`?entity=<id>`, optional `&open=interview`/`&open=discovery`) — `wissen.ts`
  liest das beim Start und öffnet Detail-Modal bzw. den passenden Wizard direkt vorbelegt.
  Grund: Lightbox ist an vier Stellen eingebettet (Galerie/Favoriten/Alben/Wissen), ein zweites
  Set lokal gemounteter Wizards dort hätte echte Doppelpflege bedeutet (dieselbe Sorge, die die
  Phase-4-Aufgabe für „Recherchieren" selbst schon benennt). Die alte Inline-`entity-wizard-
  dialog`-Lösung für „Wissen anlegen" (P25, wegen eines inzwischen behobenen Routing-Guard-Bugs
  eingebaut) ist damit ersatzlos entfernt — `routes.ts` hat den Guard seit einer früheren Phase
  auf jede Kindroute einzeln verschoben, `openLinkedEntity()` navigiert schon länger denselben
  Weg ohne Probleme.

**Gefundene, vorbestehende Lücke (Phase 6, nicht in dieser Phase gefixt):** Die von
„Web-Recherche starten" im leeren Detail-Zustand angelegte Entity wird nicht automatisch mit der
Person verknüpft (`entity-wizard-dialog` kennt kein `media_links`-Prefill) — bestätigt beim
1:1-Nachbau der `wissen.ts`-Logik für die Personen-Seite. Gleiches Verhalten wie im Original,
also keine Regression, aber eine reale Lücke: der Chip bleibt nach diesem Weg auf „Wissen
anlegen?" hängen, bis manuell verknüpft wird. Nicht mitgefixt (Phase-6-Scope), aber hier
protokolliert.

**P27-README:** nur die „Draußen: Discovery → Phase 8"-Zeile bekam die neue Amendment-Notiz. Die
zweite geplante Ergänzung (AK-Zeile „Offline-Garantie gewahrt") trägt bereits seit Phase 1
(2026-07-21) eine inhaltsgleiche Amendment-Notiz zu ADR-031 — eine zweite, fast wortgleiche Notiz
direkt darunter wäre reine Dopplung gewesen, deshalb übersprungen.

**Kleinere Abweichungen:**
- Der Nudge „Wissen anlegen?" erscheint nicht auf „Unbekannt"-Karten (`is_unknown`) — eigene
  Ergänzung, im Plan nicht spezifiziert, aber ein Nudge auf einem unidentifizierten
  Gesichts-Cluster wäre sinnlos gewesen.
- Ring/Prozentwert/„Vollständiges Profil"/„Weitere Bilder" im Lore-Panel greifen nur, wenn
  `personId()` gesetzt ist (Face-Modus mit genau einer aufgelösten Person) — der
  Backend-Kontrakt verlangt exakt eines von `asset_id`/`person_id` (nie beide), und `LoreDto`
  trägt keine Person-Zuordnung pro Block. Im normalen Asset-Modus mit mehreren Personen bleibt
  die Sektion wie vor Phase 8 (Entity-Titel + Bio + Aktionen, ohne die neuen Zusätze) —
  entspricht dem Design-Text „erkannte **Haupt**person" (Singular).

**Konfidenz:** keine wacklige Stelle, für die ich einen offenen Check sehe — `tsc`/Build sind
grün, die Deep-Link-Logik ist reaktiv gegen die Loading-Flags gegated (kein Race mit leerem
Namen). Der Live-Smoke-Punkt unten ist trotzdem echt (kein Ersatz für tatsächliches Klicken).
