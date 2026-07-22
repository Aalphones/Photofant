/* Photofant — Wissen: personenbezogene Wissensbasis + Interview-/Web-Wizard (Klickdummy)
   Person↔Wissen-Verknüpfung: automatisch (Aufgaben-Queue, Wizard mit vorbelegter Person)
   + manuell (bestehende Notiz suchen & verknüpfen / Verknüpfung lösen) — Zustand lebt in App. */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useMemo } = React;
  const E = React.createElement;

  const OWNER_LABEL = { user: "Manuell", web: "Web", manual: "Manuell", inferred: "KI-Schätzung" };
  function OwnerPill({ owner }) {
    if (!owner) return E("span", { className: "kw-owner kw-owner-empty" }, "fehlt");
    return E("span", { className: "kw-owner kw-owner-" + owner }, OWNER_LABEL[owner] || owner);
  }

  function KRing({ pct, size = 64, children }) {
    return E("div", { className: "kw-ring", style: { width: size, height: size, "--pct": Math.round(pct * 100) } },
      E("div", { className: "kw-ring-gap" }, children));
  }

  function personAssets(assets, pid) {
    return assets.filter((a) => a.personId === pid || a.faces.some((f) => f.personId === pid));
  }

  function freshEntity(title, body) {
    return {
      id: "e" + Date.now() + Math.floor(Math.random() * 1000), title,
      domain: "Familie", completeness: 0.25, updated: new Date(),
      fields: Object.fromEntries(PF.KFIELD_DEFS.map((fd) => [fd.key, { value: null, owner: null, confidence: 0 }])),
      body: body || "Noch keine Details.", relationships: [], matchPersonId: null, matchConfidence: 0,
      sources: [{ label: "Interview · heute", kind: "interview" }],
    };
  }
  const FIELD_LABEL_KEY = { geburtstag: "geburtstag", beruf: "beruf", wohnort: "wohnort", vorlieben: "vorlieben", beziehungsstatus: "beziehung" };
  function applyFacts(entity, facts) {
    const fields = { ...entity.fields };
    const extras = [];
    facts.forEach((fct) => {
      const key = FIELD_LABEL_KEY[fct.field.toLowerCase()];
      if (key) fields[key] = { value: fct.value, owner: "web", confidence: fct.confidence };
      else extras.push(fct.field + ": " + fct.value + ".");
    });
    const filled = Object.values(fields).filter((v) => v.value).length;
    return {
      ...entity, fields,
      body: entity.body + (extras.length ? " " + extras.join(" ") : ""),
      completeness: Math.max(entity.completeness, filled / PF.KFIELD_DEFS.length),
      sources: [...entity.sources, ...facts.map((fct) => ({ label: fct.source, kind: "web" }))],
      updated: new Date(),
    };
  }

  /* ---------------- task queue ---------------- */
  const TASK_ICON = { missing_field: "info", low_completeness: "info", no_entity: "plus", suggestion: "sparkle", auto_link: "link" };
  function TaskChip({ task, onOpen, onDismiss }) {
    return E("div", { className: "kw-task-chip", onClick: onOpen },
      E("div", { className: "kw-task-ico" }, E(Icon, { name: TASK_ICON[task.kind] || "info", size: 14 })),
      E("div", { className: "kw-task-body" },
        E("div", { className: "kw-task-lbl" }, task.label),
        E("div", { className: "kw-task-sub" }, task.sub)),
      E("button", { className: "kw-task-x", title: "Verwerfen", onClick: (e) => { e.stopPropagation(); onDismiss(); } },
        E(Icon, { name: "x", size: 12 })));
  }

  /* ---------------- overview grid ---------------- */
  function KCard({ person, entity, onOpen }) {
    const pct = entity ? entity.completeness : 0;
    return E("button", { className: "kw-card", onClick: onOpen },
      E(KRing, { pct, size: 64 }, E(Avatar, { personId: person.id, size: 54 })),
      E("div", { className: "kw-card-name" }, person.name),
      entity
        ? E("div", { className: "kw-card-meta" }, Math.round(pct * 100) + "% · " + entity.domain)
        : E("div", { className: "kw-card-meta kw-card-empty" }, "Kein Wissen angelegt"));
  }

  /* ---------------- link pickers ---------------- */
  // Notiz → Person (manuell verknüpfen; auch aus dem Auto-Match-Task)
  function PersonLinkPicker({ entityTitle, suggestedPersonId, suggestedConfidence, onPick, onClose }) {
    const [q, setQ] = useState("");
    const ql = q.trim().toLowerCase();
    const dir = PF.DIRECTORY;
    const list = ql ? dir.filter((p) => p.name.toLowerCase().includes(ql)) : dir;
    return E("div", { className: "op-scrim", onClick: onClose },
      E("div", { className: "op-modal pp-modal", onClick: (e) => e.stopPropagation() },
        E("div", { className: "op-head" },
          E(Icon, { name: "link", size: 16 }),
          E("div", { style: { fontWeight: 600, fontSize: 14 } }, "„" + entityTitle + "“ verknüpfen"),
          E("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: onClose }, E(Icon, { name: "x", size: 14 }))),
        E("div", { className: "op-search" },
          E(Icon, { name: "search", size: 15 }),
          E("input", { autoFocus: true, value: q, placeholder: "Person suchen…", onChange: (e) => setQ(e.target.value) })),
        suggestedPersonId != null && !ql && E("div", { className: "pp-quick-wrap" },
          E("div", { className: "pp-sec-lbl" }, "Vorschlag"),
          E("div", { className: "pp-quick" },
            E("button", { className: "pp-chip", onClick: () => onPick(suggestedPersonId) },
              E(Avatar, { personId: suggestedPersonId, size: 44 }),
              E("div", { className: "pp-chip-name" }, PF.personName(suggestedPersonId)),
              E("span", { className: "score-pill high" }, Math.round(suggestedConfidence * 100) + "%")))),
        E("div", { className: "pp-list" },
          E("button", { className: "pp-row", onClick: () => onPick(null) },
            E("div", { className: "pp-row-av unknown" }, E(Icon, { name: "x", size: 16 })),
            E("div", { className: "pp-row-name" }, "Ohne Verknüpfung — eigenständige Notiz behalten")),
          list.map((p) => E("button", { key: p.id, className: "pp-row", onClick: () => onPick(p.id) },
            E(Avatar, { personId: p.id, size: 34 }),
            E("div", { className: "pp-row-name" }, p.name),
            p.count > 0 && E("span", { className: "pp-row-count" }, p.count + " Foto" + (p.count === 1 ? "" : "s")))))));
  }
  // Person → bestehende Notiz (aus dem leeren Profil-Zustand)
  function EntityLinkPicker({ unlinked, onPick }) {
    const [q, setQ] = useState("");
    const ql = q.trim().toLowerCase();
    const list = unlinked.filter((u) => !ql || u.title.toLowerCase().includes(ql));
    return E("div", { className: "op-scrim", onClick: () => onPick(null) },
      E("div", { className: "op-modal pp-modal", onClick: (e) => e.stopPropagation() },
        E("div", { className: "op-head" },
          E(Icon, { name: "link", size: 16 }),
          E("div", { style: { fontWeight: 600, fontSize: 14 } }, "Bestehende Notiz verknüpfen"),
          E("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: () => onPick(null) }, E(Icon, { name: "x", size: 14 }))),
        E("div", { className: "op-search" },
          E(Icon, { name: "search", size: 15 }),
          E("input", { autoFocus: true, value: q, placeholder: "Notiz suchen…", onChange: (e) => setQ(e.target.value) })),
        E("div", { className: "pp-list" },
          list.length === 0
            ? E("div", { className: "pp-empty" }, "Keine passende Notiz gefunden.")
            : list.map((u) => E("button", { key: u.id, className: "pp-row", onClick: () => onPick(u.id) },
                E("div", { className: "pp-row-av unknown" }, E(Icon, { name: "book", size: 16 })),
                E("div", { className: "pp-row-name" }, u.title),
                E("span", { className: "pp-row-count" }, Math.round(u.completeness * 100) + "%"))))));
  }

  /* ---------------- detail overlay ---------------- */
  function KDetail({ person, entity, assets, onClose, onOpenAsset, onStartInterview, onStartWebsearch, onLinkExisting, hasUnlinked, onUnlink }) {
    const [suggAccepted, setSuggAccepted] = useState(false);
    const [suggDismissed, setSuggDismissed] = useState(false);
    const [albumDone, setAlbumDone] = useState(false);
    const suggestion = PF.KNOWLEDGE_SUGGESTIONS[person.id];
    const pics = useMemo(() => personAssets(assets, person.id).slice(0, 12), [assets, person.id]);

    if (!entity) {
      return E("div", { className: "kw-scrim", onClick: onClose },
        E("div", { className: "kw-modal kw-modal-empty", onClick: (e) => e.stopPropagation() },
          E("button", { className: "edit-ibtn kw-modal-close", onClick: onClose }, E(Icon, { name: "x", size: 15 })),
          E(Avatar, { personId: person.id, size: 72 }),
          E("div", { style: { fontSize: 17, fontWeight: 700, marginTop: 14 } }, person.name),
          E("p", { className: "kw-empty-txt" }, "Noch kein Wissen zu " + person.name + " — starte ein privates Interview oder verknüpfe eine bestehende Notiz."),
          E("div", { style: { display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" } },
            E("button", { className: "pbtn primary", onClick: () => onStartInterview(person.id) },
              E(Icon, { name: "sparkle", size: 15 }), "Interview starten"),
            hasUnlinked && E("button", { className: "mini-btn", onClick: () => onLinkExisting(person.id) },
              E(Icon, { name: "link", size: 13 }), "Bestehende Notiz verknüpfen"))));
    }

    return E("div", { className: "kw-scrim", onClick: onClose },
      E("div", { className: "kw-modal", onClick: (e) => e.stopPropagation() },
        E("button", { className: "edit-ibtn kw-modal-close", onClick: onClose }, E(Icon, { name: "x", size: 15 })),
        E("div", { className: "kw-detail-head" },
          E(KRing, { pct: entity.completeness, size: 72 }, E(Avatar, { personId: person.id, size: 60 })),
          E("div", { style: { minWidth: 0 } },
            E("div", { className: "kw-detail-name" }, person.name),
            E("div", { className: "kw-detail-sub" },
              Math.round(entity.completeness * 100) + "% vollständig · " + entity.domain + " · aktualisiert " +
              entity.updated.toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" }))),
          E("div", { className: "kw-detail-actions" },
            E("button", { className: "mini-btn", onClick: () => onStartInterview(person.id) }, E(Icon, { name: "sparkle", size: 13 }), "Interview"),
            E("button", { className: "mini-btn", onClick: () => onStartWebsearch(person.id) }, E(Icon, { name: "globe", size: 13 }), "Web-Suche"),
            E("button", { className: "mini-btn", onClick: () => onUnlink(person.id) }, E(Icon, { name: "x", size: 13 }), "Verknüpfung lösen"))),

        suggestion && !suggDismissed && E("div", { className: "kw-ai-banner" + (suggAccepted ? " done" : "") },
          E(Icon, { name: "sparkle", size: 15 }),
          E("div", { className: "kw-ai-txt" },
            suggAccepted
              ? E("span", null, "Übernommen: ", E("b", null, suggestion.value))
              : E("span", null, suggestion.text)),
          !suggAccepted && E("div", { className: "kw-ai-acts" },
            E("button", { className: "mini-btn primary", onClick: () => setSuggAccepted(true) }, "Übernehmen"),
            E("button", { className: "mini-btn", onClick: () => setSuggDismissed(true) }, "Verwerfen"))),

        E("div", { className: "kw-detail-cols" },
          E("div", { className: "kw-detail-main" },
            E("div", { className: "panel-sec", style: { border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 16 } },
              E("div", { className: "psec-title" }, "Profil"),
              E("p", { className: "kw-bio" }, entity.body)),
            E("div", { className: "panel-sec", style: { border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 16, marginTop: 12 } },
              E("div", { className: "psec-title" }, "Merkmale"),
              E("div", { className: "kw-fields" },
                PF.KFIELD_DEFS.map((fd) => {
                  const v = entity.fields[fd.key];
                  return E("div", { className: "kw-field-row", key: fd.key },
                    E("div", { className: "kw-field-lbl" }, fd.label),
                    E("div", { className: "kw-field-val" }, v.value || E("span", { className: "kw-field-missing" }, "—")),
                    E(OwnerPill, { owner: v.owner }));
                }))),
            entity.relationships.length > 0 && E("div", { className: "panel-sec", style: { border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 16, marginTop: 12 } },
              E("div", { className: "psec-title" }, "Beziehungen"),
              E("div", { className: "kw-rel-row" },
                entity.relationships.map((r, i) => E("div", { className: "kw-rel-chip", key: i },
                  E(Avatar, { personId: r.targetPersonId, size: 28 }),
                  E("div", null,
                    E("div", { className: "kw-rel-name" }, PF.personName(r.targetPersonId)),
                    E("div", { className: "kw-rel-type" }, r.type)))))),
            E("div", { className: "panel-sec", style: { border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 16, marginTop: 12 } },
              E("div", { className: "psec-title" }, "Quellen"),
              entity.sources.map((s, i) => E("div", { className: "kw-source-row", key: i },
                E(Icon, { name: s.kind === "web" ? "globe" : s.kind === "interview" ? "sparkle" : "pencil", size: 13 }),
                s.label))),
            E("div", { className: "kw-album-sugg" },
              E(Icon, { name: "layers", size: 15 }),
              E("div", { className: "kw-ai-txt" },
                albumDone
                  ? "Album „Sommerurlaub 2025“ wurde angelegt."
                  : pics.length + " Fotos + Wissen deuten auf ein Album „Sommerurlaub 2025“ hin."),
              !albumDone && E("button", { className: "mini-btn primary", onClick: () => setAlbumDone(true) }, "Album vorschlagen"))),

          E("div", { className: "kw-detail-side" },
            E("div", { className: "psec-title" }, "Verknüpfte Fotos · " + pics.length),
            E("div", { className: "kw-photo-grid" },
              pics.map((a) => E("div", { className: "kw-photo-cell", key: a.id, onClick: () => onOpenAsset(a.id) },
                E(Img, { src: a.photo, bg: a.bg }))))))));
  }

  /* ---------------- Interview wizard ---------------- */
  function InterviewWizard({ presetPersonId, onClose, onSaved }) {
    const Q = PF.KNOWLEDGE_INTERVIEW_QUESTIONS;
    const [personId, setPersonId] = useState(presetPersonId != null ? presetPersonId : null);
    const [newName, setNewName] = useState("");
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState(Array(Q.length).fill(""));
    const name = personId != null ? PF.personName(personId) : newName.trim();
    const canAdvanceIntro = presetPersonId != null || personId != null || newName.trim().length > 0;

    const next = () => {
      if (step === Q.length) { setStep(step + 1); setTimeout(() => setStep(step + 2), 1100); return; }
      setStep(step + 1);
    };
    const back = () => setStep(Math.max(0, step - 1));
    const synthesis = "„" + name + "“ — aus den Interview-Antworten synthetisiertes Kurzprofil: " +
      (answers.filter(Boolean).join(" ") || "Bislang keine Details ergänzt.");

    let body;
    if (step === 0) {
      body = E("div", { className: "kw-iv-body" },
        presetPersonId != null && E("div", { className: "kw-iv-preset" },
          E(Avatar, { personId: presetPersonId, size: 40 }),
          E("div", null,
            E("div", { style: { fontSize: 13.5, fontWeight: 600 } }, "Interview mit " + name),
            E("div", { style: { fontSize: 11.5, color: "var(--text-3)" } }, Q.length + " kurze Fragen — leer lassen zum Überspringen."))),
        presetPersonId == null && E("div", { className: "kw-iv-pick" },
          E("div", { className: "pp-sec-lbl", style: { padding: "0 0 6px" } }, "Person wählen"),
          E("div", { className: "kw-iv-pick-row" },
            PF.PERSONS.map((p) => E("button", {
              key: p.id, className: "pp-chip" + (personId === p.id ? " sel" : ""),
              onClick: () => { setPersonId(p.id); setNewName(""); },
            }, E(Avatar, { personId: p.id, size: 40 }), E("div", { className: "pp-chip-name" }, p.name)))),
          E("div", { className: "kw-iv-or" }, "oder neue Person"),
          E("input", {
            className: "kw-iv-input", placeholder: "Name eingeben…", value: newName,
            onChange: (e) => { setNewName(e.target.value); setPersonId(null); },
          }),
          E("div", { style: { fontSize: 11, color: "var(--text-3)", marginTop: 8 } },
            "Kein Treffer? Die Notiz wird als eigenständiges Wissen gespeichert — später im Wissen-Tab verknüpfbar.")));
    } else if (step <= Q.length) {
      const qi = step - 1;
      body = E("div", { className: "kw-iv-body" },
        E("div", { className: "iv-progress-lbl" }, "Frage " + (qi + 1) + " von " + Q.length),
        E("label", { className: "kw-label" }, Q[qi]),
        E("textarea", {
          className: "kw-textarea", rows: 4, autoFocus: true, placeholder: "Deine Antwort (leer lassen zum Überspringen)…",
          value: answers[qi], onChange: (e) => { const a = [...answers]; a[qi] = e.target.value; setAnswers(a); },
        }));
    } else if (step === Q.length + 1) {
      body = E("div", { className: "kw-iv-body kw-iv-center" },
        E("div", { className: "spinner", style: { width: 26, height: 26, borderWidth: 3 } }),
        E("div", { style: { marginTop: 12, color: "var(--text-2)", fontSize: 13 } }, "Antworten werden zu einem Kurzprofil zusammengefasst…"));
    } else {
      body = E("div", { className: "kw-iv-body" },
        E("div", { className: "kw-summary-lbl" }, "Vorschlag für " + name),
        E("p", { className: "kw-bio" }, synthesis),
        E("div", { className: "kw-explain" }, E(Icon, { name: "info", size: 12 }),
          "Aus " + answers.filter(Boolean).length + " Antworten · Modell Gemma 3 12B · Prompt v3 · Konfidenz 88%"));
    }

    const isSummary = step === Q.length + 2;
    const isSynth = step === Q.length + 1;
    return E("div", { className: "kw-scrim", onClick: onClose },
      E("div", { className: "kw-wiz", onClick: (e) => e.stopPropagation() },
        E("div", { className: "op-head" },
          E(Icon, { name: "sparkle", size: 16 }),
          E("div", { style: { fontWeight: 600, fontSize: 14 } }, "Privates Interview"),
          E("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: onClose }, E(Icon, { name: "x", size: 14 }))),
        body,
        !isSynth && E("div", { className: "kw-wiz-foot" },
          isSummary
            ? E(React.Fragment, null,
                E("button", { className: "mini-btn", onClick: () => setStep(1) }, E(Icon, { name: "chevronDown", size: 13, style: { transform: "rotate(180deg)" } }), "Antworten anpassen"),
                E("button", { className: "mini-btn primary", onClick: () => { onSaved(name, personId, synthesis); onClose(); } }, E(Icon, { name: "check", size: 13 }), "Übernehmen"))
            : E(React.Fragment, null,
                step > 0 && E("button", { className: "mini-btn", onClick: back }, "Zurück"),
                step === 0 && E("div", null),
                E("button", { className: "mini-btn primary", disabled: step === 0 && !canAdvanceIntro, onClick: next },
                  step === Q.length ? "Zusammenfassen" : "Weiter")))));
  }

  /* ---------------- Websearch wizard ---------------- */
  function WebsearchWizard({ presetPersonId, onClose, onSaved }) {
    const [personId, setPersonId] = useState(presetPersonId != null ? presetPersonId : null);
    const [hints, setHints] = useState("");
    const [step, setStep] = useState(0);
    const [checked, setChecked] = useState(() => PF.KNOWLEDGE_WEB_FACTS.map(() => true));
    const name = personId != null ? PF.personName(personId) : "";
    const start = () => { setStep(1); setTimeout(() => setStep(2), 1000); };
    const toggle = (i) => setChecked((c) => c.map((v, j) => j === i ? !v : v));
    const acceptedN = checked.filter(Boolean).length;

    let body;
    if (step === 0) {
      body = E("div", { className: "kw-iv-body" },
        presetPersonId != null && E("div", { className: "kw-iv-preset" },
          E(Avatar, { personId: presetPersonId, size: 40 }),
          E("div", null,
            E("div", { style: { fontSize: 13.5, fontWeight: 600 } }, "Web-Suche für " + name),
            E("div", { style: { fontSize: 11.5, color: "var(--text-3)" } }, "Gemma schlägt öffentlich auffindbare Fakten zur Bestätigung vor."))),
        presetPersonId == null && E("div", { className: "kw-iv-pick" },
          E("div", { className: "pp-sec-lbl", style: { padding: "0 0 6px" } }, "Person wählen"),
          E("div", { className: "kw-iv-pick-row" },
            PF.PERSONS.map((p) => E("button", {
              key: p.id, className: "pp-chip" + (personId === p.id ? " sel" : ""), onClick: () => setPersonId(p.id),
            }, E(Avatar, { personId: p.id, size: 40 }), E("div", { className: "pp-chip-name" }, p.name))))),
        E("label", { className: "kw-label" }, "Hinweise (Links, Beruf, Stadt …) — optional"),
        E("textarea", { className: "kw-textarea", rows: 3, placeholder: "z.B. instagram.com/…", value: hints, onChange: (e) => setHints(e.target.value) }));
    } else if (step === 1) {
      body = E("div", { className: "kw-iv-body kw-iv-center" },
        E("div", { className: "spinner", style: { width: 26, height: 26, borderWidth: 3 } }),
        E("div", { style: { marginTop: 12, color: "var(--text-2)", fontSize: 13 } }, "Gemma durchsucht öffentliche Quellen für " + name + "…"));
    } else {
      body = E("div", { className: "kw-iv-body" },
        E("div", { className: "kw-summary-lbl" }, "Gefundene Fakten — zur Bestätigung"),
        PF.KNOWLEDGE_WEB_FACTS.map((fct, i) => E("label", { className: "kw-fact-row", key: i },
          E("input", { type: "checkbox", checked: checked[i], onChange: () => toggle(i) }),
          E("div", { className: "kw-fact-body" },
            E("div", { className: "kw-fact-field" }, fct.field),
            E("div", { className: "kw-fact-val" }, fct.value)),
          E("span", { className: "kw-fact-src" }, fct.source),
          E("span", { className: "score-pill " + (fct.confidence >= 0.75 ? "high" : "mid") }, Math.round(fct.confidence * 100) + "%"))));
    }
    return E("div", { className: "kw-scrim", onClick: onClose },
      E("div", { className: "kw-wiz", onClick: (e) => e.stopPropagation() },
        E("div", { className: "op-head" },
          E(Icon, { name: "globe", size: 16 }),
          E("div", { style: { fontWeight: 600, fontSize: 14 } }, "Wissen per Web-Suche ergänzen"),
          E("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: onClose }, E(Icon, { name: "x", size: 14 }))),
        body,
        step !== 1 && E("div", { className: "kw-wiz-foot" },
          step === 0
            ? E(React.Fragment, null, E("div", null), E("button", { className: "mini-btn primary", disabled: !name, onClick: start }, E(Icon, { name: "search", size: 13 }), "Suchen"))
            : E(React.Fragment, null,
                E("button", { className: "mini-btn", onClick: () => setStep(0) }, "Zurück"),
                E("button", {
                  className: "mini-btn primary", disabled: acceptedN === 0,
                  onClick: () => { onSaved(name, personId, PF.KNOWLEDGE_WEB_FACTS.filter((_, i) => checked[i])); onClose(); },
                }, E(Icon, { name: "check", size: 13 }), acceptedN + " Fakten übernehmen")))));
  }

  /* ---------------- page ---------------- */
  function Knowledge({ assets, focusPersonId, onOpenAsset, onConsumeFocus, linkOverrides, setLinkOverrides, unlinked, setUnlinked }) {
    const [openId, setOpenId] = useState(focusPersonId != null ? focusPersonId : null);
    if (focusPersonId != null && openId !== focusPersonId) { setOpenId(focusPersonId); }
    const [dismissed, setDismissed] = useState(() => new Set());
    const [wizard, setWizard] = useState(null);
    const [toast, setToast] = useState(null);
    const [pendingLink, setPendingLink] = useState(null); // { entity, taskId }
    const [pendingEntityLink, setPendingEntityLink] = useState(null); // personId

    const entityFor = (pid) => Object.prototype.hasOwnProperty.call(linkOverrides, pid) ? linkOverrides[pid] : PF.KNOWLEDGE[pid];
    const notify = (msg) => { setToast(msg); setTimeout(() => setToast(null), 2800); };

    const close = () => { setOpenId(null); onConsumeFocus && onConsumeFocus(); };
    const tasks = PF.KNOWLEDGE_TASKS.filter((t) => !dismissed.has(t.id));
    const openPerson = PF.PERSONS.find((p) => p.id === openId);
    const openEntity = openId != null ? entityFor(openId) : null;

    const openTaskTarget = (t) => {
      if (t.kind === "no_entity") { setWizard({ kind: "interview", personId: t.personId }); return; }
      if (t.kind === "auto_link") { const ent = unlinked.find((u) => u.id === t.entityId); if (ent) setPendingLink({ entity: ent, taskId: t.id }); return; }
      setOpenId(t.personId);
    };

    const resolvePersonLink = (personId) => {
      const entity = pendingLink.entity;
      if (personId != null) {
        setLinkOverrides((prev) => ({ ...prev, [personId]: { ...entity, updated: new Date() } }));
        setUnlinked((list) => list.filter((u) => u.id !== entity.id));
        notify("„" + entity.title + "“ mit " + PF.personName(personId) + " verknüpft.");
      } else {
        notify("„" + entity.title + "“ bleibt eigenständige Notiz.");
      }
      if (pendingLink.taskId != null) setDismissed((s) => new Set([...s, pendingLink.taskId]));
      setPendingLink(null);
    };
    const resolveEntityLink = (entityId) => {
      const personId = pendingEntityLink;
      setPendingEntityLink(null);
      if (entityId == null) return;
      const entity = unlinked.find((u) => u.id === entityId);
      if (!entity) return;
      setLinkOverrides((prev) => ({ ...prev, [personId]: { ...entity, updated: new Date() } }));
      setUnlinked((list) => list.filter((u) => u.id !== entityId));
      notify("„" + entity.title + "“ mit " + PF.personName(personId) + " verknüpft.");
    };
    const onUnlink = (personId) => {
      const entity = entityFor(personId);
      if (!entity) return;
      setUnlinked((list) => [...list, { ...entity, id: entity.id || ("e" + personId + Date.now()) }]);
      setLinkOverrides((prev) => ({ ...prev, [personId]: null }));
      notify("Verknüpfung zu " + PF.personName(personId) + " gelöst — Notiz bleibt erhalten.");
    };

    const onInterviewSaved = (name, personId, bioText) => {
      if (personId != null) {
        setLinkOverrides((prev) => {
          const cur = Object.prototype.hasOwnProperty.call(prev, personId) ? prev[personId] : PF.KNOWLEDGE[personId];
          const base = cur || freshEntity(name, "");
          return { ...prev, [personId]: { ...base, body: bioText, updated: new Date(), sources: [...base.sources, { label: "Interview · heute", kind: "interview" }] } };
        });
        notify(name + " — Kurzprofil übernommen.");
      } else {
        setUnlinked((list) => [...list, freshEntity(name, bioText)]);
        notify("„" + name + "“ als eigenständige Notiz gespeichert — noch nicht verknüpft.");
      }
    };
    const onWebsearchSaved = (name, personId, facts) => {
      if (personId != null) {
        setLinkOverrides((prev) => {
          const cur = Object.prototype.hasOwnProperty.call(prev, personId) ? prev[personId] : PF.KNOWLEDGE[personId];
          const base = cur || freshEntity(name, "");
          return { ...prev, [personId]: applyFacts(base, facts) };
        });
      } else {
        setUnlinked((list) => [...list, applyFacts(freshEntity(name, ""), facts)]);
      }
      notify(facts.length + " Fakten für " + name + (personId != null ? " übernommen." : " als Notiz gespeichert — noch nicht verknüpft."));
    };

    return E("div", { className: "kw-wrap" },
      E("div", { className: "kw-head" },
        E("div", null,
          E("h2", { className: "kw-title" }, "Wissen"),
          E("p", { className: "kw-sub" }, "Wissen über die Menschen in deiner Sammlung — Grundlage für bessere Captions, Suche und Vorschläge.")),
        E("div", { className: "kw-head-actions" },
          E("button", { className: "kw-btn", onClick: () => setWizard({ kind: "interview", personId: null }) },
            E(Icon, { name: "sparkle", size: 15 }), "Privates Interview"),
          E("button", { className: "kw-btn", onClick: () => setWizard({ kind: "websearch", personId: null }) },
            E(Icon, { name: "globe", size: 15 }), "Web-Suche"))),

      toast && E("div", { className: "kw-toast" }, E(Icon, { name: "check", size: 14 }), toast),

      tasks.length > 0 && E("div", { className: "kw-tasks" },
        E("div", { className: "kw-tasks-lbl" }, "Offene Aufgaben · " + tasks.length),
        E("div", { className: "kw-task-row" },
          tasks.map((t) => E(TaskChip, {
            key: t.id, task: t, onOpen: () => openTaskTarget(t),
            onDismiss: () => setDismissed((s) => new Set([...s, t.id])),
          })))),

      E("div", { className: "kw-grid" },
        PF.PERSONS.map((p) => E(KCard, { key: p.id, person: p, entity: entityFor(p.id), onOpen: () => setOpenId(p.id) }))),

      unlinked.length > 0 && E("div", { className: "kw-tasks", style: { marginTop: 26 } },
        E("div", { className: "kw-tasks-lbl" }, "Nicht verknüpfte Notizen · " + unlinked.length),
        E("div", { className: "kw-unlinked-grid" },
          unlinked.map((u) => E("div", { className: "kw-unlinked-card", key: u.id },
            E("div", { className: "kw-unlinked-ico" }, E(Icon, { name: "book", size: 16 })),
            E("div", { className: "kw-unlinked-body" },
              E("div", { className: "kw-unlinked-title" }, u.title),
              E("div", { className: "kw-unlinked-meta" }, Math.round(u.completeness * 100) + "% · " + u.domain)),
            E("button", { className: "mini-btn primary", onClick: () => setPendingLink({ entity: u, taskId: null }) },
              E(Icon, { name: "link", size: 12 }), "Verknüpfen"))))),

      openPerson && E(KDetail, {
        person: openPerson, entity: openEntity, assets, onClose: close,
        onOpenAsset: (id) => { close(); onOpenAsset(id); },
        onStartInterview: (pid) => setWizard({ kind: "interview", personId: pid }),
        onStartWebsearch: (pid) => setWizard({ kind: "websearch", personId: pid }),
        onLinkExisting: (pid) => setPendingEntityLink(pid),
        hasUnlinked: unlinked.length > 0,
        onUnlink,
      }),

      pendingLink && E(PersonLinkPicker, {
        entityTitle: pendingLink.entity.title, suggestedPersonId: pendingLink.entity.matchPersonId,
        suggestedConfidence: pendingLink.entity.matchConfidence, onPick: resolvePersonLink, onClose: () => setPendingLink(null),
      }),
      pendingEntityLink != null && E(EntityLinkPicker, { unlinked, onPick: resolveEntityLink }),

      wizard && wizard.kind === "interview" && E(InterviewWizard, { presetPersonId: wizard.personId, onClose: () => setWizard(null), onSaved: onInterviewSaved }),
      wizard && wizard.kind === "websearch" && E(WebsearchWizard, { presetPersonId: wizard.personId, onClose: () => setWizard(null), onSaved: onWebsearchSaved }));
  }

  window.Knowledge = Knowledge;
})();
