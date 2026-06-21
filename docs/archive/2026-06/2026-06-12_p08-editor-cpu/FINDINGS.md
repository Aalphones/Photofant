# FINDINGS — P8 Editor CPU

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [x] → Phase 4: **Crop-Personen-Abgleich** — Der Save-Endpoint hängt die Version an die editierte `asset_instance` (oder `face`). Dadurch ist der Crop-Sonderfall §8.2a natürlich gekapselt: die Version gehört nur der Person, deren Instanz editiert wurde. Eine aktive Face-Detection auf dem Crop-Ergebnis (um zu prüfen, welche Personen rausgefallen sind) wird erst relevant, wenn Versionen repliziert werden sollen (Edit automatisch für alle beteiligten Personen anlegen). Aktuell: keine Replikation, keine zusätzliche Detection nötig.
- [x] → Phase 5: **Version-Replikation & Crop-Sonderfall**: Soll ein gespeicherter Edit automatisch als Version bei allen am Bild beteiligten Personen erscheinen (nicht nur der editierten), muss beim Save Face-Detection auf dem Ergebnis laufen und nur Personen, die noch im Bild sind, bekommen die Version. Die Infrastruktur dafür (Konzept §8.2a) ist gekapselt in `_resolve_save_context`, Erweiterungspunkt klar.
