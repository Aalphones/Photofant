/* Photofant — Galerie view: filter rail + justified grid + selection */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useMemo, useRef } = React;

  /* ---------------- filter rail ---------------- */
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

  function Rail({ F, set, counts, onClose }) {
    const [tagQ, setTagQ] = useState("");
    const toggleSet = (key, val) => {
      const next = new Set(F[key]); next.has(val) ? next.delete(val) : next.add(val);
      set({ ...F, [key]: next });
    };
    const tagFacets = PF.TAG_FACETS.filter((t) => t.name.includes(tagQ.toLowerCase())).slice(0, tagQ ? 30 : 12);

    return React.createElement("aside", { className: "rail" },
      React.createElement("div", { className: "rail-head" },
        React.createElement("h4", null, "Filter"),
        React.createElement("button", { className: "iconbtn", style: { width: 32, height: 32 }, onClick: onClose },
          React.createElement(Icon, { name: "x", size: 18 }))),
      // Person
      React.createElement(Facet, { title: "Person" },
        PF.PERSONS.map((p) => React.createElement(Row, {
          key: p.id, on: F.persons.has(p.id), onClick: () => toggleSet("persons", p.id),
          label: p.name, count: counts.persons[p.id] || 0,
          lead: React.createElement("div", { className: "face-chip" }, React.createElement(Img, { src: p.portrait, bg: p.avatarBg })),
        })),
        React.createElement(Row, {
          on: F.persons.has(-1), onClick: () => toggleSet("persons", -1),
          label: "Unbekannt", count: counts.persons[-1] || 0,
          lead: React.createElement("div", { className: "face-chip", style: { display: "grid", placeItems: "center", background: "var(--surface)" } },
            React.createElement(Icon, { name: "face", size: 14, style: { color: "var(--text-3)" } })),
        })),
      // Quelle
      React.createElement(Facet, { title: "Quelle" },
        ["original", "sdxl", "flux"].map((s) => React.createElement(Row, {
          key: s, on: F.sources.has(s), onClick: () => toggleSet("sources", s),
          label: PF.sourceLabel(s), count: counts.sources[s] || 0,
          lead: React.createElement("span", { className: "swatch", style: { background: s === "flux" ? "oklch(0.55 0.16 285)" : s === "sdxl" ? "oklch(0.52 0.13 200)" : "oklch(0.55 0.02 256)" } }),
        }))),
      // Framing
      React.createElement(Facet, { title: "Framing" },
        ["close_up", "medium", "full_body"].map((f) => React.createElement(Row, {
          key: f, on: F.framings.has(f), onClick: () => toggleSet("framings", f),
          label: PF.framingLabel(f), count: counts.framings[f] || 0,
        }))),
      // Qualität
      React.createElement(Facet, { title: "Qualität (min.)" },
        React.createElement(QualitySlider, { value: F.qualityMin, onChange: (v) => set({ ...F, qualityMin: v }) })),
      // Favoriten
      React.createElement(Facet, { title: "Sammlung" },
        React.createElement(Row, {
          on: F.favOnly, onClick: () => set({ ...F, favOnly: !F.favOnly }), label: "Nur Favoriten",
          lead: React.createElement("span", { style: { color: "var(--gold)" } }, React.createElement(Icon, { name: "star", size: 15, fill: true })),
        }),
        React.createElement(Row, {
          on: F.editedOnly, onClick: () => set({ ...F, editedOnly: !F.editedOnly }), label: "Mit Edits/Versionen",
          lead: React.createElement("span", { style: { color: "var(--text-3)" } }, React.createElement(Icon, { name: "layers", size: 15 })),
        })),
      // Tags
      React.createElement(Facet, { title: "Tags" },
        React.createElement("div", { className: "tag-search" },
          React.createElement(Icon, { name: "search", size: 13, style: { color: "var(--text-3)" } }),
          React.createElement("input", { value: tagQ, placeholder: "Tag suchen…", onChange: (e) => setTagQ(e.target.value) })),
        tagFacets.map((t) => React.createElement(Row, {
          key: t.name, on: F.tags.has(t.name), onClick: () => toggleSet("tags", t.name), label: t.name, count: t.count,
        }))));
  }

  function QualitySlider({ value, onChange }) {
    const ref = useRef(null);
    const drag = (e) => {
      const rect = ref.current.getBoundingClientRect();
      const move = (ev) => {
        const x = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
        onChange(Math.round(x * 100) / 100);
      };
      move(e);
      const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
      window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
    };
    return React.createElement("div", null,
      React.createElement("div", { className: "qual-track", ref, onMouseDown: drag },
        React.createElement("div", { className: "qual-fill", style: { width: (value * 100) + "%" } }),
        React.createElement("div", { className: "qual-knob", style: { left: (value * 100) + "%" } })),
      React.createElement("div", { className: "qual-row" },
        React.createElement("span", null, "≥ " + Math.round(value * 100)),
        React.createElement("span", null, "100")));
  }

  /* ---------------- grid cell ---------------- */
  function Cell({ a, base, selected, selMode, onOpen, onToggleSel, onFav }) {
    const up = a.versions.some((v) => v.type === "upscale" && v.current);
    return React.createElement("div", {
      className: "cell" + (selected ? " sel" : ""),
      style: { height: base, flexGrow: a.ar.w / a.ar.h, flexBasis: (a.ar.w / a.ar.h) * base + "px" },
      onClick: (e) => { if (selMode || e.metaKey || e.ctrlKey) onToggleSel(a.id, e); else onOpen(a.id); },
    },
      React.createElement("div", { className: "img" }, React.createElement(Img, { src: a.photo, bg: a.bg })),
      React.createElement("div", { className: "veil" }),
      React.createElement("button", { className: "pick", onClick: (e) => { e.stopPropagation(); onToggleSel(a.id, e); } },
        selected && React.createElement(Icon, { name: "check", size: 13, stroke: 3, style: { color: "#fff" } })),
      React.createElement("button", { className: "fav" + (a.favourite ? " on" : ""), onClick: (e) => { e.stopPropagation(); onFav(a.id); } },
        React.createElement(Icon, { name: "star", size: 16, fill: a.favourite })),
      // person tag (top-left) when grouped not by person
      React.createElement("div", { className: "tile-person" },
        React.createElement(Avatar, { personId: a.personId, size: 22 })),
      React.createElement("div", { className: "meta-bl" },
        a.source !== "original" && React.createElement("span", { className: "badge " + a.source }, PF.sourceLabel(a.source)),
        up && React.createElement("span", { className: "badge up" }, "2×"),
        a.versionCount > 1 && React.createElement("span", { className: "badge", style: { display: "inline-flex", alignItems: "center", gap: 4 } },
          React.createElement(Icon, { name: "layers", size: 10 }), a.versionCount)));
  }

  /* ---------------- main gallery ---------------- */
  function Gallery({ assets, F, setF, search, onOpen, onFav, sel, setSel, selMode, setSelMode, sort, setSort, group, setGroup, density, setDensity, railOpen, setRailOpen, isMobile }) {
    const counts = useMemo(() => {
      const c = { persons: {}, sources: {}, framings: {} };
      assets.forEach((a) => {
        c.persons[a.personId] = (c.persons[a.personId] || 0) + 1;
        c.sources[a.source] = (c.sources[a.source] || 0) + 1;
        c.framings[a.framing] = (c.framings[a.framing] || 0) + 1;
      });
      return c;
    }, [assets]);

    // apply filters + search
    const filtered = useMemo(() => {
      const q = search.q.trim().toLowerCase();
      return assets.filter((a) => {
        if (F.persons.size && !F.persons.has(a.personId)) return false;
        if (F.sources.size && !F.sources.has(a.source)) return false;
        if (F.framings.size && !F.framings.has(a.framing)) return false;
        if (a.quality < F.qualityMin) return false;
        if (F.favOnly && !a.favourite) return false;
        if (F.editedOnly && a.versionCount < 2) return false;
        if (F.tags.size && ![...F.tags].every((t) => a.tags.some((x) => x.name === t))) return false;
        if (q) {
          if (search.mode === "tags") { if (!a.tags.some((t) => t.name.includes(q))) return false; }
          else if (search.mode === "caption") { if (!a.caption.toLowerCase().includes(q)) return false; }
          else { /* semantic: loose match across caption+tags+scene */
            const hay = (a.caption + " " + a.tags.map((t) => t.name).join(" ") + " " + PF.SCENES[a.scene].name).toLowerCase();
            if (!q.split(/\s+/).some((w) => hay.includes(w))) return false;
          }
        }
        return true;
      });
    }, [assets, F, search]);

    const sorted = useMemo(() => {
      const arr = [...filtered];
      arr.sort((a, b) => sort.key === "size" ? b.fileSize - a.fileSize : b.date - a.date);
      if (sort.dir === "asc") arr.reverse();
      return arr;
    }, [filtered, sort]);

    // grouping
    const groups = useMemo(() => {
      const map = new Map();
      const keyOf = (a) => group === "person" ? PF.personName(a.personId) : group === "source" ? PF.sourceLabel(a.source) : a.periodLabel;
      sorted.forEach((a) => { const k = keyOf(a); if (!map.has(k)) map.set(k, []); map.get(k).push(a); });
      return [...map.entries()];
    }, [sorted, group]);

    const base = isMobile
      ? (density === "lg" ? 150 : density === "sm" ? 96 : 122)
      : (density === "lg" ? 250 : density === "sm" ? 150 : 196);
    const flatOrder = useMemo(() => sorted.map((a) => a.id), [sorted]);
    const openWithOrder = (id) => onOpen(id, flatOrder);

    const activeFilterCount = F.persons.size + F.sources.size + F.framings.size + F.tags.size + (F.favOnly ? 1 : 0) + (F.editedOnly ? 1 : 0) + (F.qualityMin > 0 ? 1 : 0);

    const toggleSel = (id) => { const n = new Set(sel); n.has(id) ? n.delete(id) : n.add(id); setSel(n); };
    const selectAll = (ids) => { const n = new Set(sel); ids.forEach((i) => n.add(i)); setSel(n); };

    const removeChip = (kind, val) => {
      if (kind === "fav") return setF({ ...F, favOnly: false });
      if (kind === "edited") return setF({ ...F, editedOnly: false });
      if (kind === "qual") return setF({ ...F, qualityMin: 0 });
      const next = new Set(F[kind]); next.delete(val); setF({ ...F, [kind]: next });
    };

    const chips = [];
    F.persons.forEach((p) => chips.push({ kind: "persons", val: p, label: PF.personName(p), key: "Person" }));
    F.sources.forEach((s) => chips.push({ kind: "sources", val: s, label: PF.sourceLabel(s), key: "Quelle" }));
    F.framings.forEach((f) => chips.push({ kind: "framings", val: f, label: PF.framingLabel(f), key: "Framing" }));
    F.tags.forEach((t) => chips.push({ kind: "tags", val: t, label: t, key: "Tag" }));
    if (F.favOnly) chips.push({ kind: "fav", label: "Favoriten", key: "" });
    if (F.editedOnly) chips.push({ kind: "edited", label: "Mit Edits", key: "" });
    if (F.qualityMin > 0) chips.push({ kind: "qual", label: "Qualität ≥ " + Math.round(F.qualityMin * 100), key: "" });

    return React.createElement("div", { className: "content" },
      railOpen ? React.createElement(React.Fragment, null,
        React.createElement("div", { className: "rail-scrim", onClick: () => setRailOpen(false) }),
        React.createElement(Rail, { F, set: setF, counts, onClose: () => setRailOpen(false) })) : null,
      React.createElement("div", { className: "grid-wrap" + (selMode ? " selmode" : "") },
        // subbar
        React.createElement("div", { className: "subbar" },
          React.createElement("div", { className: "sb-chips" },
            React.createElement("span", { className: "result-count" }, chips.length ? sorted.length + " Treffer" : sorted.length + " Bilder"),
            chips.length > 0 && React.createElement("span", { className: "sb-div" }),
            chips.map((c, i) => React.createElement("span", { key: i, className: "chip" + (c.key === "" ? " accent" : "") },
              c.key && React.createElement("span", { className: "chip-key" }, c.key + ":"), c.label,
              React.createElement("span", { className: "x", onClick: () => removeChip(c.kind, c.val) }, React.createElement(Icon, { name: "x", size: 12 })))),
            chips.length > 0 && React.createElement("button", { className: "clear-all", onClick: () => setF(window.PF_EMPTY_FILTERS()) }, "Alle entfernen")),
          React.createElement("div", { className: "sb-tools" },
            // group
            React.createElement("div", { className: "seg seg-group" },
              [["month", "Monat"], ["person", "Person"], ["source", "Quelle"]].map(([k, l]) =>
                React.createElement("button", { key: k, className: group === k ? "on" : "", onClick: () => setGroup(k) }, l))),
            // sort
            React.createElement("button", { className: "selectbtn", onClick: () => setSort(sort.key === "date" ? { key: "size", dir: "desc" } : sort.key === "size" && sort.dir === "desc" ? { key: "size", dir: "asc" } : { key: "date", dir: "desc" }) },
              React.createElement(Icon, { name: "sort", size: 15 }), sort.key === "size" ? "Größe" : "Datum",
              React.createElement("span", { style: { color: "var(--text-3)", fontSize: 11 } }, sort.dir === "asc" ? "↑" : "↓")),
            // density
            React.createElement("div", { className: "seg seg-density" },
              [["sm", "grid"], ["md", "grid"], ["lg", "grid"]].map(([k]) =>
                React.createElement("button", { key: k, className: density === k ? "on" : "", onClick: () => setDensity(k), title: "Dichte " + k },
                  React.createElement(Icon, { name: "grid", size: k === "sm" ? 13 : k === "md" ? 15 : 17 })))),
            // select toggle
            React.createElement("button", { className: "selectbtn" + (selMode ? " on" : ""), onClick: () => { setSelMode(!selMode); if (selMode) setSel(new Set()); }, style: selMode ? { background: "var(--accent-weak)", borderColor: "var(--accent-line)", color: "var(--accent)" } : {} },
              React.createElement(Icon, { name: "select", size: 15 }), React.createElement("span", { className: "sel-lbl" }, "Auswählen")))),

        // groups + grids
        sorted.length === 0
          ? React.createElement("div", { className: "placeholder-view", style: { height: "60vh" } },
              React.createElement(Icon, { name: "search", size: 40 }),
              React.createElement("h3", null, "Keine Treffer"),
              React.createElement("p", null, "Passe die Filter oder die Suche an, um Bilder zu finden."))
          : groups.map(([label, items]) => React.createElement("section", { key: label, "data-screen-label": label },
              React.createElement("div", { className: "month-head" },
                React.createElement("h3", null, label),
                React.createElement("span", { className: "m-count" }, items.length),
                React.createElement("div", { className: "m-line" }),
                React.createElement("button", { className: "month-select", onClick: () => { setSelMode(true); selectAll(items.map((i) => i.id)); } }, "Alle auswählen")),
              React.createElement("div", { className: "grid", style: { display: "flex", flexWrap: "wrap" } },
                items.map((a) => React.createElement(Cell, {
                  key: a.id, a, base, selected: sel.has(a.id), selMode,
                  onOpen: openWithOrder, onToggleSel: () => toggleSel(a.id), onFav,
                })),
                // spacer to keep last row left-aligned
                React.createElement("div", { style: { flexGrow: 10, flexBasis: 0 } })))),

        React.createElement("div", { style: { height: 40 } })));
  }

  window.Gallery = Gallery;
})();
