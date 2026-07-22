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

- [ ] `_build_user_prompt` (oder ein neuer Helper) erweitert: bei vorhandenem
      `media_links.persons`-Eintrag Captions + Tags der Fotos dieser Person laden (Query analog
      `assets.py` Zeile 616-633) und als eigenen Abschnitt an den Prompt anhängen.
- [ ] Deckelung/Aggregation festlegen. **Nicht raten** — prüfen, ob es für „häufigste Tags einer
      Personen-Foto-Menge" schon eine Query/Helper gibt (z.B. in `collections/engine.py` oder
      `collections/captions.py`), bevor eine neue geschrieben wird.
- [ ] Test: Person mit Fotos, deren Caption z.B. „am Strand in Portugal" lautet → Prompt enthält
      diesen Text. Person ganz ohne Fotos → Prompt unverändert wie heute.
- [ ] Prompt-Datei (`PromptLibrary`-Eintrag `_PROMPT_NAME`) ggf. anpassen, falls das
      System-Prompt-Wording auf die neue Abschnitts-Struktur eingehen soll — erst den
      bestehenden Prompt-Text lesen, nicht danebenschreiben.

### Docs

- [ ] `docs/routes.md` bzw. eine kurze ADR-Notiz: Vermerk, dass die KI-Ergänzung jetzt auch
      Captions/Tags als Quelle nutzt — Transparenz, falls später jemand nachfragt, woher ein
      Vorschlag stammt.

## Report-Back
