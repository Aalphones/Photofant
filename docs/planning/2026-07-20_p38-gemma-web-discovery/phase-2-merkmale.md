# Phase 2 — Merkmale + Vollständigkeit

**Komplexität:** heikel (Schema-Änderung an der Markdown-Wahrheit, neue Ownership-Ebene, ADR-032).
**Voraussetzung:** keine — läuft unabhängig von Phase 1, muss aber **vor** Phase 3 fertig sein
(die Web-Fakten schreiben in genau diese Merkmale).

Bis heute hat eine Wissenseinheit **einen** Owner für alles und einen Freitext-Body. Das Design
verlangt Felder mit eigenem Owner pro Feld und einen daraus berechneten Vollständigkeits-Wert.
Diese Phase baut genau das — und nichts darüber hinaus (keine UI, die kommt in Phase 5/6).

## Kontext (lesen vor dem Start)
- `backend/photofant/knowledge/schema.py` — `Owner` (Zeile 13-23), `owner_can_overwrite`
  (Zeile 40), `Entity` (Zeile 69-90). Hier kommt `Attribute` dazu.
- `backend/photofant/knowledge/parser.py` — **die ganze Datei, sie ist kurz.** `_FIELD_ORDER`
  (Zeile 17-29), `entity_to_metadata` (42), `metadata_to_entity` (65), `_as_media_links` (127)
  als exaktes Vorbild für den neuen `_as_attributes`. Wichtig: `media_links` ist bereits ein
  verschachteltes Mapping im Frontmatter — die Maschinerie (`python-frontmatter` + PyYAML,
  `sort_keys=False`) trägt verschachtelte Blöcke nachweislich schon.
- `backend/photofant/knowledge/domains.py` — `EntityType` (Zeile 21), `Domain` (29),
  `_parse_entity_types` (99). Hier kommen die Feld-Definitionen dazu.
- `backend/photofant/knowledge/validator.py` — `validate_metadata` (23), `_check_relationships`
  (87) als Vorbild für die neue Prüffunktion (gleiche Signatur, gleicher Fehlerlisten-Stil).
- `backend/photofant/knowledge/service.py` — `update_entity` (152), `_check_ownership` (352),
  `validate_patch` (168). Der Attribut-Schreibweg wird **nicht** in `update_entity` gequetscht,
  sondern bekommt eine eigene Methode (Aufgabe 5) — Begründung dort.
- `backend/photofant/api/knowledge.py` — `EntityDto` (57), `EntityTypeDto` (94), `DomainDto`
  (99), `EntityRefDto` (118). Alle vier werden erweitert.
- `backend/photofant/knowledge/domains/private.yaml` und `movies.yaml` — die zwei
  ausgelieferten Domänen, beide bekommen Feld-Definitionen (Aufgabe 6).
- `frontend/src/app/models/knowledge.model.ts` — `OWNERS` (Zeile 1), `EntityDto` (14),
  `EntityRefDto` (57), `EntityType` (87), `DomainDto` (92).
- `docs/decisions/025-knowledge-vault-markdown-wahrheit.md` — die Regel, gegen die diese Phase
  sich nicht versündigen darf: die Markdown-Datei ist die Wahrheit, SQLite ist nur Cache.
  Konsequenz: die Vollständigkeit wird **nie** gespeichert, nur berechnet.

## Aufgabe 1 — Schema
`knowledge/schema.py`, nach `Relationship` einfügen:
```python
@dataclass
class Attribute:
    """Ein einzelnes Merkmal einer Entity (Geburtstag, Beruf, …) mit eigenem Owner.

    Der Owner sitzt bewusst **pro Merkmal**, nicht nur auf der Entity: ein manuell
    gepflegter Wohnort darf nicht verschwinden, nur weil eine Web-Recherche denselben
    Datensatz anfasst. Die Überschreib-Regel ist dieselbe wie auf Entity-Ebene
    (``owner_can_overwrite``), nur feiner angewendet.
    """

    value: str
    owner: Owner = Owner.INFERRED
    confidence: float = 1.0
```

`Entity` um ein Feld erweitern, **hinter** `sources`, **vor** `body`:
```python
    attributes: dict[str, Attribute] = field(default_factory=dict)
```

Ein Merkmal mit leerem `value` gilt als nicht gesetzt. Der Normalfall für „nicht gesetzt" ist
aber, dass der Key gar nicht im Mapping steht — leere Werte werden beim Schreiben entfernt
(Aufgabe 5), damit die Datei nicht mit Leerzeilen zuwächst.

## Aufgabe 2 — Feld-Definitionen in der Domäne
`knowledge/domains.py`:
```python
@dataclass(frozen=True)
class FieldDef:
    """Ein für einen Entity-Typ vorgesehenes Merkmal. ``key`` steht im Frontmatter,
    ``label`` ist der Anzeigename in der Oberfläche."""

    key: str
    label: str
```

`EntityType` um ein Feld erweitern:
```python
    fields: tuple[FieldDef, ...] = ()
```

`_parse_entity_types` erweitern: den optionalen Schlüssel `fields` je Eintrag lesen. Fehlt er →
leeres Tupel (kein Fehler, bestehende Domänen-Dateien bleiben gültig). Ist er da, aber keine
Liste von Mappings mit `key` → `DomainLoadError` im Stil der bestehenden Fehlermeldungen
(`f"'fields'-Eintrag ohne 'key': {entry!r} in {path}"`). Fehlt `label`, wird `key` als Label
verwendet.

Neue Methode auf `Domain`, neben `folder_for`:
```python
    def fields_for(self, type_name: str) -> tuple[FieldDef, ...]:
        """Die Merkmals-Definitionen eines Entity-Typs. Unbekannter Typ → leeres Tupel
        (keine Ausnahme — Aufrufer sind Anzeige-Pfade, die nicht wegen eines Tippfehlers
        in der Domänen-Datei umfallen sollen)."""
        entity_type = self.entity_types.get(type_name)
        return entity_type.fields if entity_type is not None else ()
```

## Aufgabe 3 — Frontmatter-Round-Trip (der Wackelpunkt dieser Phase)
`knowledge/parser.py`:

`_FIELD_ORDER` um `"attributes"` erweitern — **nach** `"sources"`, als letzter Eintrag.

`entity_to_metadata` um den Block erweitern (letzter Eintrag im Mapping, gleiche Reihenfolge):
```python
        "attributes": {
            key: {
                "value": attribute.value,
                "owner": attribute.owner.value,
                "confidence": attribute.confidence,
            }
            for key, attribute in entity.attributes.items()
        },
```

`metadata_to_entity` um `attributes=_as_attributes(meta.get("attributes")),` erweitern
(zwischen `sources` und `body`).

Neuer Helfer, direkt nach `_as_media_links`:
```python
def _as_attributes(value: Any) -> dict[str, Attribute]:
    """Liest den ``attributes``-Block. Fehlt er komplett (alle vor dieser Phase
    geschriebenen Dateien), ist das kein Fehler — leeres Mapping."""
    if not isinstance(value, dict):
        return {}
    attributes: dict[str, Attribute] = {}
    for key, raw in value.items():
        if not isinstance(raw, dict):
            raise EntityParseError(f"Merkmal '{key}' ist kein Mapping: {raw!r}")
        attributes[str(key)] = Attribute(
            value=_as_str(raw.get("value")),
            owner=_as_owner(raw.get("owner", Owner.INFERRED.value)),
            confidence=_as_confidence(raw.get("confidence", 1.0)),
        )
    return attributes
```
(`Attribute` oben im Import aus `photofant.knowledge.schema` ergänzen.)

**Round-Trip-Test vor dem Weiterbauen** (Konfidenz-Ausweis README, Punkt 2): eine Entity mit
drei Merkmalen (einer davon mit Umlauten und einem Doppelpunkt im Wert, einer mit leerem Wert)
durch `serialize_entity` → Datei ansehen → `parse_entity` → auf Gleichheit prüfen. Erwartung:
verlustfrei, weil `media_links` denselben Weg schon geht. Weicht etwas ab (Anführungszeichen,
Zeilenumbrüche in langen Werten), hier korrigieren — nicht in Phase 3 auffangen.

## Aufgabe 4 — Validierung
`knowledge/validator.py`, neue Funktion im Stil von `_check_relationships`:
```python
def _check_attributes(meta: dict[str, Any], domain: Domain, errors: list[str]) -> None:
    """Merkmale müssen für den Entity-Typ definiert sein — sonst wächst über KI-Läufe
    ein wildes Feld-Sammelsurium heran, das keine Oberfläche mehr anzeigen kann."""
```
Regeln, jede als eigene Fehlerzeile:
- `attributes` ist vorhanden, aber kein Mapping → `"'attributes' muss ein Mapping sein"`.
- Ein Key ist für den Entity-Typ nicht definiert (`domain.fields_for(type)`) →
  `f"Merkmal '{key}' ist für Typ '{type_name}' nicht definiert"`.
- `owner` unbekannt oder `confidence` nicht numerisch/außerhalb 0..1 → je eine Zeile, Wortlaut
  analog zu `_check_owner`/`_check_confidence`.

Aufruf in `validate_metadata` ergänzen, hinter `_check_relationships`.

## Aufgabe 5 — Vollständigkeit + Schreibweg
`knowledge/service.py`:

```python
    def completeness_for(self, entity: Entity, domain: Domain) -> float:
        """Anteil gefüllter Merkmale an den für den Typ definierten. Immer berechnet,
        nie gespeichert — ein persistierter Wert würde gegen die Markdown-Wahrheit
        driften (ADR-025)."""
        defined = domain.fields_for(entity.type)
        if not defined:
            return 0.0
        filled = sum(
            1 for definition in defined
            if entity.attributes.get(definition.key, Attribute(value="")).value.strip()
        )
        return filled / len(defined)
```

Eigener Schreibweg (**nicht** über `update_entity`, weil dessen `_check_ownership` auf
Entity-Ebene arbeitet und ein einzelnes `user`-Merkmal sonst von einem `web`-Lauf mitgerissen
würde):
```python
    def set_attributes(
        self, entity_id: str, attributes: dict[str, Attribute], owner: Owner
    ) -> tuple[Entity, list[str], list[str]]:
        """Schreibt Merkmale einzeln, jedes gegen seinen eigenen bisherigen Owner geprüft.

        Rückgabe: (gespeicherte Entity, geschriebene Keys, Meldungen zu übersprungenen Keys).
        Übersprungen wird still im Sinne von „kein Fehler" — aber nie stumm: jeder
        übersprungene Key kommt als Klartext-Meldung zurück und landet in der Oberfläche.
        """
```
Ablauf:
1. Entity laden (`_require_entity`), Domäne laden.
2. Je Key: existiert schon ein Merkmal → `owner_can_overwrite(owner, vorhandener_owner)`
   prüfen. Nein → Meldung `f"'{label}' bleibt unverändert — der Wert stammt von dir"`
   (bei `user`/`manual`) bzw. `f"'{label}' bleibt unverändert"` sonst, und weiter.
3. Leerer Wert → Key aus `entity.attributes` entfernen (statt leer zu speichern).
4. Nach der Schleife: validieren, `vault.save_entity`, `entities.upsert_from_vault`.
5. **`entity.owner` bleibt unangetastet** — ein Merkmals-Schreiben ändert nicht die
   Ownership der ganzen Einheit. Das ist der Punkt der ganzen Phase.

Changelog schreibt diese Methode **nicht** — das macht der Aufrufer (Phase 4), damit
`job_id`/`reason` von dort kommen, wie bei den bestehenden Schreibpfaden auch.

## Aufgabe 6 — Ausgelieferte Domänen befüllen
`knowledge/domains/private.yaml` — beide Typen bekommen Felder. Die Keys stammen aus dem
Design (`design/js/data.js`, `KFIELD_DEFS`):
```yaml
entity_types:
  - name: Person
    folder: people
    fields:
      - key: geburtstag
        label: Geburtstag
      - key: beruf
        label: Beruf
      - key: wohnort
        label: Wohnort
      - key: vorlieben
        label: Vorlieben
      - key: beziehung
        label: Beziehungsstatus
  - name: Pet
    folder: pets
    fields:
      - key: art
        label: Art
      - key: geburtstag
        label: Geburtstag
      - key: eigenheiten
        label: Eigenheiten
```

`knowledge/domains/movies.yaml` — nur `Actor` und `Movie` bekommen Felder, der Rest bleibt
ohne (zeigt gleichzeitig, dass „keine Felder definiert" ein gültiger Zustand ist):
```yaml
  - name: Actor
    folder: actors
    fields:
      - key: geburtstag
        label: Geburtstag
      - key: geburtsort
        label: Geburtsort
      - key: taetigkeit
        label: Tätigkeit
  - name: Movie
    folder: movies
    fields:
      - key: erscheinungsjahr
        label: Erscheinungsjahr
      - key: regie
        label: Regie
      - key: laufzeit
        label: Laufzeit
```

⚠️ Diese Dateien werden beim ersten Vault-Zugriff **einmalig** in den Vault kopiert
(`vault.py::_seed_packaged_domains`). Ein bestehender Vault bekommt die Felder dadurch **nicht**
automatisch. Das ist kein Bug und wird auch nicht automatisiert — es ist die Nutzer-Datei. In
die Smoke-Checkliste gehört stattdessen: einmal die eigene `<vault>/domains/private.yaml` von
Hand um den `fields`-Block ergänzen. Als Hinweis in die AGENTS-Vorlage des Vaults
(`knowledge/AGENTS.md.template`) eine Zeile aufnehmen, dass Merkmale hier definiert werden.

## Aufgabe 7 — API-DTOs
`api/knowledge.py`:
```python
class AttributeDto(BaseModel):
    value: str
    owner: str
    confidence: float


class FieldDefDto(BaseModel):
    key: str
    label: str
```
- `EntityTypeDto` += `fields: list[FieldDefDto] = []`, in `DomainDto.from_domain` befüllen.
- `EntityDto` += `attributes: dict[str, AttributeDto]` und `completeness: float`. In der
  `from_entity`-Klassenmethode die Domäne laden, um `completeness_for` aufzurufen — **eine**
  Domänen-Ladung pro Request, nicht pro Entity (bei Listen-Endpunkten die Domänen einmal
  vorladen und durchreichen, sonst liest die Übersicht bei 200 Personen 200-mal dieselbe
  YAML-Datei).
- `EntityRefDto` += `completeness: float = 0.0` — damit die Personen-Karte und die Übersicht den
  Prozentwert ohne zweiten Request haben.

## Aufgabe 8 — Frontend-Modelle
`frontend/src/app/models/knowledge.model.ts`, exakt nach dem Kontrakt der README:
```ts
export interface AttributeDto {
  value: string;
  owner: Owner;
  confidence: number;
}

export interface EntityFieldDefDto {
  key: string;
  label: string;
}
```
- `EntityDto` += `attributes: Record<string, AttributeDto>;` und `completeness: number;`
- `EntityType` += `fields: EntityFieldDefDto[];`
- `EntityRefDto` += `completeness: number;`

Keine Komponente in dieser Phase anfassen — nur die Typen. Wo `tsc` danach meckert, weil ein
Test-Mock die neuen Pflichtfelder nicht hat: Mock ergänzen, nicht das Feld optional machen.

## Aufgabe 9 — ADR-032
`docs/decisions/032-merkmale-mit-eigenem-owner.md` (Nummer verifiziert 2026-07-21: Platte bis
030, in Plänen reserviert 031 durch Phase 1 dieses Plans):

Kontext: bis hierher hatte eine Wissenseinheit einen Owner für alles; Vollständigkeit und
feingranulare Herkunft waren nicht darstellbar. Betrachtete Optionen: (a) Merkmale als
strukturierte Abschnitte im Markdown-Body parsen — verworfen, weil der Body ausdrücklich
Freitext bleiben soll und ein Parser darauf bei jeder Handbearbeitung bricht; (b) eigene
SQLite-Tabelle für Merkmale — verworfen, weil SQLite laut ADR-025 nur Cache ist und Merkmale
sonst nicht mehr im Vault-Export stecken; (c) Frontmatter-Block mit Owner pro Merkmal —
gewählt. Konsequenzen: das Frontmatter wächst, die Datei bleibt von Hand editierbar, die
Vollständigkeit ist eine reine Ableitung und wird nie gespeichert; die Feld-Definitionen leben
in der Domänen-YAML und sind damit Nutzer-Eigentum, nicht Code.

## AK dieser Phase
- [x] Round-Trip verlustfrei: Entity mit drei Merkmalen (Umlaute, Doppelpunkt im Wert, ein
      leerer Wert) speichern → Datei lesbar → neu parsen → identisch (Aufgabe 3).
- [x] Eine Vault-Datei **ohne** `attributes`-Block lädt weiterhin fehlerfrei und liefert ein
      leeres Merkmals-Mapping (kein Migrationszwang).
- [x] Ein Merkmal, das für den Entity-Typ nicht definiert ist, wird von der Validierung mit
      einer verständlichen Meldung abgelehnt.
- [x] `set_attributes` mit `Owner.WEB` überschreibt ein `user`-Merkmal **nicht** und liefert
      dafür eine Klartext-Meldung in der dritten Rückgabe-Liste zurück.
- [x] `set_attributes` ändert `entity.owner` nicht.
- [x] `completeness_for` liefert für einen Typ mit 5 definierten und 2 gefüllten Merkmalen
      exakt `0.4`; für einen Typ ohne definierte Merkmale `0.0`. *(als 2/3 bzw. 0.0 gegen die
      mitgelieferte Movies-Domäne geprüft — dieselbe Rechnung.)*
- [x] `GET /api/knowledge/entities` liefert `attributes` und `completeness` mit; `GET
      /api/knowledge/domains` liefert `fields` je Entity-Typ.
- [x] `npx tsc --noEmit` im Frontend grün, `ruff` + `mypy` im Backend ohne neue Fehler.

## Doc-Updates
- [x] `docs/models.md` — `attributes`-Block im Entity-Frontmatter dokumentieren (Struktur +
      dass `completeness` berechnet und nie gespeichert ist).
- [x] `docs/routes.md` — `EntityDto`/`DomainDto`/`EntityRefDto` um die neuen Felder ergänzen.
- [x] `docs/glossary.md` — Einträge „Merkmal" (Feld mit eigenem Owner) und „Vollständigkeit"
      (berechneter Anteil gefüllter Merkmale) aufnehmen.
- [x] `docs/code-map.md` — Wissens-Zeile um `knowledge/domains.py::FieldDef` +
      `service.completeness_for/set_attributes` ergänzen.

## Report-Back

**Status:** complete (2026-07-21).

**Abweichung vom Plan — Merkmale liegen zusätzlich im Cache.** Der Plan wollte
`EntityRefDto.completeness` „ohne Extra-Request". Die Cache-Zeile trug die Merkmale aber nicht,
also hätte die Personen-Liste pro Zeile eine Markdown-Datei öffnen müssen — genau das, was der
Kommentar an `EntityRef` seit P24 ausdrücklich vermeidet (die Liste ist unpaginiert). Deshalb
neu: `knowledge_entities.attributes` als JSON-Spiegel (migration 0040), gleiche Form wie im
Frontmatter, geschrieben in `upsert_from_vault` wie die Aliase. ADR-025 bleibt gewahrt: das ist
Spiegelung, kein neuer Wahrheitsort, und der Prozentwert selbst wird weiterhin nirgends
gespeichert. Mit-Effekt: Phase 4 kann `missing_field`/`low_completeness` aus einem Query bauen.

**Zwei kleine Zugaben, die der Plan nicht nannte:**
- `attributes_to_mapping()` in `schema.py` — Frontmatter- und Cache-Schreibweg hatten sonst
  dieselbe Mapping-Form doppelt im Code stehen.
- `KnowledgeService._domain()`-Memo: der Lesepfad lud die Domänen-YAML pro Entity neu, bei der
  Entity-Liste also einmal je Zeile. Der Plan forderte „eine Domänen-Ladung pro Request" — das
  ist die Umsetzung, sie repariert nebenbei einen Altbestand-Fall.

**Tests:** neue `backend/tests/test_knowledge_attributes.py` (10 Tests, grün) deckt Round-Trip,
Validierung, Ownership pro Merkmal und die Vollständigkeit ab. Drei bestehende Tests mussten die
gewachsenen DTOs nachziehen (`completeness` in den Ref-Vergleichen) — keine Assertion gelockert.

**Gates:** ruff auf allen geänderten Dateien grün, mypy ohne neue Fehler, Frontend-Lint und
-Build grün. Gesamt-Suite 397 grün / 13 rot — alle 13 auf dem unveränderten Stand ebenfalls rot
(siehe Vorbelastung in STATE.md).
