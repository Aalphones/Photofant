/* Photofant — Alben: EIN Album-Typ. Jedes Album kann per Zahnrad auf
   automatische Befüllung (Smart, trigger-basiert) umgeschaltet werden — wie bei Google Fotos. */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useMemo, useRef, useEffect } = React;

  /* ---------- helpers ---------- */
  const triggerLabel = (t) => t.type === "person" ? PF.personName(t.personId) : t.type === "tag" ? t.tagName : "\u201E" + t.phrase + "\u201C";
  const triggerIcon = (t) => t.type === "person" ? "face" : t.type === "tag" ? "tag" : "text";
  const triggerKind = (t) => ({ person: "Person", tag: "Tag", caption: "Caption" }[t.type]);
  const sameTrigger = (a, b) => a.type === b.type && a.personId === b.personId && a.tagName === b.tagName && a.phrase === b.phrase;
  const lookup = (assets, ids) => ids.map((id) => assets.find((a) => a.id === id)).filter(Boolean);
  // overview-card members (uses the album's stored smart state)
  const cardMembers = (col, assets) => col.smart && col.smart.on
    ? PF.matchTriggers(assets, col.smart.triggers, col.smart.mode)
    : lookup(assets, col.memberIds);

  /* ---------- auto cover (collage from member photos) ---------- */
  function AlbumCover({ photos }) {
    const ps = photos.slice(0, 4);
    if (ps.length === 0)
      return React.createElement("div", { className: "album-cover empty" }, React.createElement(Icon, { name: "album", size: 28, style: { color: "var(--text-3)" } }));
    if (ps.length < 4)
      return React.createElement("div", { className: "album-cover one" }, React.createElement(Img, { src: ps[0] }));
    return React.createElement("div", { className: "album-cover quad" },
      ps.map((p, i) => React.createElement("div", { className: "qc", key: i }, React.createElement(Img, { src: p }))));
  }

  /* ---------- overview card ---------- */
  function AlbumCard({ col, assets, onOpen }) {
    const members = cardMembers(col, assets);
    const smart = col.smart && col.smart.on;
    return React.createElement("button", { className: "album-card", onClick: () => onOpen(col.id) },
      React.createElement(AlbumCover, { photos: members.map((m) => m.photo) }),
      smart && React.createElement("span", { className: "smart-tag" }, React.createElement(Icon, { name: "sparkle", size: 11 }), "Auto"),
      React.createElement("div", { className: "album-info" },
        React.createElement("div", { className: "album-name" }, col.name),
        React.createElement("div", { className: "album-sub" },
          React.createElement("span", { className: "mono" }, members.length + (members.length === 1 ? " Bild" : " Bilder")),
          React.createElement("span", { className: "dotsep" }, "\u00B7"),
          React.createElement("span", { className: smart ? "auto-fill" : "" }, smart ? "automatisch" : "manuell")),
        smart && React.createElement("div", { className: "trig-summary" },
          col.smart.triggers.slice(0, 3).map((t, i) => React.createElement("span", { className: "trig-mini" + (t.negate ? " neg" : ""), key: i },
            React.createElement(Icon, { name: triggerIcon(t), size: 10 }), triggerLabel(t))))));
  }

  /* ---------- overview (single, unified list) ---------- */
  function Overview({ assets, onOpen }) {
    return React.createElement("div", { className: "grid-wrap albums-wrap" },
      React.createElement("div", { className: "alb-sec-head" },
        React.createElement(Icon, { name: "album", size: 16, style: { color: "var(--text-2)" } }),
        React.createElement("h3", null, "Alben"),
        React.createElement("span", { className: "m-count" }, PF.COLLECTIONS.length),
        React.createElement("div", { className: "m-line" }),
        React.createElement("span", { className: "alb-note" }, "Manuell oder \u2014 per Zahnrad \u2014 automatisch bef\u00FCllt")),
      React.createElement("div", { className: "albums-grid" },
        PF.COLLECTIONS.map((c) => React.createElement(AlbumCard, { key: c.id, col: c, assets, onOpen })),
        React.createElement("button", { className: "album-card new" },
          React.createElement("div", { className: "album-cover new" }, React.createElement(Icon, { name: "plus", size: 24 })),
          React.createElement("div", { className: "album-info" },
            React.createElement("div", { className: "album-name" }, "Neues Album"),
            React.createElement("div", { className: "album-sub" }, "Leer \u2014 sp\u00E4ter smart schaltbar")))),
      React.createElement("div", { style: { height: 40 } }));
  }

  /* ---------- justified tile ---------- */
  function Tile({ a, base, st, onOpen, onFav }) {
    const up = a.versions.some((v) => v.type === "upscale" && v.current);
    return React.createElement("div", {
      className: "cell atile" + (st === "in" ? " at-in" : st === "out" ? " at-out" : ""),
      style: { height: base, flexGrow: a.ar.w / a.ar.h, flexBasis: (a.ar.w / a.ar.h) * base + "px" },
      onClick: () => st !== "out" && onOpen(a.id),
    },
      React.createElement("div", { className: "img" }, React.createElement(Img, { src: a.photo, bg: a.bg })),
      React.createElement("div", { className: "veil" }),
      React.createElement("button", { className: "fav" + (a.favourite ? " on" : ""), onClick: (e) => { e.stopPropagation(); onFav(a.id); } },
        React.createElement(Icon, { name: "star", size: 16, fill: a.favourite })),
      React.createElement("div", { className: "meta-bl" },
        a.source !== "original" && React.createElement("span", { className: "badge " + a.source }, PF.sourceLabel(a.source)),
        up && React.createElement("span", { className: "badge up" }, "2\u00D7")),
      st === "in" && React.createElement("span", { className: "tile-flag in" }, React.createElement(Icon, { name: "plus", size: 11, stroke: 3 }), "kommt rein"),
      st === "out" && React.createElement("div", { className: "tile-out-veil" },
        React.createElement("span", { className: "tile-flag out" }, React.createElement(Icon, { name: "minus", size: 11, stroke: 3 }), "f\u00E4llt raus")));
  }

  function justified(items, base, render) {
    return React.createElement("div", { className: "grid", style: { display: "flex", flexWrap: "wrap" } },
      items.map(render),
      React.createElement("div", { style: { flexGrow: 10, flexBasis: 0 } }));
  }

  /* ---------- small toggle switch ---------- */
  function Switch({ on, onClick }) {
    return React.createElement("button", { className: "switch" + (on ? " on" : ""), onClick, role: "switch", "aria-checked": on },
      React.createElement("span", { className: "knob" }));
  }

  /* ---------- add-trigger picker ---------- */
  function AddTrigger({ assets, triggers, onAdd, onClose }) {
    const [tab, setTab] = useState("person");
    const [tagQ, setTagQ] = useState("");
    const [phrase, setPhrase] = useState("");
    const countFor = (t) => assets.filter((a) => PF.evalTrigger(a, t)).length;

    return React.createElement("div", { className: "add-trig" },
      React.createElement("div", { className: "at-tabs" },
        [["person", "Person", "face"], ["tag", "Tag", "tag"], ["caption", "Caption", "text"]].map(([k, l, ic]) =>
          React.createElement("button", { key: k, className: "at-tab" + (tab === k ? " on" : ""), onClick: () => setTab(k) },
            React.createElement(Icon, { name: ic, size: 13 }), l)),
        React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28, marginLeft: "auto" }, onClick: onClose },
          React.createElement(Icon, { name: "x", size: 14 }))),

      tab === "person" && React.createElement("div", { className: "at-list" },
        PF.PERSONS.map((p) => {
          const t = { type: "person", personId: p.id };
          const on = triggers.some((u) => sameTrigger(u, t));
          return React.createElement("button", { key: p.id, className: "at-row" + (on ? " on" : ""), disabled: on, onClick: () => onAdd(t) },
            React.createElement(Avatar, { personId: p.id, size: 26 }),
            React.createElement("span", null, p.name),
            React.createElement("span", { className: "at-count" }, on ? "aktiv" : "+" + countFor(t)));
        })),

      tab === "tag" && React.createElement("div", null,
        React.createElement("div", { className: "tag-search", style: { margin: "2px 0 8px" } },
          React.createElement(Icon, { name: "search", size: 13, style: { color: "var(--text-3)" } }),
          React.createElement("input", { value: tagQ, placeholder: "Tag suchen\u2026", autoFocus: true, onChange: (e) => setTagQ(e.target.value) })),
        React.createElement("div", { className: "at-list" },
          PF.TAG_FACETS.filter((f) => f.name.includes(tagQ.toLowerCase())).slice(0, 18).map((f) => {
            const t = { type: "tag", tagName: f.name };
            const on = triggers.some((u) => sameTrigger(u, t));
            return React.createElement("button", { key: f.name, className: "at-row" + (on ? " on" : ""), disabled: on, onClick: () => onAdd(t) },
              React.createElement(Icon, { name: "tag", size: 13, style: { color: "var(--text-3)" } }),
              React.createElement("span", null, f.name),
              React.createElement("span", { className: "at-count" }, on ? "aktiv" : "+" + f.count));
          }))),

      tab === "caption" && React.createElement("div", { className: "at-caption" },
        React.createElement("div", { className: "tag-search", style: { margin: "2px 0 8px" } },
          React.createElement(Icon, { name: "text", size: 14, style: { color: "var(--text-3)" } }),
          React.createElement("input", {
            value: phrase, placeholder: "Wort oder Phrase\u2026", autoFocus: true,
            onChange: (e) => setPhrase(e.target.value),
            onKeyDown: (e) => { if (e.key === "Enter" && phrase.trim()) onAdd({ type: "caption", phrase: phrase.trim() }); },
          })),
        phrase.trim() && React.createElement("button", { className: "at-row hint", onClick: () => onAdd({ type: "caption", phrase: phrase.trim() }) },
          React.createElement(Icon, { name: "plus", size: 13 }),
          React.createElement("span", null, "Caption enth\u00E4lt \u201E" + phrase.trim() + "\u201C"),
          React.createElement("span", { className: "at-count" }, "+" + countFor({ type: "caption", phrase: phrase.trim() })))));
  }

  /* ---------- settings panel (the gear) ---------- */
  function SettingsPanel({ col, assets, smartOn, setSmartOn, mode, setMode, triggers, setTriggers, matched, ledger, onClose }) {
    const [adding, setAdding] = useState(false);
    const addTrigger = (t) => { setTriggers((prev) => [...prev, t]); setAdding(false); };
    const removeTrigger = (i) => setTriggers((prev) => prev.filter((_, idx) => idx !== i));
    const toggleNeg = (i) => setTriggers((prev) => prev.map((t, idx) => idx === i ? { ...t, negate: !t.negate } : t));
    const connector = mode === "all" ? "UND" : "ODER";

    const suggestions = useMemo(() => {
      const usedTags = new Set(triggers.filter((t) => t.type === "tag").map((t) => t.tagName));
      const usedP = new Set(triggers.filter((t) => t.type === "person").map((t) => t.personId));
      const tagS = PF.TAG_FACETS.filter((f) => !usedTags.has(f.name)).slice(0, 5).map((f) => ({ t: { type: "tag", tagName: f.name }, n: f.count }));
      const pS = PF.PERSONS.filter((p) => !usedP.has(p.id))
        .map((p) => ({ t: { type: "person", personId: p.id }, n: assets.filter((a) => PF.evalTrigger(a, { type: "person", personId: p.id })).length }))
        .sort((a, b) => b.n - a.n).slice(0, 2);
      return [...pS, ...tagS];
    }, [triggers, assets]);

    return React.createElement("aside", { className: "rules" },
      React.createElement("div", { className: "set-head" },
        React.createElement("div", null,
          React.createElement(Icon, { name: "settings", size: 14, style: { color: "var(--text-3)" } }),
          React.createElement("span", null, "Album-Einstellungen")),
        React.createElement("button", { className: "iconbtn", style: { width: 30, height: 30 }, onClick: onClose },
          React.createElement(Icon, { name: "x", size: 16 }))),

      // smart toggle — the heart of the unification
      React.createElement("div", { className: "smart-card" + (smartOn ? " on" : "") },
        React.createElement("div", { className: "smart-row" },
          React.createElement("div", { className: "smart-ico" }, React.createElement(Icon, { name: "sparkle", size: 16 })),
          React.createElement("div", { style: { flex: 1, minWidth: 0 } },
            React.createElement("div", { className: "smart-title" }, "Automatisch bef\u00FCllen"),
            React.createElement("div", { className: "smart-desc" }, "Regeln f\u00FCllen dieses Album automatisch \u2014 wie Smart-Alben bei Google Fotos.")),
          React.createElement(Switch, { on: smartOn, onClick: () => setSmartOn((v) => !v) }))),

      smartOn
        ? React.createElement(React.Fragment, null,
            React.createElement("div", { className: "live-stat" },
              React.createElement("span", { className: "live-dot" }),
              React.createElement("span", { className: "live-num mono" }, matched.length),
              React.createElement("span", { className: "live-lbl" }, "Bilder \u00B7 automatisch bef\u00FCllt"),
              ledger && React.createElement("span", { className: "ledger", key: ledger.k },
                ledger.added > 0 && React.createElement("span", { className: "ld-in" }, "+" + ledger.added),
                ledger.removed > 0 && React.createElement("span", { className: "ld-out" }, "\u2212" + ledger.removed))),

            React.createElement("div", { className: "rules-block" },
              React.createElement("div", { className: "rules-label" }, "Verkn\u00FCpfung"),
              React.createElement("div", { className: "mode-seg" },
                React.createElement("button", { className: mode === "all" ? "on" : "", onClick: () => setMode("all") }, "Alle (UND)"),
                React.createElement("button", { className: mode === "any" ? "on" : "", onClick: () => setMode("any") }, "Eine (ODER)"))),

            React.createElement("div", { className: "rules-block" },
              React.createElement("div", { className: "rules-label" }, "Trigger \u00B7 " + triggers.length),
              React.createElement("div", { className: "trig-list" },
                triggers.length === 0 && React.createElement("div", { className: "trig-empty" }, "Noch keine Trigger \u2014 f\u00FCge unten welche hinzu."),
                triggers.map((t, i) => React.createElement(React.Fragment, { key: i },
                  i > 0 && React.createElement("div", { className: "connector" }, React.createElement("span", null, connector)),
                  React.createElement("div", { className: "trig-row" + (t.negate ? " neg" : "") },
                    React.createElement("div", { className: "trig-ico" }, React.createElement(Icon, { name: triggerIcon(t), size: 14 })),
                    React.createElement("div", { className: "trig-body" },
                      React.createElement("div", { className: "trig-kind" }, triggerKind(t)),
                      React.createElement("div", { className: "trig-val" }, triggerLabel(t))),
                    React.createElement("button", { className: "neg-btn" + (t.negate ? " on" : ""), title: "Ausschluss", onClick: () => toggleNeg(i) },
                      t.negate ? "ausschlie\u00DFen" : "einschlie\u00DFen"),
                    React.createElement("button", { className: "trig-x", onClick: () => removeTrigger(i) }, React.createElement(Icon, { name: "x", size: 13 })))))),
              adding
                ? React.createElement(AddTrigger, { assets, triggers, onAdd: addTrigger, onClose: () => setAdding(false) })
                : React.createElement("button", { className: "add-trig-btn", onClick: () => setAdding(true) },
                    React.createElement(Icon, { name: "plus", size: 14 }), "Trigger hinzuf\u00FCgen")),

            !adding && suggestions.length > 0 && React.createElement("div", { className: "rules-block" },
              React.createElement("div", { className: "rules-label" }, "Vorschl\u00E4ge"),
              React.createElement("div", { className: "suggest-wrap" },
                suggestions.map((s, i) => React.createElement("button", { key: i, className: "suggest-chip", onClick: () => addTrigger(s.t) },
                  React.createElement(Icon, { name: triggerIcon(s.t), size: 11 }), triggerLabel(s.t),
                  React.createElement("span", { className: "sc-n" }, "+" + s.n))))),

            React.createElement("div", { className: "rules-foot" },
              React.createElement(Icon, { name: "info", size: 13 }),
              React.createElement("span", null, "Mitgliedschaft wird bei jeder \u00C4nderung an Tags, Caption oder Personen-Zuordnung neu bewertet \u2014 passende Bilder kommen rein, andere fallen raus.")))
        : React.createElement("div", { className: "set-manual" },
            React.createElement(Icon, { name: "album", size: 22, style: { color: "var(--text-3)" } }),
            React.createElement("div", { className: "sm-title" }, "Manuell kuratiert"),
            React.createElement("p", null, "Dieses Album enth\u00E4lt nur Bilder, die du selbst hinzugef\u00FCgt hast. Schalte die automatische Bef\u00FCllung ein, um es zus\u00E4tzlich per Person-, Tag- oder Caption-Regeln zu f\u00FCllen.")),
      React.createElement("div", { style: { height: 18 } }));
  }

  /* ---------- album detail (unified) ---------- */
  function AlbumDetail({ col, assets, onBack, onOpen, onFav }) {
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [smartOn, setSmartOn] = useState(!!(col.smart && col.smart.on));
    const [mode, setMode] = useState((col.smart && col.smart.mode) || "any");
    const [triggers, setTriggers] = useState(((col.smart && col.smart.triggers) || []).map((t) => ({ ...t })));

    const members = useMemo(() => smartOn
      ? PF.matchTriggers(assets, triggers, mode)
      : lookup(assets, col.memberIds)
    , [assets, smartOn, mode, triggers, col]);
    const memberIds = useMemo(() => members.map((a) => a.id), [members]);

    // in/out animation
    const [display, setDisplay] = useState(() => members.map((a) => ({ a, st: "stable" })));
    const [ledger, setLedger] = useState(null);
    const prevRef = useRef(new Set(memberIds));
    const first = useRef(true);

    useEffect(() => {
      const prev = prevRef.current;
      const now = new Set(memberIds);
      if (first.current) { first.current = false; prevRef.current = now; setDisplay(members.map((a) => ({ a, st: "stable" }))); return; }
      const added = memberIds.filter((id) => !prev.has(id));
      const removed = [...prev].filter((id) => !now.has(id));
      const removedAssets = removed.map((id) => assets.find((a) => a.id === id)).filter(Boolean);
      setDisplay([
        ...members.map((a) => ({ a, st: added.includes(a.id) ? "in" : "stable" })),
        ...removedAssets.map((a) => ({ a, st: "out" })),
      ]);
      if (added.length || removed.length) setLedger({ added: added.length, removed: removed.length, k: Date.now() });
      prevRef.current = now;
      const t = setTimeout(() => setDisplay(memberIds.map((id) => ({ a: assets.find((x) => x.id === id), st: "stable" })).filter((d) => d.a)), 1300);
      return () => clearTimeout(t);
    }, [memberIds]);

    useEffect(() => { if (!ledger) return; const t = setTimeout(() => setLedger(null), 2600); return () => clearTimeout(t); }, [ledger]);

    return React.createElement("div", { className: "content alb-detail" + (settingsOpen ? " settings-open" : "") },
      settingsOpen && React.createElement(SettingsPanel, {
        col, assets, smartOn, setSmartOn, mode, setMode, triggers, setTriggers, matched: members, ledger,
        onClose: () => setSettingsOpen(false),
      }),
      React.createElement("div", { className: "grid-wrap" },
        // header
        React.createElement("div", { className: "alb-detail-head" },
          React.createElement("button", { className: "back-row", onClick: onBack },
            React.createElement(Icon, { name: "arrowLeft", size: 16 }), "Alle Alben"),
          React.createElement("div", { className: "adh-main" },
            React.createElement(AlbumCover, { photos: members.map((m) => m.photo) }),
            React.createElement("div", { className: "adh-text" },
              React.createElement("div", { className: "adh-name" }, col.name,
                smartOn && React.createElement("span", { className: "adh-auto" }, React.createElement(Icon, { name: "sparkle", size: 12 }), "Auto")),
              React.createElement("div", { className: "adh-sub" },
                React.createElement("span", { className: "mono" }, members.length + " Bilder"),
                React.createElement("span", { className: "dotsep" }, "\u00B7"),
                smartOn ? "automatisch bef\u00FCllt" : "manuell kuratiert",
                React.createElement("span", { className: "dotsep" }, "\u00B7"), col.desc)),
            React.createElement("div", { className: "adh-actions" },
              ledger && React.createElement("span", { className: "ledger inline", key: ledger.k },
                ledger.added > 0 && React.createElement("span", { className: "ld-in" }, "+" + ledger.added),
                ledger.removed > 0 && React.createElement("span", { className: "ld-out" }, "\u2212" + ledger.removed)),
              !smartOn && React.createElement("button", { className: "selectbtn" }, React.createElement(Icon, { name: "plus", size: 15 }), React.createElement("span", { className: "sel-lbl" }, "Bilder")),
              React.createElement("button", { className: "selectbtn" }, React.createElement(Icon, { name: "export", size: 15 }), React.createElement("span", { className: "sel-lbl" }, "Export")),
              React.createElement("button", { className: "iconbtn gear" + (settingsOpen ? " on" : ""), title: "Album-Einstellungen", onClick: () => setSettingsOpen((o) => !o) },
                React.createElement(Icon, { name: "settings", size: 18 })))),
          smartOn && React.createElement("div", { className: "adh-rules" },
            React.createElement(Icon, { name: "sparkle", size: 12, style: { color: "var(--semantic)" } }),
            React.createElement("span", { className: "ar-mode" }, mode === "all" ? "Alle Trigger" : "Ein Trigger"),
            triggers.map((t, i) => React.createElement("span", { className: "trig-mini" + (t.negate ? " neg" : ""), key: i },
              React.createElement(Icon, { name: triggerIcon(t), size: 10 }), triggerLabel(t))),
            React.createElement("button", { className: "ar-edit", onClick: () => setSettingsOpen(true) }, "bearbeiten"))),

        // results
        members.length === 0 && display.length === 0
          ? React.createElement("div", { className: "placeholder-view", style: { height: "55vh" } },
              React.createElement(Icon, { name: smartOn ? "sparkle" : "album", size: 40 }),
              React.createElement("h3", null, smartOn ? "Keine Treffer" : "Album ist leer"),
              React.createElement("p", null, smartOn ? "F\u00FCge Trigger hinzu oder lockere die Verkn\u00FCpfung (ODER)." : "F\u00FCge Bilder hinzu oder aktiviere die automatische Bef\u00FCllung per Zahnrad."))
          : React.createElement("div", { style: { padding: "6px 0 0" } },
              justified(display, 190, (d) => React.createElement(Tile, { key: d.a.id, a: d.a, base: 190, st: d.st, onOpen: (id) => onOpen(id, memberIds), onFav }))),
        React.createElement("div", { style: { height: 40 } })));
  }

  /* ---------- router ---------- */
  function Albums({ assets, onOpen, onFav }) {
    const [sel, setSel] = useState(null);
    const col = sel ? PF.COLLECTIONS.find((c) => c.id === sel) : null;
    if (!col) return React.createElement(Overview, { assets, onOpen: setSel });
    return React.createElement(AlbumDetail, { key: col.id, col, assets, onBack: () => setSel(null), onOpen, onFav });
  }

  window.Albums = Albums;
})();
