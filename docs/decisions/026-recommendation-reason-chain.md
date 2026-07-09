# ADR-026 — Empfehlungen ohne neuen Vektorstore: gewichtete Reason-Chain

**Status:** Angenommen — Phase 1 umgesetzt (P26 Phase 1: Backend-Job + Reason-Chain + API)
**Datum:** 2026-07-09
**Betrifft:** Plan `2026-07-01_p26-recommendation-engine`, nutzt Bestand aus ADR-001 (SigLIP2-Vektorindex) und P22 (Wissensgraph); Aktivierung folgt ADR-008 (Feature per Setting)

> **ADR-Nummer:** Der Plan reservierte „ADR-012" — die Nummer war zu dem Zeitpunkt schon
> vergeben (Galerie-Stapel). Wie bei P24 (011 war belegt) wird die nächste freie Nummer
> genommen: **026**.

---

## Kontext

Empfehlungen sollen zu einem Bild passende weitere Bilder zeigen — **mit nachvollziehbarer
Begründung** („warum empfohlen?"). Es gibt zwei vorhandene Signalquellen, kein neues Modell
soll dazukommen (Kontrakt: kein Modell-Download, keine Laufzeit-Netzwerkzugriffe):

- **Bild-Ähnlichkeit** aus dem SigLIP2-Vektorindex (`db/vector_index.py`), 0..1 Kosinus.
- **Wissensgraph** aus P22 (Personen ↔ Entities ↔ Beziehungen).

Die Frage: **wie** werden beide zu einer erklärbaren Empfehlung kombiniert, ohne einen
zweiten Retrieval-Store zu bauen und ohne die Domäne „Movies" hart zu verdrahten (die
Domänen-Typen sind konfigurierbar, Dok 020).

## Optionen

- **Rein CLIP-basiert (nächste Nachbarn im Bildraum):** verworfen — ignoriert den Graphen,
  „warum" wäre nur „sieht ähnlich aus", keine semantische Begründung.
- **Eigener Empfehlungs-Vektorstore (kombiniertes Embedding):** verworfen — neuer Store,
  neues Training/Modell, und die Begründung wäre wieder eine undurchsichtige Zahl.
- **Gewichtete Kombination vorhandener Signale mit expliziter Reason-Chain (gewählt).**

## Entscheidung

**Score = gewichtete Summe unabhängiger, benannter Signale:**

    score = w_person·[gleiche Person] + w_role·[gleiche Rolle]
          + w_film·[gleicher Film]    + w_clip·clip_similarity

- Die drei Graph-Signale sind **an der Datenstruktur** festgemacht, nicht an Typnamen —
  damit domänen-agnostisch:
  - **gleiche Person** — geteilte reale Person im Bild (aktive `asset_instance`; die
    `_unknown`-Sammelperson zählt nicht, sonst „teilt" jedes unzugeordnete Bild eine Person).
  - **gleiche Rolle** — geteilte **direkt** verknüpfte Entity (`knowledge_media_links`);
    im Movies-Beispiel die Figur.
  - **gleicher Film** — geteiltes **1-Hop**-Beziehungsziel dieser Rollen
    (`knowledge_relationships`); im Movies-Beispiel Film/Serie. Zwei Hops (z.B. Franchise
    über `part_of`) zählen bewusst nicht — sonst wird „verwandt" beliebig.
- Jedes beitragende Signal erzeugt ein **Reason-Chain-Glied** `{signal, detail, weight}` mit
  konkretem Wert (`{same_role, "Tony Stark", 0.25}`, `{clip, "0.94", 0.2}`). Eine
  Fehlgewichtung wird so **sichtbar** statt hinter einer Gesamtzahl versteckt (das ist das
  Kern-Risiko des Plans).

**Gewichte + Schwelle in den settings** (`recommendations.weights`, `.min_score`,
`.max_results`, `.enabled`) — an einem realen Bild-Set kalibrierbar, abschaltbar (ADR-008).
Default-Gewichte summieren zu 1.0, damit der Score in [0, 1] liegt und `min_score` (0.3)
direkt interpretierbar ist.

**Zwei Kandidatenquellen, ein Scorer:** CLIP-Nachbarn (mit Ähnlichkeitswert) **und**
graph-verbundene Assets (ohne) fließen in denselben Scorer. Ein Kandidat aus beiden Quellen
trägt beide Signalarten — genau der belegbare „CLIP **und** Graph"-Fall. Die CLIP-Schicht
wird nur **gelesen** (`vector_index.search`), nicht umgebaut (Chesterton).

**Kein synchrones Rechnen in der API:** `GET /api/recommendations` liest den Cache
(`recommendation_cache`); ein Fehltreffer plant den `RecommendationJob` und liefert leer +
Status `computing` (Kontrakt: die UI blockiert nie).

**Ein Job statt zwei:** Der `RecommendationJob` **ersetzt** die Cache-Zeilen der Quelle
idempotent und bedient damit „auf Abruf berechnen" und „nach Änderung neu berechnen". Ein
separater `RecommendationUpdateJob` (README-Kontrakt) wäre verhaltensgleich und damit nur
Rauschen. Auto-Trigger bei Graph-Änderungen sind spätere Integration.

**„Warum nicht?"** (`GET /api/recommendations/{source}/{target}/why-not`) rechnet ein
Einzelpaar **live** (kein Cache, kein Index-Scan) und listet anwesende **und** fehlende
Signale samt Schwelle — nur auf Anfrage (das ist potenziell teuer, deshalb nichts auf Vorrat).

## Konsequenzen

- Kein neuer Vektorstore, kein Modell-Download. Die Empfehlung ist eine erklärbare Summe
  vorhandener Signale.
- Die Reason-Chain ist die **geteilte Explainability-Payload** mit P25 (Korrektur-Log) und
  P26 Phase 3 („Warum?"-Popover) — ein Format für Herkunft/Begründung.
- Die Score-Qualität hängt an den Gewichten. Das ist bewusst ein **kalibrierbarer** Knopf
  (Smoke am realen Set, Nutzer-Aufgabe), kein hartkodierter Kompromiss — die Reason-Chain
  macht eine Fehlgewichtung auffindbar.
- Der Graph-Kontext wird **gebündelt** für viele Kandidaten aufgelöst (konstant wenige
  Queries), damit die Berechnung bei großer Bibliothek nicht in N+1 zerfällt.
