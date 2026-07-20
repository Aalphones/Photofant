# FINDINGS — P27 Gemma-Integration

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

- [x] Phase 1: **ADR-Nummern korrigiert** — Plan reservierte 013/014, beide belegt. Real
  angelegt als **027** (AI-Layer) + **028** (Gemma-Runtime). README + code-map nachgezogen.
- [x] Phase 1 (Chesterton): **`load_transformers_model` lud immer einen `AutoProcessor`** —
  ein Multimodal-Konzept, das ein reines Text-LM (Gemma) nicht hat. Additiver
  `load_processor`-Schalter (Default `True`, Captioner unberührt); `False` lädt `AutoTokenizer`.
- [ ] → Phase 2/3: **Explainability-Confidence ist bei roher Textgenerierung `None`**
  (`GenerationResult.confidence`). Import-/Update-Job muss eine **Patch-Confidence** selbst
  ableiten und in die Payload + den Changelog-Eintrag (P25-Pfad) schreiben.
- [x] → Phase 2/3/4: **Schreibpfad steht** — `ToolRegistry(service, owner)` + der Service-
  Trockenlauf `validate_patch()`. Jobs: KI-Vorschlag → `ValidatePatch` (zeigen) → Nutzer-Go →
  `PatchEntity`/P25-`KnowledgePatchJob` mit passendem `owner` (Autonomie → `inferred`/`web`,
  nie `user`). `autonomy_for(capability)` liefert `off|ask|auto` fürs Gating. → Phase 4: der
  Interview-Vorschlag ist Nutzer-Wissen, deshalb `owner=user` über den normalen `create_entity`-
  Pfad (kein `PatchEntity`); Validierung via `validate_entity`-Trockenlauf im Job.
- [x] → Phase 4: **`INTERVIEW` hat in der Tool-Registry bewusst kein Such-/Lese-Tool**
  (`_CAPABILITY_TOOLS`) — private Personen nicht mit Bestand/Web vermischen (ADR-009). Beim
  Bauen des Interview-Flows nicht nachträglich Tools freischalten. → eingehalten: der
  `InterviewJob` ruft nur `generate()` (kein Tool-Routing), Gemma sieht nur die Antworten.
- [x] → Phase 2/3/4 (Kontrakt-Abweichung, minor): `ai.promptLibraryPath`-Default ist **leer =
  mitgelieferte Prompts** (`inference/prompts/*.md`), nicht `<vault>/prompts`. Offline-tauglich
  ohne Seeding; der Nutzer kann per Pfad auf einen eigenen Ordner umbiegen.
- [x] → Phase 2/3/4: **`ai.idleTimeoutSeconds` steuert den ganzen Generativ-Slot** (Gemma
  *und* Captioner — genau ein Modell resident), nicht Gemma allein (ADR-028). Kein Per-Modell-
  Timeout; falls je nötig, isolierter Folge-Schritt. → Phase 4 nutzt denselben Slot, keine
  Änderung nötig.
- [x] Phase 2: **KI-Vorschlag reist über den Job-Stream** (mit User entschieden). Neu:
  `JobStatus.result`/`job_queue.set_result` + `JobDto.result` + Frontend `Job.result`
  (generisch `Record<string,unknown>`). Der Job setzt sein Ergebnis vor dem DONE-Update;
  ein Store-Effekt (`correlateSuggestionJob$`) fischt genau den erwarteten `job_id` aus dem
  Strom aller Job-Updates und wandelt done/error in ein Vorschlags-Ergebnis um. **Phase 3/4
  erben diesen Kanal** — kein neuer Endpunkt nötig, nur ein eigener Ergebnis-Typ + Job-Kind.
- [x] → Phase 3/4: **Autonomie-Gate-Muster steht** — `api/knowledge_ai.py` mit
  `GET /knowledge/ai/autonomy` (Frontend blendet Aktionen bei `off` aus) + der jeweiligen
  Auslöse-Route, die zusätzlich serverseitig `autonomy_for(...) == "off"` → 409 prüft. Phase 3
  (Update) hängt sich an dieselbe Autonomie-Abfrage (`knowledge_update`), Phase 4 an `interview`.
  → Phase 4: `/interview`-Route 409 bei `off`, Button ausgeblendet über `interviewAutonomy`.
- [x] → Phase 3/4: **Import füllt nur die Beschreibung** (Gemma-Absatz); Aliase/Beziehungen
  bleiben leer im Vorschlag. Ein rohes Text-LM liefert dafür nichts Verlässliches. Wenn Phase 3
  reichere Vorschläge will, den **Prompt** dafür bauen (strukturierte Ausgabe), nicht die
  Feld-Ableitung im Job hart verdrahten — der Suggestion-Typ trägt die Felder bereits. → Phase 4
  hält dieselbe Grenze: der Interview-Vorschlag füllt nur den Body, Aliase/Beziehungen leer.
