# ADR-034 — Das Interview fragt Merkmale ab, statt sie aus Prosa zu raten

**Status:** Akzeptiert — 2026-07-22
**Querverweise:** [032](032-merkmale-mit-eigenem-owner.md) ·
[031](031-web-recherche-netzwerkzugriff.md) ·
Konzept-ADR-009 (Privat/Öffentlich-Trennung)

## Kontext
Der Interview-Mode war bewusst prosa-only: Gemma fasste die Antworten zu einem Absatz
zusammen und durfte nichts darüber hinaus behaupten (Konzept-ADR-009 — „nur zusammenfassen,
nie Fakten erfinden"). Seit Merkmale ein eigener Datenpunkt mit eigenem Owner sind
(ADR-032), fällt auf, was dabei fehlt: Ein komplettes Interview über eine private Person
hinterlässt ein Profil mit **null** ausgefüllten Merkmalen — der Vollständigkeits-Ring bleibt
bei 0 %, und die Aufgabe „Feld fehlt" bleibt für immer offen.

Der naheliegende Weg wäre gewesen, Gemma die Merkmale aus dem Erzähltext herauslesen zu
lassen. Genau das hatte die ursprüngliche Entscheidung untersagt, und zwar zu Recht: Bei
einer realen, dem Nutzer bekannten Person ist ein geratener Geburtstag oder Wohnort kein
harmloser Fehler, sondern eine erfundene Behauptung über einen echten Menschen — in einer
Datenbank, die er als Wahrheit ansieht.

## Entscheidung
Die Merkmale werden **gefragt**, nicht geraten. Trägt ein Merkmal in der Domänen-Datei eine
`question`, bekommt es im Interview ein eigenes Eingabefeld (alle Felder liegen zusammen auf
einem Schritt „Eckdaten", damit der Wizard kein Formular-Marathon wird). Was der Nutzer dort
eintippt, wird **wörtlich** übernommen: Owner `user`, volle Confidence, ohne Modell dazwischen.

Der Modell-Pfad bleibt erhalten, aber klein und optional: Für Merkmale, die der Nutzer
**leer gelassen** hat, darf Gemma aus den Erzähl-Antworten einen Wert vorschlagen — Owner
`inferred`, in der Oberfläche als KI-Schätzung erkennbar. Ein vom Nutzer gefülltes Merkmal
wird davon nie angefasst; die Merkmals-Keys stammen ausschließlich aus der Domäne, alles
andere verwirft das Backend.

Das **präzisiert** Konzept-ADR-009, hebt es nicht auf: Ein selbst eingetippter Wert ist kein
erfundener Fakt. Das Gewicht liegt jetzt auf dem deterministischen Pfad, der riskante ist
optional, auf leere Felder beschränkt und als solcher markiert.

## Betrachtete Optionen
- **Alles wie bisher lassen (nur Prosa)** — verworfen: Merkmale blieben dauerhaft leer, und
  der ganze Vollständigkeits-Apparat aus ADR-032 liefe für private Personen ins Leere.
- **Gemma die Merkmale aus dem Erzähltext extrahieren lassen** — verworfen: maximales
  Halluzinations-Risiko genau dort, wo es am teuersten ist (reale Personen). Ein geratener
  Geburtstag sieht im Profil genauso aus wie ein echter.
- **Gefragte Felder + optionale Schätzung für leere Felder** — gewählt.

## Konsequenzen
- Die Fragen leben in der Domänen-Datei, nicht im Frontend. Ein neues Merkmal bringt seine
  Frage automatisch mit; ein Merkmal ohne `question` wird schlicht nicht gefragt.
- Das Interview wird länger — statt fünf Fragen sind es drei Erzähl-Fragen plus ein Schritt
  mit den Merkmals-Feldern. Zwei bisherige Fragen (Vorlieben, Beziehung) entfallen, weil sie
  jetzt Merkmals-Fragen sind und sich sonst doppeln würden.
- **JSON aus einem rohen Text-LM ist nicht garantiert.** Bricht das Parsen, ist das kein
  Fehlerfall: der komplette Modell-Text wird zum Absatz, und die gefragten Merkmale bleiben
  vollständig erhalten — sie hängen nicht am Modell. Das Interview kann daran nicht scheitern.
- Ob die Bonus-Schätzung auf einem kleinen lokalen Modell überhaupt brauchbare Werte liefert,
  ist offen. Trägt sie nichts bei, bleibt der gefragte Pfad davon unberührt — dann wäre der
  Bonus-Pfad ersatzlos entfernbar, ohne dass das Feature etwas verliert.
