# Wissen: mehr Tiefe, Design nachgezogen

Das Wissen-Feature bleibt hinter dem Design-Mockup zurück, und die beiden Erfassungswege
liefern zu wenig: Das **Interview** erzeugt heute nur einen Fließtext-Absatz und füllt kein
einziges Merkmal — es fragt die Merkmale ja auch gar nicht ab. Die **Web-Recherche** sucht ins
Blaue statt in den für die Domäne einschlägigen Quellen und schreibt von Gemma vorgeschlagene
neue Einträge, ohne sie je zu zeigen. Dazu fehlen im Detail-Dialog drei Design-Elemente.

Der Hebel für die ersten beiden Punkte liegt in den **Domänen-Dateien**: Dort steht schon, welche
Merkmale ein Typ hat. Dort kommen jetzt die passende **Frage** und die **bevorzugten Quellen**
dazu — Frage und Feld wandern gemeinsam, und ein neues Merkmal bringt seine Frage automatisch mit.

Mockup: `C:\Users\sasch\Downloads\Photofant\design_handoff_photofant\wissen-feature`
(`js/knowledge.jsx` = Referenz für Detail-Dialog und beide Wizards).

**Nachträglich (2026-07-22) zwei weitere Lücken gefunden**, beim Test einer Person-Verknüpfung
(She-Hulk/Tatiana Maslany): Eine verknüpfte Person zeigte trotz bestehender Verknüpfung keine
Fotos, und Captions/Tags der Fotos fließen nirgends in die KI-Ergänzung ein. Beides sind
Phase 7 und 8 geworden.

## Phasen

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [Domänen: Feld-Fragen und bevorzugte Quellen](phase-1-domaenen-schema.md) | standard | complete |
| 2 | [Interview: Fragen aus der Domäne, Antworten feldgenau](phase-2-interview-fragen-merkmale.md) | heikel | complete |
| 3 | [Merkmale speichern und im Wizard zeigen](phase-3-merkmale-end-to-end.md) | standard | complete |
| 4 | [Web-Recherche: bevorzugte Quellen + Einträge bestätigen](phase-4-web-recherche.md) | standard | pending |
| 5 | [„aktualisiert am …" end-to-end](phase-5-zeitstempel.md) | standard | pending |
| 6 | [Detail-Dialog: Album-Button + KI-Banner](phase-6-detail-dialog.md) | standard | pending |
| 7 | [Fotos: echte Verknüpfung zur Person](phase-7-foto-verknuepfung.md) | standard | pending |
| 8 | [Captions/Tags als Signal für die KI-Ergänzung](phase-8-captions-tags-signal.md) | standard | pending |

Phase 1 ist das Fundament für 2 und 4 und muss zuerst laufen. Der Rest ist untereinander
unabhängig — mit einer losen Ausnahme: Phase 6 Teil A (Album-Button) lässt sich zwar auch ohne
Phase 7 bauen und testen (ein Foto lässt sich zum Testen manuell per `PATCH .../entities/{id}`
in `media_links.assets` eintragen), zeigt aber erst nach Phase 7 im echten Betrieb ohne
Handarbeit etwas an.

## Kontrakt (Backend ↔ Frontend)

Sechs Schnittstellen werden erweitert. Sie sind hier festgenagelt, damit Phasen unabhängig
umsetzbar bleiben.

### 0. Domänen-Dateien (Phase 1 → 2 und 4)

Zwei neue, optionale YAML-Schlüssel. Beide reisen über `DomainDto` ins Frontend.

```yaml
name: Movies
preferred_sources: [wikipedia.org]         # Vorgabe der Domäne
entity_types:
  - name: Actor
    folder: actors
    preferred_sources: [imdb.com, wikipedia.org]   # schlägt die Domänen-Vorgabe
    fields:
      - key: geburtstag
        label: Geburtstag
        question: Wann hat {name} Geburtstag?      # nur für das Interview
```

- `question` fehlt → das Merkmal wird im Interview nicht gefragt.
- `preferred_sources` am Typ gewinnt vollständig gegen die der Domäne; fehlen beide → leer.
- Private Domänen tragen keine bevorzugten Quellen (sie gehen nie ins Netz).

### 1. Interview-Ergebnis (Phase 2 → 3)

`KnowledgeInterviewResult.suggestion` bekommt ein Feld `attributes`. Das Label reist mit,
damit das Frontend keine Domänen-Auflösung braucht:

```jsonc
"suggestion": {
  "title": "Jonas", "type": "Person", "domain": "Privat",
  "aliases": [], "relationships": [], "body": "…",
  "attributes": {
    "beruf": { "label": "Beruf", "value": "Elektroingenieur", "owner": "inferred", "confidence": 0.8 }
  }
}
```

- Keys **ausschließlich** aus `domain.fields_for(entity_type)` — unbekannte Keys werden im
  Backend verworfen, nie durchgereicht.
- `owner` ist `"user"`, wenn der Nutzer den Wert im Interview selbst eingetippt hat, und
  `"inferred"`, wenn Gemma ihn für ein leer gelassenes Feld vorgeschlagen hat (ADR-034).
  Ein selbst eingetippter Wert wird nie von einem Modell-Vorschlag überschrieben.
- `attributes` darf leer sein (`{}`) — das ist der Normalfall bei kargen Antworten.

### 2. Entity anlegen mit Merkmalen (Phase 3)

`CreateEntityRequest` bekommt `attributes: dict[str, AttributeDto] = {}`.
Der Entity-Owner bleibt `user` (der Nutzer hat bestätigt); jedes **Merkmal** behält seinen
eigenen Owner aus dem DTO (ADR-032). Kein Merkmals-Owner wird vom Entity-Owner überschrieben.

### 3. Zeitstempel (Phase 5)

`EntityDto` bekommt `updated_at: datetime | None` — gelesen aus der Änderungszeit der
Vault-Markdown-Datei, nicht gespeichert (der Vault bleibt Markdown-first, keine neue Spalte).
`null` ist gültig, wenn die Datei nicht auflösbar ist; das Frontend blendet die Angabe dann aus.

### 4. Fotos einer verknüpften Person (Phase 7)

`related_media` in `LoreDto` bleibt vom Typ her unverändert (`kind="asset"`-Einträge), enthält
bei einer personen-verknüpften Entity aber zusätzlich die **live** aus `AssetInstance` gelesenen
Fotos der Person, nicht nur die manuell in `media_links.assets` eingetragenen. Diese Fotos werden
**nicht** in den Vault zurückgeschrieben — reine Lesezeit-Anreicherung, damit ein neues Foto der
Person sofort auftaucht, ohne die Markdown-Datei zu berühren.

### 5. Captions/Tags im KI-Prompt (Phase 8)

Kein neuer Endpunkt, keine neue DTO-Schnittstelle — `knowledge_update_job._build_user_prompt`
bekommt intern mehr Kontext (Captions + Top-Tags der Fotos der verknüpften Person). Für
Frontend/API unsichtbar; der bestehende Vorschlag-Owner (`inferred`) und Opt-in-Ablauf ändern
sich nicht.

## Finale AK (Gesamtergebnis)

1. Das Interview fragt die Merkmale des Typs **aktiv ab** — je Merkmal mit hinterlegter Frage ein
   eigenes Eingabefeld, alle optional.
2. Ein Interview mit ausgefüllten Eckdaten legt eine Notiz an, deren Merkmale **wörtlich** die
   eingetippten Werte tragen (Owner-Pill „Selbst angegeben").
3. Ein Interview mit ausschließlich leeren Antworten läuft trotzdem durch und erzeugt eine
   Notiz ohne Merkmale — kein Fehler, kein Abbruch.
4. Die Web-Recherche durchsucht bei einer Domäne/einem Typ mit bevorzugten Quellen zuerst diese
   (Schauspieler → IMDb, Wikipedia) und füllt danach mit einer offenen Suche auf.
5. Die Web-Recherche zeigt gefundene **neue Einträge** als abhakbare Zeilen; abgewählte
   Einträge werden nicht geschrieben.
6. Der Detail-Dialog zeigt in der Kopfzeile „N % vollständig · Domäne · aktualisiert TT. Mon JJJJ".
7. Der Detail-Dialog hat unter den Sektionen eine Album-Zeile, die aus den verknüpften Fotos
   ein echtes Album anlegt.
8. Eine mit einer Person verknüpfte Wissens-Entity zeigt deren erkannte Fotos automatisch als
   „Verknüpfte Fotos" — ohne manuelles Einzel-Verknüpfen.
9. Der KI-Ergänzungsvorschlag bezieht bei personen-verknüpften Entities Captions/Tags der
   Fotos dieser Person als zusätzlichen Hinweis mit ein.
10. `cd backend && uv run ruff check .` und `cd frontend && npm run lint && npm run build` sind grün.

## Kritisch gegenlesen

🟡 **Das Halluzinations-Risiko ist stark gesunken, aber nicht null.** Ursprünglich sollte Gemma
die Merkmale aus Prosa herauslesen — genau deshalb hatte P27 den Interview-Job bewusst prosa-only
gelassen. Jetzt werden die Merkmale **gefragt**: Was der Nutzer eintippt, wird wörtlich übernommen,
ohne Modell dazwischen. Das Modell darf nur noch für **leer gelassene** Felder einen Wert
vorschlagen, markiert als „KI-Schätzung". Damit trägt der deterministische Pfad das Gewicht und
der riskante ist optional, klein und erkennbar. Begründung als ADR-034.

🟡 **JSON aus Gemma ist nicht garantiert.** Bricht das Parsen, darf das Interview **nicht**
scheitern — Fallback: kompletter Text wird `body`, die **gefragten** Merkmale bleiben erhalten
(sie hängen nicht am Modell). Das ist der wichtigste Test der Phase 2.

🟡 **Bevorzugte Quellen dürfen die Suche nicht verengen.** Ein harter `site:`-Filter kann leer
zurückkommen. Deshalb zwei Durchläufe: erst eingeschränkt, dann offen auffüllen — nie nur
eingeschränkt.

🟡 **Das Interview wird länger.** Für eine private Person kommen zu den drei Erzähl-Fragen fünf
Merkmals-Felder dazu. Damit daraus kein Formular-Marathon wird, liegen **alle Merkmals-Felder auf
einem einzigen Schritt** („Eckdaten") statt je einem Wizard-Schritt — vier Schritte statt acht.
Das weicht bewusst vom Mockup ab, das eine Frage pro Schritt zeigt.

🟡 **Proaktiver KI-Banner vs. strikter Opt-in.** Das Mockup zeigt den Vorschlag sofort beim
Öffnen; der Bestand fordert bewusst einen Klick, weil jedes Öffnen sonst einen echten
Gemma-Lauf auslöst (P38-Prinzip „KI nur auf explizite Aktion"). **Entscheidung: Opt-in bleibt**
— der Auslöser wird nur optisch zum designten Banner und erklärt sich selbst. Kein Auto-Lauf
beim Öffnen. Details in Phase 5.

🟡 **Fotos live lesen statt im Vault spiegeln (Phase 7) — bewusste Abweichung vom bestehenden
`media_links`-Muster.** Jede andere Verknüpfung in diesem System liegt explizit in der
Markdown-Datei. Für Personen-Fotos wäre das bei Hunderten Bildern und ständigem Zuwachs die
falsche Richtung (Vault-Schreiblast, Datenverdopplung mit `AssetInstance`). Deshalb hier bewusst
eine Ausnahme: gelesen, nie geschrieben. Fällt bei der Umsetzung ein Grund auf, warum das nicht
trägt (z.B. Performance bei sehr vielen erkannten Fotos), gehört das in die FINDINGS.

🟡 **Deckelung der Foto-/Caption-Anzahl (Phase 7 + 8) ist noch keine Zahl, nur eine Absicht.**
Wie viele Fotos/Captions „genug" sind, ohne den Dialog bzw. den Prompt aufzublähen, ist beim
Schreiben dieser Phasen nicht verifiziert — Startwert in der Umsetzung selbst festlegen und in
FINDINGS begründen, falls er sich als zu klein/groß herausstellt.

### Konfidenz-Ausweis

1. **Ob die Bonus-Schätzung aus den Erzähl-Antworten brauchbar ist, weiß ich nicht** — das hängt
   am Modell auf dieser Maschine. Der gefragte Pfad ist davon unabhängig und trägt auch dann,
   wenn die Schätzung nichts liefert. Auflösender Check: nach Phase 3 drei Interviews fahren, bei
   denen bewusst Felder leer bleiben, und schauen, ob die „KI-Schätzung"-Werte plausibel sind
   (Smoke-Checkliste Punkt 2).
2. **Ob DuckDuckGo `site:`-Verknüpfungen mit `OR` zuverlässig annimmt**, habe ich nicht
   verifiziert — die Suchanbindung geht über `ddgs`. Auflösender Check zu Beginn Phase 4:
   eine Beispielanfrage gegen `search_web` fahren und die Treffer-Hosts ansehen. Fällt sie durch,
   ist der Rückfallweg trivial: je bevorzugter Quelle eine eigene Anfrage statt einer verknüpften.
3. **Zeitstempel-Pfad ist geklärt** — `Vault.entity_path(entity, domain)` existiert (Zeile 69),
   nachgesehen. Ebenso bestätigt: `createCollection` im Frontend-Service, `set_attributes`,
   `domain.fields_for()`, die Prompt-Datei und die beiden Domänen-YAMLs.

## Smoke-Checkliste (User, am Plan-Ende)

Wackelstellen zuerst:

1. **Interview mit einer realen Person, Eckdaten ausgefüllt**: Stehen die eingetippten Werte
   danach **wörtlich** als Merkmale im Profil, mit Pill „Selbst angegeben"? Das ist der Kernpfad.
2. **Interview mit absichtlich leer gelassenen Feldern**: Schlägt Gemma dafür etwas vor? Ist es
   plausibel oder erfunden? 3 Läufe — hier entscheidet sich, ob der Bonus-Pfad bleibt.
3. **Interview ganz ohne Antworten**: läuft es durch, ohne zu scheitern?
4. **Web-Recherche auf einem Schauspieler**: Tauchen IMDb/Wikipedia unter den Quellen auf?
   Erscheinen gefundene Einträge als abhakbare Zeilen, und bleibt ein abgewählter Eintrag
   wirklich weg (danach in der Wissen-Übersicht prüfen)?
5. **Detail-Dialog**: Datum in der Kopfzeile plausibel? Album-Button legt ein Album an, das in
   der Alben-Ansicht auftaucht?
6. **Bestehende Merkmale**: Ein von Hand gepflegtes Merkmal darf ein Interview **nicht**
   überschreiben (Owner-Schutz).
7. **Person mit vielen Fotos verknüpfen**: Tauchen die Fotos ohne manuelles Zutun unter
   „Verknüpfte Fotos" auf? Legt der Album-Button daraus ein echtes Album an? Enthält der
   KI-Vorschlag danach erkennbar etwas aus den Captions/Tags dieser Fotos?

## Summary

_(beim Archivieren füllen)_

## Files touched

_(beim Archivieren füllen)_

## Deviations from plan

_(beim Archivieren füllen)_

## Follow-ups

_(beim Archivieren füllen)_
