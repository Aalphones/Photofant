/* Photofant — Beziehungs-/Bild-Browser + Person-Auswahl
   · RelationBrowser: durchsuch- & filterbarer Bild-Picker (an der Galerie-Roll orientiert)
   · PersonSelect:    kompaktes Personen-Such-Popover
   Beide → window. */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useMemo } = React;

  /* ---- local facet + row (reuse gallery rail CSS) ---- */
  function Facet({ title, children, defaultOpen = true }) {
    const [open, setOpen] = useState(defaultOpen);
    return React.createElement("div", { className: "facet" + (open ? "" : " closed") },
      React.createElement("div", { className: "facet-head", onClick: () => setOpen((o) => !o) },
        React.createElement("span", { className: "facet-title" }, title),
        React.createElement("span", { className: "chev" }, React.createElement(Icon, { name: "chevronDown", size: 15 }))),
      React.createElement("div", { className: "facet-body" }, children));
  }
  function Row({ on, onClick, label, count, lead }) {
    return React.createElement("div", { className: "frow" + (on ? " on" : ""), onClick },
      React.createElement("div", { className: "cbox" }, on && React.createElement(Icon, { name: "check", size: 12, stroke: 3, style: { color: "#fff" } })),
      lead, React.createElement("span", null, label),
      count != null && React.createElement("span", { className: "fcount" }, count));
  }

  /* ======================================================
     RELATION BROWSER
     props: assets, title, subtitle, multi, initialSelected[],
            excludeIds[], defaultSource, confirmLabel, onConfirm(ids), onClose
     ====================================================== */
  function RelationBrowser({ assets, title, subtitle, multi = false, initialSelected = [],
    excludeIds = [], defaultSource = null, confirmLabel, onConfirm, onClose }) {
    const [sel, setSel] = useState(() => new Set(initialSelected));
    const [q, setQ] = useState("");
    const [mode, setMode] = useState("all"); // all | tags | caption
    const [filtersOpen, setFiltersOpen] = useState(false);
    const [F, setF] = useState(() => ({
      persons: new Set(), sources: new Set(defaultSource ? [defaultSource] : []),
      framings: new Set(), tags: new Set(), favOnly: false, editedOnly: false,
    }));

    const pool = useMemo(() => assets.filter((a) => !excludeIds.includes(a.id)), [assets, excludeIds]);

    const counts = useMemo(() => {
      const c = { persons: {}, sources: {}, framings: {} };
      pool.forEach((a) => {
        c.persons[a.personId] = (c.persons[a.personId] || 0) + 1;
        c.sources[a.source] = (c.sources[a.source] || 0) + 1;
        c.framings[a.framing] = (c.framings[a.framing] || 0) + 1;
      });
      return c;
    }, [pool]);

    const toggleSet = (key, val) => {
      const next = new Set(F[key]); next.has(val) ? next.delete(val) : next.add(val);
      setF({ ...F, [key]: next });
    };

    const list = useMemo(() => {
      const ql = q.trim().toLowerCase();
      return pool.filter((a) => {
        if (F.persons.size && !F.persons.has(a.personId) && !a.faces.some((f) => F.persons.has(f.personId))) return false;
        if (F.sources.size && !F.sources.has(a.source)) return false;
        if (F.framings.size && !F.framings.has(a.framing)) return false;
        if (F.favOnly && !a.favourite) return false;
        if (F.editedOnly && a.versionCount < 2) return false;
        if (F.tags.size && ![...F.tags].every((t) => a.tags.some((x) => x.name === t))) return false;
        if (ql) {
          if (mode === "tags") { if (!a.tags.some((t) => t.name.includes(ql))) return false; }
          else if (mode === "caption") { if (!(a.caption || "").toLowerCase().includes(ql)) return false; }
          else {
            const hay = ("#" + a.id + " " + a.caption + " " + a.tags.map((t) => t.name).join(" ") + " " + PF.SCENES[a.scene].name + " " + PF.personName(a.personId)).toLowerCase();
            if (!ql.split(/\s+/).every((w) => hay.includes(w))) return false;
          }
        }
        return true;
      });
    }, [pool, F, q, mode]);

    const tagFacets = PF.TAG_FACETS.slice(0, 10);
    const activeFilters = F.persons.size + F.sources.size + F.framings.size + F.tags.size + (F.favOnly ? 1 : 0) + (F.editedOnly ? 1 : 0);

    const pick = (id) => {
      if (multi) { const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n); }
      else setSel(new Set(sel.has(id) ? [] : [id]));
    };
    const clearFilters = () => setF({ persons: new Set(), sources: new Set(), framings: new Set(), tags: new Set(), favOnly: false, editedOnly: false });

    const selArr = [...sel];

    return React.createElement("div", { className: "big-scrim", onClick: onClose, style: { zIndex: 130 } },
      React.createElement("div", { className: "rb-modal", onClick: (e) => e.stopPropagation() },
        // head
        React.createElement("div", { className: "rb-head" },
          React.createElement("div", { className: "rh-ico" }, React.createElement(Icon, { name: "link", size: 17 })),
          React.createElement("div", { style: { minWidth: 0, flex: 1 } },
            React.createElement("div", { className: "rb-title" }, title || "Bild auswählen"),
            React.createElement("div", { className: "rb-sub" }, subtitle || (multi ? "Mehrfachauswahl möglich" : "Durchsuchen, filtern und ein Bild wählen"))),
          React.createElement("button", { className: "iconbtn", style: { width: 32, height: 32 }, onClick: onClose }, React.createElement(Icon, { name: "x", size: 18 }))),

        React.createElement("div", { className: "rb-body" },
          // mobile scrim behind the filter sheet
          filtersOpen && React.createElement("div", { className: "rb-fscrim", onClick: () => setFiltersOpen(false) }),
          // filters rail / mobile bottom sheet
          React.createElement("aside", { className: "rb-filters" + (filtersOpen ? " open" : "") },
            React.createElement("div", { className: "rb-fhead" },
              React.createElement("span", { className: "rf-t" }, "Filter"),
              activeFilters > 0 && React.createElement("button", { className: "rf-clear", onClick: clearFilters }, "Zurücksetzen"),
              React.createElement("button", { className: "rb-fclose", "aria-label": "Filter schließen", onClick: () => setFiltersOpen(false) }, React.createElement(Icon, { name: "x", size: 18 }))),
            React.createElement("div", { className: "rb-fscroll" },
            React.createElement(Facet, { title: "Person" },
              PF.PERSONS.map((p) => React.createElement(Row, {
                key: p.id, on: F.persons.has(p.id), onClick: () => toggleSet("persons", p.id),
                label: p.name, count: counts.persons[p.id] || 0,
                lead: React.createElement("div", { className: "face-chip" }, React.createElement(Img, { src: p.portrait, bg: p.avatarBg })),
              })),
              React.createElement(Row, {
                on: F.persons.has(-1), onClick: () => toggleSet("persons", -1), label: "Unbekannt", count: counts.persons[-1] || 0,
                lead: React.createElement("div", { className: "face-chip", style: { display: "grid", placeItems: "center", background: "var(--surface)" } },
                  React.createElement(Icon, { name: "face", size: 14, style: { color: "var(--text-3)" } })),
              })),
            React.createElement(Facet, { title: "Quelle" },
              ["original", "sdxl", "flux"].map((s) => React.createElement(Row, {
                key: s, on: F.sources.has(s), onClick: () => toggleSet("sources", s), label: PF.sourceLabel(s), count: counts.sources[s] || 0,
                lead: React.createElement("span", { className: "swatch", style: { background: s === "flux" ? "oklch(0.55 0.16 285)" : s === "sdxl" ? "oklch(0.52 0.13 200)" : "oklch(0.55 0.02 256)" } }),
              }))),
            React.createElement(Facet, { title: "Framing", defaultOpen: false },
              ["close_up", "medium", "full_body"].map((f) => React.createElement(Row, {
                key: f, on: F.framings.has(f), onClick: () => toggleSet("framings", f), label: PF.framingLabel(f), count: counts.framings[f] || 0,
              }))),
            React.createElement(Facet, { title: "Sammlung", defaultOpen: false },
              React.createElement(Row, { on: F.favOnly, onClick: () => setF({ ...F, favOnly: !F.favOnly }), label: "Nur Favoriten",
                lead: React.createElement("span", { style: { color: "var(--gold)" } }, React.createElement(Icon, { name: "star", size: 15, fill: true })) }),
              React.createElement(Row, { on: F.editedOnly, onClick: () => setF({ ...F, editedOnly: !F.editedOnly }), label: "Mit Edits/Versionen",
                lead: React.createElement("span", { style: { color: "var(--text-3)" } }, React.createElement(Icon, { name: "layers", size: 15 })) })),
            React.createElement(Facet, { title: "Tags", defaultOpen: false },
              tagFacets.map((t) => React.createElement(Row, {
                key: t.name, on: F.tags.has(t.name), onClick: () => toggleSet("tags", t.name), label: t.name, count: t.count,
              })))),
            React.createElement("button", { className: "rb-fdone", onClick: () => setFiltersOpen(false) },
              list.length + " Bilder anzeigen")),

          // main
          React.createElement("div", { className: "rb-main" },
            React.createElement("div", { className: "rb-searchbar" },
              React.createElement("div", { className: "rb-search" },
                React.createElement(Icon, { name: "search", size: 15 }),
                React.createElement("input", { autoFocus: true, value: q, placeholder: "Freitextsuche: ID, Caption, Tags, Person …", onChange: (e) => setQ(e.target.value) }),
                q && React.createElement("button", { className: "rb-clearq", "aria-label": "Suche leeren", onClick: () => setQ("") }, React.createElement(Icon, { name: "x", size: 14 }))),
              React.createElement("button", { className: "rb-filterbtn" + (filtersOpen ? " on" : ""), onClick: () => setFiltersOpen((o) => !o) },
                React.createElement(Icon, { name: "filter", size: 15 }), React.createElement("span", null, "Filter"),
                activeFilters > 0 ? React.createElement("span", { className: "fb-badge" }, activeFilters) : null),
              React.createElement("div", { className: "rb-modes" },
                [["all", "Alle"], ["tags", "Tags"], ["caption", "Cap."]].map(([k, l]) =>
                  React.createElement("button", { key: k, className: mode === k ? "on" : "", onClick: () => setMode(k) }, l))),
              React.createElement("span", { className: "rb-count" }, list.length + " Bilder")),

            React.createElement("div", { className: "rb-scroll" },
              React.createElement("div", { className: "rb-grid" },
                list.length === 0
                  ? React.createElement("div", { className: "rb-empty" },
                      React.createElement(Icon, { name: "search", size: 38 }),
                      React.createElement("div", { style: { fontWeight: 600, color: "var(--text-2)" } }, "Keine Treffer"),
                      React.createElement("div", { style: { fontSize: 12, marginTop: 4 } }, "Filter oder Suche anpassen"))
                  : list.map((a) => React.createElement("div", {
                      key: a.id, className: "rb-cell" + (sel.has(a.id) ? " sel" : ""), onClick: () => pick(a.id),
                      onDoubleClick: () => { if (!multi) { onConfirm([a.id]); } },
                    },
                      React.createElement(Img, { src: a.photo, bg: a.bg }),
                      React.createElement("div", { className: "rc-veil" }),
                      a.source !== "original" && React.createElement("span", { className: "rc-badge badge " + a.source }, PF.sourceLabel(a.source)),
                      React.createElement("span", { className: "rc-id" }, "#" + a.id),
                      React.createElement("span", { className: "rc-chk" }, sel.has(a.id) && React.createElement(Icon, { name: "check", size: 13, stroke: 3 }))))))),

        // footer
        React.createElement("div", { className: "rb-foot" },
          React.createElement("div", { className: "rbf-info" },
            selArr.length === 0
              ? React.createElement("span", { style: { color: "var(--text-3)" } }, multi ? "Keine Bilder gewählt" : "Kein Bild gewählt")
              : React.createElement(React.Fragment, null,
                  React.createElement("div", { className: "rb-selstrip" },
                    selArr.slice(0, 5).map((id) => { const a = assets.find((x) => x.id === id); return React.createElement("div", { key: id, className: "rss-thumb" }, React.createElement(Img, { src: a.photo, bg: a.bg })); })),
                  React.createElement("span", null, React.createElement("b", null, selArr.length), multi ? " Bilder gewählt" : " ausgewählt"))),
          React.createElement("div", { className: "rbf-actions" },
            React.createElement("button", { className: "foot-btn ghost", onClick: onClose }, "Abbrechen"),
            React.createElement("button", { className: "foot-btn primary", disabled: selArr.length === 0, onClick: () => onConfirm(selArr) },
              React.createElement(Icon, { name: "check", size: 16 }), confirmLabel || (multi ? "Übernehmen" : "Verknüpfen")))))));
  }

  /* ======================================================
     PERSON SELECT (compact popover)
     props: excludeIds[], onPick(id), onClose, title
     ====================================================== */
  function PersonSelect({ excludeIds = [], onPick, onClose, title }) {
    const [q, setQ] = useState("");
    const ql = q.trim().toLowerCase();
    const dir = PF.DIRECTORY;
    const list = (ql ? dir.filter((p) => p.name.toLowerCase().includes(ql)) : dir).slice(0, 60);
    return React.createElement("div", { className: "psp-scrim", onClick: onClose },
      React.createElement("div", { className: "psp-modal", onClick: (e) => e.stopPropagation() },
        React.createElement("div", { className: "psp-head" },
          React.createElement(Icon, { name: "face", size: 16, style: { color: "var(--text-2)" } }),
          React.createElement("div", { className: "ph-t" }, title || "Person hinzufügen"),
          React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28, marginLeft: "auto" }, onClick: onClose }, React.createElement(Icon, { name: "x", size: 15 }))),
        React.createElement("div", { className: "psp-search" },
          React.createElement(Icon, { name: "search", size: 15 }),
          React.createElement("input", { autoFocus: true, value: q, placeholder: "Person suchen … (" + dir.length + " bekannte Gesichter)", onChange: (e) => setQ(e.target.value) })),
        React.createElement("div", { className: "psp-list" },
          list.length === 0 && React.createElement("div", { className: "psp-empty" }, "Keine Person für „" + q + "“"),
          list.map((p) => React.createElement("button", {
            key: p.id, className: "psp-row" + (excludeIds.includes(p.id) ? " dis" : ""),
            onClick: () => { onPick(p.id); onClose(); },
          },
            React.createElement(Avatar, { personId: p.id, size: 32 }),
            React.createElement("span", { className: "psp-name" }, p.name),
            excludeIds.includes(p.id)
              ? React.createElement(Icon, { name: "check", size: 15, style: { color: "var(--accent)" } })
              : p.count > 0 && React.createElement("span", { className: "psp-count" }, p.count))))));
  }

  window.RelationBrowser = RelationBrowser;
  window.PersonSelect = PersonSelect;
})();
