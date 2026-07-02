# FINDINGS — P11 Duale Duplikaterkennung

Format: `- [ ] → Phase N: <Erkenntnis / Abweichung / Folgefund>`

<!-- Einträge werden während der Umsetzung von mode-implementing eingepflegt -->

- [ ] → Phase 3: Phase 2 hat `DupePairDto.phash_distance` bereits auf `int | None` gestellt (sonst crasht `/review/dupes` bei reinen CLIP-Paaren mit 500). Phase 3 baut darauf die volle Kontrakt-Form (`clip_distance`, `phash_similarity_pct`, `clip_similarity_pct`, `triggered_by`) — die Nullable-Änderung an `phash_distance` nicht nochmal machen, nur ergänzen.
