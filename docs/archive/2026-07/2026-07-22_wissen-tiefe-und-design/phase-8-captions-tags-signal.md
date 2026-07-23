# Phase 8 — Captions/Tags als Signal für die KI-Ergänzung

**Rating:** standard

Zweiter Fund aus derselben Prüfung wie Phase 7: Der bestehende KI-Ergänzungsvorschlag
(`knowledge_update_job`) baut seinen Prompt ausschließlich aus der aktuellen `body`-Beschreibung
der Entity — Captions und Tags der Fotos dieser Person fließen nirgends ein, obwohl das
Foto-System (Captioning/Tagging) längst existiert. Das trifft besonders die **private** Domäne:
dort läuft nie eine Web-Recherche (ADR-009 — private Domänen gehen nie ins Netz), Captions/Tags
sind für eine private Person also der einzige organische Zusatz-Hinweis, der automatisch
verfügbar wäre.

**Entscheidung:** Kein neuer Auslöser, keine neue Autonomie-Stufe — dieselbe Opt-in-Aktion wie
heute (Banner-Klick aus Phase 6 Teil B) bekommt lediglich mehr Kontext im Prompt. Der bestehende
Owner-Schutz (ein von Hand gepflegtes Merkmal wird nie überschrieben) gilt unverändert weiter;
Captions/Tags sind nur ein zusätzlicher Hinweis für Gemma, kein Beleg — dieselbe Vorsicht wie
beim Halluzinations-Risiko in der README (ADR-034).

## Kontext — das musst du lesen

- `backend/photofant/jobs/knowledge_update_job.py` → `_build_user_prompt` (Zeile 41) — hier
  hängt der neue Abschnitt an.
- `backend/photofant/db/models.py` → `Asset.caption` (Zeile 55), `Tag`/`AssetTag`
  (Zeile 126, 134).
- `backend/photofant/api/assets.py` Zeile 616-633 — dasselbe Muster wie in Phase 7 für „Fotos
  dieser Person", hier als Quelle für Captions/Tags statt Thumbnails.
- `backend/photofant/knowledge/service.py` → `media_links`/`get_lore`, um an die verlinkte
  Person-ID der Entity zu kommen.
- README dieses Plans, Abschnitt „Kritisch gegenlesen" (Halluzinations-Risiko, ADR-034) — gleiche
  Grundhaltung gilt hier.

## AK dieser Phase

1. Ist die Wissens-Entity mit einer Person verknüpft, bezieht der KI-Ergänzungsvorschlag
   (derselbe Opt-in-Banner wie heute, kein neuer Auslöser) zusätzlich zur bestehenden
   Beschreibung eine kompakte Zusammenfassung aus Captions und den häufigsten Tags der Fotos
   dieser Person mit ein.
2. Ohne Personen-Verknüpfung (reine Notiz) ändert sich nichts — es gibt keine Fotos, aus denen
   sich etwas ableiten ließe.
3. Die Zusammenfassung ist gedeckelt (z.B. die letzten N Captions + die Top-M Tags nach
   Häufigkeit), damit der Prompt nicht durch hunderte Fotos aufgebläht wird.
4. Der bestehende Owner-Schutz bleibt unverändert: der Vorschlag überschreibt nie ein von Hand
   gepflegtes Merkmal und wird weiterhin erst nach „Übernehmen" gespeichert.
5. `cd backend && uv run ruff check .` grün. Frontend ändert sich hier vermutlich gar nicht
   (reine Backend-Prompt-Erweiterung) — falls doch, `npm run lint && npm run build` zusätzlich.

## Checkliste

### Backend

- [x] `_build_user_prompt` erweitert: neuer Parameter `photo_signal`, gefüllt von
      `_photo_signal_section()` — bei vorhandenem `media_links.persons`-Eintrag Captions + Tags
      der erkannten Fotos dieser Person laden (`_recognized_photo_asset_ids`, eigene Query statt
      Import aus `api/knowledge.py` — Jobs importieren nicht aus der API-Schicht) und als eigenen
      Abschnitt an den Prompt anhängen.
- [x] Deckelung/Aggregation festgelegt: `_MAX_PHOTO_CAPTIONS = 8` (neueste zuerst), `_MAX_PHOTO_TAGS
      = 12` (häufigste zuerst, `manually_removed` ausgeschlossen). Keine bestehende Helper-Query
      für „häufigste Tags einer Foto-Menge" gefunden (`collections/engine.py`, `captions.py`,
      `stats.py` geprüft — dort nur `Counter` für Framing/Bucket-Stats, nichts Wiederverwendbares)
      — Startwert, kein Messwert; FINDINGS falls zu klein/groß.
- [x] Test: Person mit Fotos (Caption „am Strand in Portugal", Tag „strand") → Prompt enthält
      beides. Entity ganz ohne Personen-Verknüpfung → Prompt unverändert (kein Foto-Abschnitt).
- [x] Prompt-Datei (`knowledge_update.md`) angepasst: neue Regel „Captions/Tags sind Hinweise,
      keine bestätigten Fakten" (gleiche Vorsicht wie ADR-034), Version 1 → 2.

### Docs

- [x] `docs/routes.md` beim `knowledge_update`-Ergebnis ergänzt: Captions/Tags fließen bei
      Personen-Verknüpfung als Hinweis in den Prompt ein, kein neues Feld/keine neue DTO.

## Report-Back

Nur Backend geändert — reine Prompt-Erweiterung, keine Schnittstelle betroffen. Frontend bleibt
unverändert (README-Vermutung bestätigt). `_recognized_photo_asset_ids` nutzt bewusst nur
`media_links.persons` (nicht zusätzlich `media_links.assets`), damit AK 2 exakt gilt: manuell
verknüpfte, aber nicht personen-zugeordnete Assets liefern kein Foto-Signal. Zwei neue Tests in
`test_knowledge_update_job.py` decken AK 1/2/3 ab. `uv run ruff check .` und `uv run mypy
photofant/jobs/knowledge_update_job.py` grün für die geänderte Datei; volle Testsuite läuft.
