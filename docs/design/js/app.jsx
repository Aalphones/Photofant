/* Photofant — app shell: nav + top bar (3-level search) + job dock + routing */
(function () {
  const { Icon, PF, Gallery, Lightbox, Albums, Models, DownloadDialog, BindDialog, CaptionerDialog, Settings, Maintenance, Editor, ReviewQueue, Training } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useEffect, useMemo, useRef } = React;

  const emptyFilters = () => ({
    persons: new Set(), sources: new Set(), framings: new Set(), tags: new Set(),
    qualityMin: 0, favOnly: false, editedOnly: false,
  });
  window.PF_EMPTY_FILTERS = emptyFilters;

  /* ---------------- nav rail ---------------- */
  function Nav({ view, setView, assets, onClose }) {
    const total = assets.length;
    const favs = assets.filter((a) => a.favourite).length;
    const items = [
      { id: "gallery", icon: "gallery", label: "Galerie", count: total },
      { id: "people", icon: "people", label: "Personen", count: PF.PERSONS.length },
      { id: "favourites", icon: "star", label: "Favoriten", count: favs },
      { id: "albums", icon: "album", label: "Alben", count: PF.COLLECTIONS.length },
      { id: "training", icon: "training", label: "Trainingssets", count: 3 },
    ];
    const tools = [
      { id: "review", icon: "face", label: "Review-Queue", count: 7 },
      { id: "trash", icon: "trash", label: "Papierkorb", count: 12 },
      { id: "models", icon: "model", label: "Modelle" },
      { id: "maintenance", icon: "wrench", label: "Wartung" },
      { id: "settings", icon: "settings", label: "Einstellungen" },
    ];
    const item = (it) => React.createElement("button", {
      key: it.id, className: "nav-item" + (view === it.id ? " active" : ""), onClick: () => setView(it.id),
    },
      React.createElement(Icon, { name: it.icon, size: 18, fill: it.id === "favourites" && view === it.id }),
      React.createElement("span", null, it.label),
      it.count != null && React.createElement("span", { className: "count" }, it.count));

    return React.createElement("nav", { className: "nav" },
      React.createElement("div", { className: "brand" },
        React.createElement("div", { className: "brand-mark" }),
        React.createElement("div", null,
          React.createElement("div", { className: "brand-name" }, "Photofant"),
          React.createElement("div", { className: "brand-sub" }, "vergisst nie")),
        React.createElement("button", { className: "iconbtn nav-close", style: { width: 32, height: 32, marginLeft: "auto" }, onClick: onClose },
          React.createElement(Icon, { name: "x", size: 18 }))),
      items.map(item),
      React.createElement("div", { className: "nav-group-label" }, "Verwaltung"),
      tools.map(item),
      React.createElement("div", { className: "nav-spacer" }),
      React.createElement("div", { className: "nav-foot" },
        React.createElement("div", { className: "storage" },
          React.createElement("div", { className: "storage-txt" },
            React.createElement("span", { style: { color: "var(--text-2)" } }, "Lokaler Speicher"),
            React.createElement("span", { className: "mono" }, "184 GB")),
          React.createElement("div", { className: "storage-bar" }, React.createElement("i", { style: { width: "58%" } })),
          React.createElement("div", { className: "storage-txt" },
            React.createElement("span", null, "78 Assets · 6 Personen"),
            React.createElement("span", null, "58%")))));
  }

  /* ---------------- search box (3 levels) ---------------- */
  const MODES = [
    { id: "tags", label: "Tags" },
    { id: "caption", label: "Caption" },
    { id: "semantic", label: "Semantisch" },
  ];
  const SUGGEST = {
    tags: ["porträt", "brille", "strand", "neonlicht", "rotes kleid"],
    caption: ["lächelt in die kamera", "goldene stunde", "studio von links"],
    semantic: ["frau im roten kleid am strand", "person mit brille bei nacht", "ähnlich wie ausgewähltes bild"],
  };
  function Search({ search, setSearch }) {
    const [focus, setFocus] = useState(false);
    const sem = search.mode === "semantic";
    return React.createElement("div", { className: "search" },
      React.createElement("div", { className: "search-box" + (sem ? " sem" : "") },
        React.createElement(Icon, { name: sem ? "sparkle" : "search", size: 16, style: { color: sem ? "var(--semantic)" : "var(--text-3)", flex: "none" } }),
        React.createElement("input", {
          value: search.q,
          placeholder: sem ? "Beschreibe das Bild in natürlicher Sprache…" : search.mode === "caption" ? "Caption-Volltext durchsuchen…" : "Nach Tags filtern…",
          onChange: (e) => setSearch({ ...search, q: e.target.value }),
          onFocus: () => setFocus(true), onBlur: () => setTimeout(() => setFocus(false), 140),
        }),
        search.q && React.createElement("button", { className: "iconbtn", style: { width: 24, height: 24 }, onClick: () => setSearch({ ...search, q: "" }) },
          React.createElement(Icon, { name: "x", size: 14 })),
        React.createElement("div", { className: "mode-pills" },
          MODES.map((m) => React.createElement("button", {
            key: m.id, className: "mode-pill" + (search.mode === m.id ? " on" : "") + (m.id === "semantic" ? " sem" : ""),
            onClick: () => setSearch({ ...search, mode: m.id }),
          }, m.label))),
        React.createElement("button", {
          className: "mode-cycle" + (sem ? " sem" : ""),
          onClick: () => { const i = MODES.findIndex((m) => m.id === search.mode); setSearch({ ...search, mode: MODES[(i + 1) % MODES.length].id }); },
        }, React.createElement(Icon, { name: sem ? "sparkle" : "filter", size: 13 }),
          search.mode === "tags" ? "Tags" : search.mode === "caption" ? "Cap." : "Sem.")),
      focus && React.createElement("div", { className: "search-hint" },
        React.createElement("div", { className: "sg-label" }, sem ? "Semantische Suche (CLIP/SigLIP)" : search.mode === "caption" ? "Caption-Volltext" : "Tag-Facetten"),
        SUGGEST[search.mode].map((s) => React.createElement("button", {
          key: s, className: "sg-item", onMouseDown: () => setSearch({ ...search, q: s }),
        }, React.createElement(Icon, { name: sem ? "sparkle" : "search", size: 14, style: { color: "var(--text-3)" } }), s)),
        sem && React.createElement("div", { className: "sg-item", style: { color: "var(--text-3)", fontSize: 11.5, paddingTop: 4 } },
          React.createElement(Icon, { name: "info", size: 13 }), "Freitext → Bild, oder „mehr wie dieses“ über Bild-Ähnlichkeit")));
  }

  /* ---------------- job dock ---------------- */
  function JobDock({ jobs, onClose }) {
    const iconFor = (k) => ({ tag: "tag", face: "face", caption: "text", download: "download" }[k] || "refresh");
    const active = jobs.filter((j) => !j.done).length;
    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "dock-scrim", onClick: onClose }),
      React.createElement("div", { className: "dock", onClick: (e) => e.stopPropagation() },
      React.createElement("div", { className: "dock-grab" }),
      React.createElement("div", { className: "dock-head" },
        React.createElement("h4", null, "Aufgaben-Queue",
          React.createElement("span", { className: "dock-count" }, active > 0 ? active + " aktiv" : "bereit")),
        React.createElement("button", { className: "iconbtn", style: { width: 30, height: 30 }, onClick: onClose }, React.createElement(Icon, { name: "x", size: 16 }))),
      React.createElement("div", { className: "dock-body" },
        jobs.map((j) => React.createElement("div", { className: "job", key: j.id },
          React.createElement("div", { className: "job-top" },
            React.createElement("div", { className: "job-ico" }, React.createElement(Icon, { name: iconFor(j.kind), size: 14 })),
            React.createElement("div", { style: { minWidth: 0 } },
              React.createElement("div", { className: "job-name" }, j.name),
              React.createElement("div", { className: "job-sub" }, j.sub)),
            React.createElement("span", { className: "job-pct" }, j.done ? "fertig" : Math.round(j.pct) + "%")),
          React.createElement("div", { className: "job-bar" + (j.done ? " done" : j.dl ? " dl" : "") },
            React.createElement("i", { style: { width: (j.done ? 100 : j.pct) + "%" } }))))),
      React.createElement("div", { className: "dock-foot" },
        React.createElement(Icon, { name: "info", size: 13 }),
        "Verarbeitung läuft lokal · offline · einmal pro Bild")));
  }

  /* ---------------- bulk action bar ---------------- */
  function BulkBar({ count, onClear, onFavAll, assets, sel }) {
    const acts = [
      { icon: "star", label: "Favorit", fn: onFavAll },
      { icon: "tag", label: "Taggen" },
      { icon: "move", label: "Person zuweisen" },
      { icon: "crop", label: "Bearbeiten" },
      { icon: "training", label: "Zu Trainingsset" },
      { icon: "export", label: "Export" },
    ];
    return React.createElement("div", { className: "bulkbar" },
      React.createElement("span", { className: "bulk-count" }, React.createElement("b", null, count), " ausgewählt"),
      React.createElement("div", { className: "divider-v" }),
      acts.map((a) => React.createElement("button", { key: a.label, className: "bulkbtn", onClick: a.fn },
        React.createElement(Icon, { name: a.icon, size: 15 }), a.label)),
      React.createElement("button", { className: "bulkbtn danger" }, React.createElement(Icon, { name: "trash", size: 15 }), "Papierkorb"),
      React.createElement("div", { className: "divider-v" }),
      React.createElement("button", { className: "bulk-x", onClick: onClear }, React.createElement(Icon, { name: "x", size: 16 })));
  }

  /* ---------------- placeholder views ---------------- */
  function PeopleView({ assets, onPickPerson, onImport }) {
    const [dragId, setDragId] = useState(null);
    const [editingId, setEditingId] = useState(null);
    const [editingName, setEditingName] = useState("");
    const [personNames, setPersonNames] = useState(() => {
      const names = {};
      PF.PERSONS.forEach((p) => { names[p.id] = p.name; });
      return names;
    });
    const [longPressId, setLongPressId] = useState(null);
    const longPressTimer = useRef(null);
    
    const cardDrop = (pid) => (e) => { e.preventDefault(); e.stopPropagation(); setDragId(null); onImport({ source: "person", personId: pid }); };
    
    const startEdit = (personId) => {
      setEditingId(personId);
      setEditingName(personNames[personId] || "");
    };
    
    const saveEdit = (personId) => {
      const trimmed = editingName.trim();
      if (trimmed && trimmed !== (personNames[personId] || "")) {
        setPersonNames((prev) => ({ ...prev, [personId]: trimmed }));
        const person = PF.PERSONS.find((p) => p.id === personId);
        if (person) person.name = trimmed;
      }
      setEditingId(null);
      setEditingName("");
    };
    
    const cancelEdit = () => {
      setEditingId(null);
      setEditingName("");
    };

    const handlePointerDown = (personId) => {
      longPressTimer.current = setTimeout(() => {
        setLongPressId(personId);
        startEdit(personId);
      }, 500);
    };

    const handlePointerUp = () => {
      if (longPressTimer.current) clearTimeout(longPressTimer.current);
    };

    const handlePointerCancel = () => {
      if (longPressTimer.current) clearTimeout(longPressTimer.current);
    };
    
    return React.createElement("div", { className: "grid-wrap" },
      React.createElement("div", { className: "month-head", style: { padding: "22px 22px 4px" } },
        React.createElement("h3", null, "Personen"), React.createElement("span", { className: "m-count" }, PF.PERSONS.length),
        React.createElement("div", { className: "m-line" }),
        React.createElement("span", { style: { fontSize: 11.5, color: "var(--text-3)" } }, PF.UNKNOWN_COUNT + " unbekannt · 7 zu prüfen"),
        React.createElement("span", { className: "person-edit-hint" }, "→ Doppelklick zum Umbenennen")),
      React.createElement("div", { className: "people-grid" },
        PF.PERSONS.map((p) => React.createElement("div", {
          className: "person-card" + (dragId === p.id ? " drop" : "") + (editingId === p.id ? " editing" : ""), 
          key: p.id, 
          onClick: () => !editingId && onPickPerson(p.id),
          onDragEnter: (e) => { e.preventDefault(); !editingId && setDragId(p.id); }, 
          onDragOver: (e) => e.preventDefault(),
          onDragLeave: (e) => { e.preventDefault(); setDragId((d) => d === p.id ? null : d); }, 
          onDrop: cardDrop(p.id),
          onPointerDown: () => handlePointerDown(p.id),
          onPointerUp: handlePointerUp,
          onPointerCancel: handlePointerCancel,
        },
          React.createElement("button", { className: "person-import", title: "In diesen Ordner importieren", onClick: (e) => { e.stopPropagation(); onImport({ source: "person", personId: p.id }); } },
            React.createElement(Icon, { name: "upload", size: 15 })),
          React.createElement("div", { className: "person-av" }, React.createElement(Img, { src: p.portrait, bg: p.avatarBg })),
          React.createElement("div", { style: { textAlign: "center" } },
            editingId === p.id
              ? React.createElement("div", { className: "person-name-edit" },
                  React.createElement("input", { 
                    type: "text", 
                    value: editingName, 
                    onChange: (e) => setEditingName(e.target.value),
                    onClick: (e) => e.stopPropagation(),
                    onKeyDown: (e) => {
                      e.stopPropagation();
                      if (e.key === "Enter") saveEdit(p.id);
                      if (e.key === "Escape") cancelEdit();
                    },
                    autoFocus: true,
                  }),
                  React.createElement("div", { className: "person-name-buttons" },
                    React.createElement("button", { 
                      className: "person-name-btn save",
                      onClick: (e) => { e.stopPropagation(); saveEdit(p.id); },
                      title: "Speichern"
                    }, "✓"),
                    React.createElement("button", { 
                      className: "person-name-btn cancel",
                      onClick: (e) => { e.stopPropagation(); cancelEdit(); },
                      title: "Abbrechen"
                    }, "✕")))
              : React.createElement("div", { 
                  className: "person-name", 
                  onDoubleClick: (e) => { e.stopPropagation(); startEdit(p.id); },
                  title: "Doppelklick zum Bearbeiten"
                }, personNames[p.id] || p.name),
            React.createElement("div", { className: "person-meta" }, p.count + " Bilder · " + p.favCount + " ★")))),
        React.createElement("div", { className: "person-card", onClick: () => onPickPerson(-1) },
          React.createElement("div", { className: "person-av", style: { display: "grid", placeItems: "center", background: "var(--surface)" } },
            React.createElement(Icon, { name: "face", size: 38, style: { color: "var(--text-3)" } })),
          React.createElement("div", { style: { textAlign: "center" } },
            React.createElement("div", { className: "person-name" }, "Unbekannt"),
            React.createElement("div", { className: "person-meta" }, PF.UNKNOWN_COUNT + " Bilder")))));
  }

  function Placeholder({ icon, title, desc }) {
    return React.createElement("div", { className: "grid-wrap" },
      React.createElement("div", { className: "placeholder-view" },
        React.createElement(Icon, { name: icon, size: 44 }),
        React.createElement("h3", null, title),
        React.createElement("p", null, desc),
        React.createElement("div", { style: { marginTop: 8, fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" } }, "in diesem Prototyp ist die Galerie ausgearbeitet")));
  }

  const VIEW_TITLES = {
    gallery: "Galerie", people: "Personen", favourites: "Favoriten", albums: "Alben",
    training: "Trainingssets", review: "Review-Queue", trash: "Papierkorb",
    models: "Modelle", maintenance: "Wartung", settings: "Einstellungen",
  };

  /* ---------------- root app ---------------- */
  /* ---------------- mobile bottom tab bar ---------------- */
  function MobNav({ view, go, favCount, onMore }) {
    const tabs = [
      { id: "gallery", icon: "gallery", label: "Galerie" },
      { id: "people", icon: "people", label: "Personen" },
      { id: "favourites", icon: "star", label: "Favoriten", badge: favCount },
    ];
    return React.createElement("nav", { className: "mobnav" },
      tabs.map((t) => React.createElement("button", {
        key: t.id, className: view === t.id ? "on" : "", onClick: () => go(t.id),
      },
        React.createElement(Icon, { name: t.icon, size: 21, fill: t.id === "favourites" && view === t.id }),
        React.createElement("span", null, t.label))),
      React.createElement("button", { className: ["albums", "training", "review", "trash", "models", "maintenance", "settings"].includes(view) ? "on" : "", onClick: onMore },
        React.createElement(Icon, { name: "rows", size: 21 }),
        React.createElement("span", null, "Mehr")));
  }

  function App() {
    const [view, setView] = useState("gallery");
    const [assets, setAssets] = useState(PF.ASSETS);
    const [F, setF] = useState(emptyFilters());
    const [search, setSearch] = useState({ q: "", mode: "tags" });
    const [sort, setSort] = useState({ key: "date", dir: "desc" });
    const [group, setGroup] = useState("month");
    const [density, setDensity] = useState("md");
    const [sel, setSel] = useState(new Set());
    const [selMode, setSelMode] = useState(false);
    const [isMobile, setIsMobile] = useState(() => typeof window !== "undefined" && window.matchMedia("(max-width: 860px)").matches);
    const [railOpen, setRailOpen] = useState(() => !(typeof window !== "undefined" && window.matchMedia("(max-width: 860px)").matches));
    const [navOpen, setNavOpen] = useState(false);
    const [lb, setLb] = useState(null); // { id, order:[] }
    const [dockOpen, setDockOpen] = useState(false);
    const [jobs, setJobs] = useState(PF.JOB_SEED);
    const [importCtx, setImportCtx] = useState(null);
    const [globalDrag, setGlobalDrag] = useState(false);
    const [mdDownload, setMdDownload] = useState(null); // { model, variant }
    const [mdBind, setMdBind]         = useState(null); // { model, slot }
    const [mdCaptioner, setMdCaptioner] = useState(null); // model
    const [editAsset, setEditAsset]   = useState(null);
    const [dupeCtx, setDupeCtx] = useState(null); // { scanAssets, label }
    const [prevView, setPrevView]     = useState("gallery");
    const openEditor = (a) => { setPrevView(view); setEditAsset(a); setView("editor"); };
    const dragDepth = useRef(0);
    const openImport = (c) => setImportCtx(c || { source: "top" });
    const pushJobs = (newJobs) => {
      setJobs((prev) => {
        const maxId = prev.reduce((m, j) => Math.max(m, j.id), 0);
        const withIds = newJobs.map((j, i) => ({ ...j, id: maxId + 1 + i }));
        return [...withIds, ...prev];
      });
      setDockOpen(true);
    };

    // track breakpoint; close drawers/overlays when crossing into mobile
    useEffect(() => {
      const mq = window.matchMedia("(max-width: 860px)");
      const on = () => { setIsMobile(mq.matches); if (mq.matches) setRailOpen(false); else { setRailOpen(true); setNavOpen(false); } };
      mq.addEventListener("change", on);
      return () => mq.removeEventListener("change", on);
    }, []);

    // live job progress
    useEffect(() => {
      const t = setInterval(() => {
        setJobs((prev) => prev.map((j) => {
          if (j.done) return j;
          const inc = j.dl ? 1.4 : 2.6 + Math.random() * 3;
          let pct = j.pct + inc;
          if (pct >= 100) return { ...j, pct: 100, done: true };
          return { ...j, pct };
        }));
      }, 700);
      return () => clearInterval(t);
    }, []);
    const activeJobs = jobs.filter((j) => !j.done).length;

    const toggleFav = (id) => setAssets((prev) => prev.map((a) => a.id === id ? { ...a, favourite: !a.favourite } : a));
    const updateTags = (id, tags) => setAssets((prev) => prev.map((a) => a.id === id ? { ...a, tags } : a));
    const updateAsset = (id, patch) => setAssets((prev) => prev.map((a) => a.id === id ? { ...a, ...patch } : a));
    const favSelected = () => { setAssets((prev) => prev.map((a) => sel.has(a.id) ? { ...a, favourite: true } : a)); };

    // favourites view = gallery with favOnly
    const effF = view === "favourites" ? { ...F, favOnly: true } : F;
    const galleryViewAssets = assets;

    // compute filtered assets (same logic as Gallery) for dupe scan
    const getFilteredAssets = () => {
      const q = search.q.trim().toLowerCase();
      return assets.filter(a => {
        if (effF.persons.size && !effF.persons.has(a.personId)) return false;
        if (effF.sources.size && !effF.sources.has(a.source)) return false;
        if (effF.framings.size && !effF.framings.has(a.framing)) return false;
        if (a.quality < effF.qualityMin) return false;
        if (effF.favOnly && !a.favourite) return false;
        if (effF.editedOnly && a.versionCount < 2) return false;
        if (effF.tags.size && ![...effF.tags].every(t => a.tags.some(x => x.name === t))) return false;
        if (q) {
          if (search.mode === "tags") { if (!a.tags.some(t => t.name.includes(q))) return false; }
          else if (search.mode === "caption") { if (!a.caption.toLowerCase().includes(q)) return false; }
          else { const hay = (a.caption + " " + a.tags.map(t => t.name).join(" ")).toLowerCase(); if (!q.split(/\s+/).some(w => hay.includes(w))) return false; }
        }
        return true;
      });
    };
    const openDupeScan = () => {
      const fa = getFilteredAssets();
      const hasPersonFilter = effF.persons.size === 1;
      const pid = hasPersonFilter ? [...effF.persons][0] : null;
      const lbl = fa.length + " Bilder" + (pid != null && pid >= 0 ? " · " + PF.personName(pid) : "");
      setDupeCtx({ scanAssets: fa, label: lbl, personId: pid >= 0 ? pid : null });
    };
    const openLb = (id, order) => setLb({ id, order });
    const lbAsset = lb && assets.find((a) => a.id === lb.id);
    const lbIndex = lb ? lb.order.indexOf(lb.id) : -1;
    const navLb = (dir) => {
      if (!lb) return;
      const ni = (lbIndex + dir + lb.order.length) % lb.order.length;
      setLb({ ...lb, id: lb.order[ni] });
    };

    const isGalleryLike = view === "gallery" || view === "favourites";
    const goView = (v) => { setView(v); setNavOpen(false); if (isMobile) setRailOpen(false); };

    // global drag&drop: drop image files anywhere → open import (plain context)
    const onGlobalDragEnter = (e) => {
      if (importCtx) return;
      if (!(e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files"))) return;
      e.preventDefault(); dragDepth.current++; setGlobalDrag(true);
    };
    const onGlobalDragLeave = (e) => { if (importCtx) return; dragDepth.current--; if (dragDepth.current <= 0) { dragDepth.current = 0; setGlobalDrag(false); } };
    const onGlobalDrop = (e) => {
      if (importCtx) return;
      if (!(e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files"))) return;
      e.preventDefault(); dragDepth.current = 0; setGlobalDrag(false);
      openImport({ source: "top" });
    };

    // Editor takes over full screen — skip the whole app shell
    if (view === "editor" && editAsset) {
      return React.createElement(Editor, { asset: editAsset, onBack: () => setView(prevView), pushJobs });
    }

    return React.createElement("div", {
      className: "app" + (navOpen ? " nav-open" : ""),
      onDragEnter: onGlobalDragEnter, onDragOver: (e) => { if (globalDrag) e.preventDefault(); }, onDragLeave: onGlobalDragLeave, onDrop: onGlobalDrop,
    },
      globalDrag && React.createElement("div", { className: "global-drop" },
        React.createElement("div", { className: "gd-pill" }, React.createElement(Icon, { name: "upload", size: 22 }),
          React.createElement("div", null,
            React.createElement("div", { style: { fontWeight: 700, fontSize: 15 } }, "Zum Importieren loslassen"),
            React.createElement("div", { style: { fontSize: 12, color: "var(--text-3)", marginTop: 2 } }, "Bilder werden lokal verarbeitet")))),
      navOpen && React.createElement("div", { className: "nav-scrim", onClick: () => setNavOpen(false) }),
      React.createElement(Nav, { view, setView: goView, assets, onClose: () => setNavOpen(false) }),
      React.createElement("div", { className: "main" },
        // top bar
        React.createElement("div", { className: "top" },
          isGalleryLike && React.createElement("button", { className: "iconbtn" + (railOpen ? " on" : ""), onClick: () => setRailOpen((o) => !o), title: "Filter" },
            React.createElement(Icon, { name: "filter", size: 18 })),
          React.createElement("div", { className: "top-title" }, VIEW_TITLES[view],
            isGalleryLike && React.createElement("span", { className: "muted" }, "  ")),
          isGalleryLike
            ? React.createElement(Search, { search, setSearch })
            : React.createElement("div", { style: { flex: 1 } }),
          React.createElement("div", { className: "top-actions" },
            React.createElement("button", { className: "selectbtn", style: { height: 36 }, onClick: () => openImport({ source: "top" }) },
              React.createElement(Icon, { name: "upload", size: 15 }), React.createElement("span", { className: "imp-lbl" }, "Importieren")),
            React.createElement("div", { className: "divider-v hide-sm" }),
            isGalleryLike && React.createElement("button", { className: "iconbtn", title: "Duplikat-Scan", onClick: openDupeScan },
              React.createElement(Icon, { name: "compare", size: 18 })),
            React.createElement("button", { className: "iconbtn hide-sm", title: "Shortcuts" }, React.createElement(Icon, { name: "keyboard", size: 18 })),
            React.createElement("div", { style: { position: "relative" } },
              React.createElement("button", { className: "jobpill" + (activeJobs > 0 ? " active" : "") + (dockOpen ? " open" : ""), onClick: () => setDockOpen((o) => !o), title: "Aufgaben-Queue", "aria-label": "Aufgaben-Queue" },
                activeJobs > 0 ? React.createElement("span", { className: "spinner" }) : React.createElement(Icon, { name: "check", size: 14, style: { color: "var(--good)" } }),
                React.createElement("span", { className: "jp-count" }, activeJobs),
                React.createElement("span", { className: "jp-word" }, activeJobs > 0 ? "aktiv" : "bereit")),
              dockOpen && React.createElement(JobDock, { jobs, onClose: () => setDockOpen(false) })))),

        // body
        isGalleryLike
          ? React.createElement(Gallery, {
              assets: galleryViewAssets, F: effF, setF: view === "favourites" ? (nf) => setF({ ...nf, favOnly: false }) : setF,
              search, onOpen: openLb, onFav: toggleFav,
              sel, setSel, selMode, setSelMode, sort, setSort, group, setGroup, density, setDensity,
              railOpen, setRailOpen, isMobile,
            })
          : view === "people"
            ? React.createElement(PeopleView, { assets, onImport: openImport, onPickPerson: (pid) => { goView("gallery"); setF({ ...emptyFilters(), persons: new Set([pid]) }); } })
            : view === "albums"
              ? React.createElement(Albums, { assets, onOpen: openLb, onFav: toggleFav })
            : view === "editor" && editAsset
              ? null /* handled by early return above */
            : view === "maintenance"
              ? React.createElement(Maintenance)
            : view === "settings"
              ? React.createElement(Settings)
            : view === "models"
              ? React.createElement(Models, {
                  onDownload: (m, v) => setMdDownload({ model: m, variant: v }),
                  onBind: (m, slot) => setMdBind({ model: m, slot }),
                  onCaptionerSettings: (m) => setMdCaptioner(m),
                })
            : view === "training"
              ? React.createElement(Training, { assets })
            : view === "review"
              ? React.createElement(ReviewQueue, { assets })
            : React.createElement(Placeholder, {
                icon: { albums: "album", training: "training", review: "face", trash: "trash", models: "model", maintenance: "wrench", settings: "settings" }[view] || "gallery",
                title: VIEW_TITLES[view],
                desc: "Dieser Bereich ist im Konzept beschrieben. Für diesen Prototyp liegt der Fokus auf der Galerie — Filter, 3-stufige Suche, Auswahl und die Detailansicht.",
              })),

      // bulk bar
      sel.size > 0 && React.createElement(BulkBar, { count: sel.size, onClear: () => { setSel(new Set()); setSelMode(false); }, onFavAll: favSelected, assets, sel }),

      // mobile bottom tab bar
      React.createElement(MobNav, { view, go: goView, favCount: assets.filter((a) => a.favourite).length, onMore: () => setNavOpen(true) }),

      // lightbox
      lbAsset && React.createElement(Lightbox, {
        asset: lbAsset, index: lbIndex, total: lb.order.length,
        onClose: () => setLb(null), onPrev: () => navLb(-1), onNext: () => navLb(1),
        onToggleFav: toggleFav, onUpdateTags: updateTags, onUpdateAsset: updateAsset, allAssets: assets,
        onImport: openImport, onEdit: openEditor,
      }),

      // dupe checker
      dupeCtx && React.createElement(window.DupeChecker, {
        scanAssets: dupeCtx.scanAssets,
        personId: dupeCtx.personId,
        label: dupeCtx.label,
        onClose: () => setDupeCtx(null),
        onUpdateAsset: updateAsset,
      }),

      // model acquisition dialogs
      mdDownload && React.createElement(window.DownloadDialog, {
        model: mdDownload.model, initialVariant: mdDownload.variant,
        onConfirm: (m, v) => {
          pushJobs([{ kind: "download", name: "Download: " + m.name, sub: v + " · " + (m.variants?.find(x=>x.id===v)?.size || ""), pct: 4, done: false }]);
        },
        onClose: () => setMdDownload(null),
      }),
      mdBind && React.createElement(window.BindDialog, {
        model: mdBind.model, initialSlot: mdBind.slot,
        onConfirm: () => {},
        onClose: () => setMdBind(null),
      }),
      mdCaptioner && React.createElement(window.CaptionerDialog, {
        model: mdCaptioner,
        onClose: () => setMdCaptioner(null),
      }),

      // import dialog
      importCtx && React.createElement(window.ImportDialog, {
        assets, context: importCtx, onClose: () => setImportCtx(null),
        onSubmit: (newJobs) => pushJobs(newJobs),
      }));
  }

  ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
})();
