# ADR-032 — Merkmale als Frontmatter-Block mit Owner pro Merkmal

**Status:** Akzeptiert — 2026-07-21
**Querverweise:** [025](025-knowledge-vault-markdown-wahrheit.md) ·
[031](031-web-recherche-netzwerkzugriff.md)

## Kontext
Bis hierher hatte eine Wissenseinheit **einen** Owner für alles und einen Freitext-Body.
Damit ließ sich weder sagen, wie vollständig das Wissen über eine Person ist, noch woher ein
einzelner Wert stammt. Beides braucht die neue Wissens-Oberfläche (Vollständigkeits-Ring,
Herkunfts-Pillen, die Aufgaben „Feld fehlt" und „kaum ausgefüllt") — und die Web-Recherche
(ADR-031) braucht es zwingend: sie muss einen von Hand gepflegten Wert stehen lassen können,
während sie daneben ein leeres Feld füllt.

## Entscheidung
Merkmale sind ein eigener `attributes`-Block im Frontmatter. Jedes Merkmal trägt `value`,
einen **eigenen** `owner` und eine eigene `confidence`. Welche Merkmale ein Entity-Typ hat,
legt die Domänen-Datei fest (`fields:` je Entity-Typ) — nicht der Code. Die Vollständigkeit
ist gefüllte durch definierte Merkmale und wird bei jedem Ausliefern berechnet, **nie**
gespeichert.

Geschrieben wird über einen eigenen Weg (`set_attributes`), nicht über den bestehenden
Entity-Patch: die bisherige Ownership-Prüfung arbeitet auf Entity-Ebene und würde ein
einzelnes selbst gepflegtes Merkmal von einem Web-Lauf mitreißen. Ein Merkmals-Schreiben
lässt die Ownership der ganzen Einheit unverändert.

## Betrachtete Optionen
- **Merkmale als strukturierte Abschnitte im Markdown-Body parsen** — verworfen: der Body
  soll ausdrücklich Freitext bleiben, und ein Parser darauf bricht bei jeder Handbearbeitung.
- **Eigene SQLite-Tabelle für Merkmale** — verworfen: SQLite ist laut ADR-025 nur Cache;
  Merkmale steckten dann nicht mehr im Vault-Export und wären beim Rebuild verloren.
- **Frontmatter-Block mit Owner pro Merkmal** — gewählt.

## Konsequenzen
- Das Frontmatter wächst, die Datei bleibt aber von Hand editierbar und der Round-Trip
  verlustfrei (geprüft mit Umlauten, Doppelpunkten, langen Werten, leeren Werten).
- Die Feld-Definitionen leben in der Domänen-YAML und sind damit Nutzer-Eigentum, nicht Code.
  Ein bestehender Vault bekommt neue Felder deshalb **nicht** automatisch — die mitgelieferten
  Domänen werden nur einmalig gesät, danach gehört die Datei dem Nutzer.
- Dateien ohne `attributes`-Block bleiben gültig (leeres Mapping); es gibt keine Migration
  bestehender Vault-Dateien.
- Merkmale werden zusätzlich in der Cache-Zeile gespiegelt (wie die Aliase). Ohne das müsste
  die Personen-Liste für jeden Prozentwert eine Markdown-Datei öffnen. Der Prozentwert selbst
  wandert nicht in den Cache — er bleibt eine reine Ableitung.
