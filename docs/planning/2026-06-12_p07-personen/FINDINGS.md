# FINDINGS — P7 Personen & Faces

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [ ] → Phase 5: Review-Queue für Face-Zuordnung: Die Score-Band-Logik in Phase 2 erkennt "review"-Fälle (0.45–0.6 Cosine), loggt sie aber nur. Phase 5 muss `review_item` mit `type='face_suggestion'` anlegen (analog `dupe_candidate`) und die UI dafür bauen. Die `clustering_job.run_incremental_match` ist der Integrationspunkt — dort den ReviewItem-Insert ergänzen.
- [x] → Phase 3: Person-Ordner müssen nach dem Clustering für die neu erstellten Personen angelegt werden (HDBSCAN erstellt nur DB-Zeilen, keine Ordner). Die physische Ordner-Erstellung + Datei-Moves passieren in Phase 3. → Umgesetzt: `materialize_clustering_results()` in `person_folders.py`.
- [ ] → Phase 4: `GET /api/persons` muss die Face-Counts pro Person liefern — nach dem Clustering existieren die Person-Zeilen, aber die Personen-View braucht aggregierte Daten (Count, Portrait-Face).
