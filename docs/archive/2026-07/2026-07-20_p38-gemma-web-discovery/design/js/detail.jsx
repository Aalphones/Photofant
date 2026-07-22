/* Photofant — detail lightbox (faces, versions, tags, generation meta) */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar, scoreClass } = window.UI;
  const { useState, useEffect, useMemo, useRef } = React;

  // Zoomable / pannable image stage.
  //  · Mausrad → Zoom auf Cursor   · Ziehen → Verschieben (gezoomt)
  //  · Doppelklick → Zoom umschalten · Touch: Auseinander-/Zusammenziehen → Zoom
  function ZoomImg({ asset }) {
    const wrapRef = useRef(null);
    const innerRef = useRef(null);
    const st = useRef({ s: 1, tx: 0, ty: 0 });
    const pointers = useRef(new Map());
    const pinchDist = useRef(null);
    const [, force] = useState(0);
    const MAX = 6;

    const apply = () => {
      const el = innerRef.current;
      if (el) el.style.transform = "translate(" + st.current.tx + "px," + st.current.ty + "px) scale(" + st.current.s + ")";
    };
    const clampT = () => {
      const r = wrapRef.current.getBoundingClientRect();
      const minX = r.width - st.current.s * r.width;
      const minY = r.height - st.current.s * r.height;
      st.current.tx = Math.min(0, Math.max(minX, st.current.tx));
      st.current.ty = Math.min(0, Math.max(minY, st.current.ty));
    };
    const reset = () => { st.current = { s: 1, tx: 0, ty: 0 }; apply(); force((n) => n + 1); };
    const zoomAt = (cx, cy, factor) => {
      const old = st.current.s;
      const s2 = Math.min(MAX, Math.max(1, old * factor));
      if (s2 === old) return;
      st.current.tx = cx - (s2 / old) * (cx - st.current.tx);
      st.current.ty = cy - (s2 / old) * (cy - st.current.ty);
      st.current.s = s2;
      if (s2 <= 1.001) { st.current.tx = 0; st.current.ty = 0; }
      clampT(); apply(); force((n) => n + 1);
    };

    useEffect(() => { reset(); }, [asset.id]);

    // native, non-passive wheel handler so preventDefault works
    useEffect(() => {
      const el = wrapRef.current;
      if (!el) return;
      const h = (e) => {
        e.preventDefault();
        const r = el.getBoundingClientRect();
        zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.2 : 1 / 1.2);
      };
      el.addEventListener("wheel", h, { passive: false });
      return () => el.removeEventListener("wheel", h);
    }, []);

    const onPointerDown = (e) => {
      wrapRef.current.setPointerCapture && wrapRef.current.setPointerCapture(e.pointerId);
      pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pointers.current.size === 2) {
        const p = [...pointers.current.values()];
        pinchDist.current = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
      }
      if (st.current.s > 1) force((n) => n + 1); // → grabbing cursor
    };
    const onPointerMove = (e) => {
      const prev = pointers.current.get(e.pointerId);
      if (!prev) return;
      pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const pts = [...pointers.current.values()];
      if (pts.length >= 2) {
        const r = wrapRef.current.getBoundingClientRect();
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
        if (pinchDist.current) {
          const mx = (pts[0].x + pts[1].x) / 2 - r.left;
          const my = (pts[0].y + pts[1].y) / 2 - r.top;
          zoomAt(mx, my, dist / pinchDist.current);
        }
        pinchDist.current = dist;
      } else if (st.current.s > 1) {
        st.current.tx += e.clientX - prev.x;
        st.current.ty += e.clientY - prev.y;
        clampT(); apply();
      }
    };
    const onPointerUp = (e) => {
      pointers.current.delete(e.pointerId);
      if (pointers.current.size < 2) pinchDist.current = null;
      force((n) => n + 1);
    };
    const onDoubleClick = (e) => {
      if (st.current.s > 1) { reset(); return; }
      const r = wrapRef.current.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, 2.6);
    };

    const zoomed = st.current.s > 1.001;
    const maxW = "min(calc(100vw - 372px - 110px), 78vh * " + (asset.ar.w / asset.ar.h) + ")";

    return React.createElement("div", {
      ref: wrapRef,
      className: "lb-img" + (zoomed ? " zoomed" : ""),
      style: { width: maxW, aspectRatio: asset.ar.w + " / " + asset.ar.h, touchAction: "none" },
      onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp, onDoubleClick,
    },
      React.createElement("div", { ref: innerRef, className: "lb-zoom-inner", style: { position: "absolute", inset: 0, transformOrigin: "0 0" } },
        React.createElement(Img, { src: asset.photoLg, bg: asset.bg, style: { position: "absolute", inset: 0 } })),

      zoomed && React.createElement("div", {
        className: "lb-zoom-pill",
        title: "Zoom zurücksetzen",
        onPointerDown: (e) => e.stopPropagation(),
        onClick: reset,
      }, Math.round(st.current.s * 100) + "%", React.createElement(Icon, { name: "x", size: 12 })));
  }

  function Section({ title, action, onAction, children }) {
    return React.createElement("div", { className: "panel-sec" },
      React.createElement("div", { className: "psec-title" }, title,
        action && React.createElement("span", { className: "pt-act", onClick: onAction }, action)),
      children);
  }

  // build the top-10 disjoint persons (best per person) for a face
  function topMatches(asset) {
    const r = PF.rng(asset.id * 31 + 7);
    const base = asset.personId >= 0 ? asset.personId : 0;
    const others = PF.PERSONS.map((p) => p.id).filter((id) => id !== base);
    // shuffle
    for (let i = others.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [others[i], others[j]] = [others[j], others[i]]; }
    const list = [];
    if (asset.personId >= 0) list.push({ id: base, score: 0.9 + r() * 0.09 });
    others.slice(0, 4).forEach((id, i) => list.push({ id, score: 0.78 - i * 0.09 - r() * 0.04 }));
    return list.sort((a, b) => b.score - a.score);
  }

  // ---- editing helpers ----

  // Searchable person picker: top-5 quick matches + full searchable directory.
  // Scales to a large roster (hundreds of known faces).
  function PersonPicker({ matches, currentId, onPick, onClose, title }) {
    const [q, setQ] = useState("");
    const ql = q.trim().toLowerCase();
    const dir = PF.DIRECTORY;
    const list = ql ? dir.filter((p) => p.name.toLowerCase().includes(ql)) : dir;
    const top = ql ? [] : (matches || []).slice(0, 5);
    const choose = (id) => { onPick(id); onClose(); };
    return React.createElement("div", { className: "op-scrim", onClick: onClose },
      React.createElement("div", { className: "op-modal pp-modal", onClick: (e) => e.stopPropagation() },
        React.createElement("div", { className: "op-head" },
          React.createElement(Icon, { name: "face", size: 16 }),
          React.createElement("div", { style: { fontWeight: 600, fontSize: 14 } }, title || "Person zuordnen"),
          React.createElement("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: onClose },
            React.createElement(Icon, { name: "x", size: 14 }))),
        React.createElement("div", { className: "op-search" },
          React.createElement(Icon, { name: "search", size: 15 }),
          React.createElement("input", { autoFocus: true, value: q, placeholder: "Person suchen … (" + dir.length + " bekannte Gesichter)", onChange: (e) => setQ(e.target.value) })),
        top.length > 0 && React.createElement("div", { className: "pp-quick-wrap" },
          React.createElement("div", { className: "pp-sec-lbl" }, "Top-Treffer"),
          React.createElement("div", { className: "pp-quick" },
            top.map((m) => React.createElement("button", {
              key: m.id, className: "pp-chip" + (m.id === currentId ? " sel" : ""), onClick: () => choose(m.id),
            },
              React.createElement(Avatar, { personId: m.id, size: 44 }),
              React.createElement("div", { className: "pp-chip-name" }, PF.personName(m.id)),
              React.createElement("span", { className: "score-pill " + scoreClass(m.score) }, Math.round(m.score * 100) + "%"))))),
        React.createElement("div", { className: "pp-list" },
          (!ql || "unbekannt".includes(ql)) && React.createElement("button", {
            className: "pp-row" + (currentId === -1 ? " sel" : ""), onClick: () => choose(-1),
          },
            React.createElement("div", { className: "pp-row-av unknown" }, React.createElement(Icon, { name: "face", size: 18 })),
            React.createElement("div", { className: "pp-row-name" }, "Unbekannt"),
            currentId === -1 && React.createElement(Icon, { name: "check", size: 15, style: { color: "var(--accent)" } })),
          list.length === 0 && React.createElement("div", { className: "pp-empty" }, "Keine Person gefunden für „" + q + "“"),
          list.map((p) => React.createElement("button", {
            key: p.id, className: "pp-row" + (p.id === currentId ? " sel" : ""), onClick: () => choose(p.id),
          },
            React.createElement(Avatar, { personId: p.id, size: 34 }),
            React.createElement("div", { className: "pp-row-name" }, p.name),
            p.count > 0 && React.createElement("span", { className: "pp-row-count" }, p.count + " Foto" + (p.count === 1 ? "" : "s")),
            p.id === currentId && React.createElement(Icon, { name: "check", size: 15, style: { color: "var(--accent)", marginLeft: p.count > 0 ? 0 : "auto" } })))))); 
  }

  // small round pencil/affordance button
  function EditBtn({ icon = "pencil", title, onClick }) {
    return React.createElement("button", {
      className: "edit-ibtn", title: title || "Bearbeiten",
      onClick: (e) => { e.stopPropagation(); onClick(); },
    }, React.createElement(Icon, { name: icon, size: 13 }));
  }

  // overlay to manually assign an original source image
  function OriginalPicker({ assets, currentId, onPick, onClose }) {
    const [q, setQ] = useState("");
    const originals = useMemo(() =>
      assets.filter((a) => a.source === "original"), [assets]);
    const list = originals.filter((a) =>
      !q || ("" + a.id).includes(q) || (a.caption || "").toLowerCase().includes(q.toLowerCase()));
    return React.createElement("div", { className: "op-scrim", onClick: onClose },
      React.createElement("div", { className: "op-modal", onClick: (e) => e.stopPropagation() },
        React.createElement("div", { className: "op-head" },
          React.createElement(Icon, { name: "link", size: 16 }),
          React.createElement("div", { style: { fontWeight: 600, fontSize: 14 } }, "Originalvorlage zuordnen"),
          React.createElement("button", { className: "edit-ibtn", style: { marginLeft: "auto" }, onClick: onClose },
            React.createElement(Icon, { name: "x", size: 14 }))),
        React.createElement("div", { className: "op-search" },
          React.createElement(Icon, { name: "search", size: 15 }),
          React.createElement("input", { autoFocus: true, value: q, placeholder: "Suche nach ID oder Caption…", onChange: (e) => setQ(e.target.value) })),
        React.createElement("div", { className: "op-grid" },
          currentId != null && React.createElement("button", { className: "op-clear", onClick: () => { onPick(null); onClose(); } },
            React.createElement(Icon, { name: "x", size: 14 }), "Zuordnung entfernen"),
          list.map((a) => React.createElement("button", {
            key: a.id, className: "op-cell" + (a.id === currentId ? " sel" : ""),
            onClick: () => { onPick(a.id); onClose(); },
          },
            React.createElement(Img, { src: a.photo, bg: a.bg }),
            React.createElement("span", { className: "op-id" }, "#" + a.id),
            a.id === currentId && React.createElement("span", { className: "op-chk" }, React.createElement(Icon, { name: "check", size: 12 })))))));
  }

  function Lightbox({ asset, index, total, onClose, onPrev, onNext, onToggleFav, onUpdateTags, onUpdateAsset, allAssets, onImport, onEdit, onOpenKnowledge, onJumpTo }) {
    const [showMeta, setShowMeta] = useState(asset.source !== "original");
    const [curVer, setCurVer] = useState(asset.versions.findIndex((v) => v.current));
    const [adding, setAdding] = useState(false);
    const [newTag, setNewTag] = useState("");
    const [editCap, setEditCap] = useState(false);
    const [capDraft, setCapDraft] = useState(asset.caption);
    const [editFace, setEditFace] = useState(-1);
    const [relPick, setRelPick] = useState(null); // null | "origin" | "edits"
    const [verDrag, setVerDrag] = useState(false);
    const [showCompare, setShowCompare] = useState(false);
    const [tab, setTab] = useState("overview");
    const matches = useMemo(() => topMatches(asset), [asset.id]);
    // header person = the first detected face (read-only display)
    const headPid = asset.faces.length ? asset.faces[0].personId : asset.personId;

    useEffect(() => {
      setCurVer(asset.versions.findIndex((v) => v.current));
      setShowMeta(asset.source !== "original");
      setEditCap(false); setEditFace(-1); setRelPick(null);
      setCapDraft(asset.caption); setTab("overview");
    }, [asset.id]);

    useEffect(() => {
      const h = (e) => {
        if (e.key === "Escape") {
          if (editFace >= 0) { setEditFace(-1); return; }
          if (relPick) { setRelPick(null); return; }
          if (editCap) { setEditCap(false); return; }
          onClose();
        }
        else if (e.key === "ArrowLeft") onPrev();
        else if (e.key === "ArrowRight") onNext();
        else if (e.key.toLowerCase() === "f" && editFace < 0 && !relPick && !editCap) onToggleFav(asset.id);
      };
      window.addEventListener("keydown", h);
      return () => window.removeEventListener("keydown", h);
    }, [asset.id, editFace, relPick, editCap]);

    const removeTag = (name) => onUpdateTags(asset.id, asset.tags.filter((t) => t.name !== name));
    const addTag = () => {
      const v = newTag.trim().toLowerCase();
      if (v && !asset.tags.some((t) => t.name === v)) onUpdateTags(asset.id, [...asset.tags, { name: v, kind: "manual" }]);
      setNewTag(""); setAdding(false);
    };
    const saveCaption = () => {
      const v = capDraft.trim();
      if (v && v !== asset.caption) onUpdateAsset(asset.id, { caption: v, captioner: "Manuell bearbeitet" });
      setEditCap(false);
    };
    const setFacePerson = (i, pid) => {
      onUpdateAsset(asset.id, { faces: asset.faces.map((f, j) => j === i ? { ...f, personId: pid, manual: true } : f) });
      setEditFace(-1);
    };
    const removeFace = (i) => onUpdateAsset(asset.id, { faces: asset.faces.filter((_, j) => j !== i) });
    const setSource = (s) => onUpdateAsset(asset.id, { source: s });
    const setFraming = (f) => onUpdateAsset(asset.id, { framing: f });
    const setOriginal = (oid) => onUpdateAsset(asset.id, { originalId: oid });
    // edits that point at THIS asset as their original
    const linkedEdits = allAssets.filter((a) => a.originalId === asset.id);
    const openNewVersion = () => onImport && onImport({ source: "relation", relAssetId: asset.id, role: asset.source === "original" ? "edit" : "original" });
    const onVerDrop = (e) => { e.preventDefault(); setVerDrag(false); openNewVersion(); };

    const sceneName = PF.SCENES[asset.scene].name;
    const meta = asset.generationMeta;
    const tabs = [
      { id: "overview", label: "Übersicht" },
      { id: "people", label: "Gesichter", count: asset.faces.length },
      { id: "versions", label: "Versionen", count: asset.versions.length },
      { id: "wissen", label: "Wissen" },
      { id: "details", label: "Details" },
    ];
    const know = headPid >= 0 ? PF.KNOWLEDGE[headPid] : null;
    const knowSugg = headPid >= 0 ? PF.KNOWLEDGE_SUGGESTIONS[headPid] : null;
    const relatedPics = headPid >= 0 ? allAssets.filter((a) => a.id !== asset.id && (a.personId === headPid || a.faces.some((f) => f.personId === headPid))).slice(0, 9) : [];

    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "lb-scrim", onClick: onClose }),
      React.createElement("div", { className: "lb" },
        // ---------- stage ----------
        React.createElement("div", { className: "lb-stage" },
          React.createElement("button", { className: "lb-nav lb-close", style: { position: "absolute", top: 16, left: 18, transform: "none" }, onClick: onClose },
            React.createElement(Icon, { name: "x", size: 20 })),
          React.createElement("div", { className: "lb-toolbar" },
            React.createElement("button", { className: "lb-tool" + (asset.favourite ? " on" : ""), title: "Favorit (F)", onClick: () => onToggleFav(asset.id) },
              React.createElement(Icon, { name: "star", size: 18, fill: asset.favourite })),
            React.createElement("button", { className: "lb-tool", title: "Vergleichen", onClick: () => setShowCompare(true) }, React.createElement(Icon, { name: "compare", size: 18 }))),
          React.createElement("button", { className: "lb-nav prev", onClick: onPrev }, React.createElement(Icon, { name: "arrowLeft", size: 22 })),
          React.createElement("button", { className: "lb-nav next", onClick: onNext }, React.createElement(Icon, { name: "arrowRight", size: 22 })),
          React.createElement(ZoomImg, { asset }),
        ),

        // ---------- panel ----------
        React.createElement("div", { className: "panel" },
          // fixed header: person + date
          React.createElement("div", { className: "panel-sec panel-fixed", style: { display: "flex", alignItems: "center", gap: 12 } },
            React.createElement(Avatar, { personId: headPid, size: 40 }),
            React.createElement("div", { style: { minWidth: 0, flex: 1 } },
              React.createElement("div", { style: { fontWeight: 600, fontSize: 14 } }, PF.personName(headPid)),
              React.createElement("div", { style: { fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" } },
                asset.date.toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" }) + " · " +
                asset.date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }))),
            React.createElement("div", { style: { marginLeft: "auto", display: "flex", gap: 6 } },
              asset.favourite && React.createElement("span", { style: { color: "var(--gold)" } }, React.createElement(Icon, { name: "star", size: 18, fill: true })))),

          // tab bar
          React.createElement("div", { className: "panel-tabs" },
            tabs.map((t) => React.createElement("button", {
              key: t.id, className: "panel-tab" + (tab === t.id ? " on" : ""), onClick: () => setTab(t.id),
            }, t.label, t.count != null && React.createElement("span", { className: "ptc" }, t.count)))),

          // scrollable content
          React.createElement("div", { className: "panel-body" },
          tab === "overview" && React.createElement(React.Fragment, null,
          // caption (editable)
          React.createElement(Section, { title: "Caption", action: editCap ? null : "Bearbeiten", onAction: () => { setCapDraft(asset.caption); setEditCap(true); } },
            editCap
              ? React.createElement("div", { className: "cap-edit" },
                  React.createElement("textarea", {
                    autoFocus: true, value: capDraft, rows: 3,
                    onChange: (e) => setCapDraft(e.target.value),
                    onKeyDown: (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) saveCaption(); if (e.key === "Escape") setEditCap(false); },
                  }),
                  React.createElement("div", { className: "cap-edit-row" },
                    React.createElement("button", { className: "mini-btn", onClick: () => setEditCap(false) }, "Abbrechen"),
                    React.createElement("button", { className: "mini-btn primary", onClick: saveCaption }, React.createElement(Icon, { name: "check", size: 13 }), "Speichern")))
              : React.createElement(React.Fragment, null,
                  React.createElement("div", { className: "caption-txt" }, asset.caption),
                  React.createElement("div", { className: "caption-src" }, "↳ " + asset.captioner))),

          // tags
          React.createElement(Section, { title: "Tags · " + asset.tags.length },
            React.createElement("div", { className: "tagwrap" },
              asset.tags.map((t) => React.createElement("span", { key: t.name, className: "tg" + (t.kind === "manual" ? " manual" : "") },
                t.name,
                React.createElement("span", { className: "tx", onClick: () => removeTag(t.name) }, React.createElement(Icon, { name: "x", size: 12 })))),
              adding
                ? React.createElement("input", {
                    autoFocus: true, className: "tg", style: { width: 110, outline: "none", color: "var(--text)" },
                    value: newTag, placeholder: "tag…",
                    onChange: (e) => setNewTag(e.target.value),
                    onKeyDown: (e) => { if (e.key === "Enter") addTag(); if (e.key === "Escape") { setAdding(false); setNewTag(""); } },
                    onBlur: addTag,
                  })
                : React.createElement("span", { className: "tg tg-add", onClick: () => setAdding(true) },
                    React.createElement(Icon, { name: "plus", size: 12 }), "Tag")))),

          tab === "people" && React.createElement(Section, { title: "Gesichter · " + asset.faces.length },
            React.createElement("div", { className: "faces-strip", style: { marginBottom: asset.faces.length ? 14 : 0 } },
              asset.faces.map((f, i) => React.createElement("div", { className: "face-item ed-row", key: i },
                React.createElement("div", { className: "face-thumb" },
                  React.createElement(Img, { src: f.cropUrl || PF.personPhoto(f.personId), bg: PF.personBg(f.personId) }),
                  React.createElement("div", { style: { position: "absolute", inset: 0, boxShadow: "inset 0 0 0 2px " + (f.manual ? "var(--good)" : "var(--accent-line)") } }),
                  React.createElement("button", { className: "face-del", title: "Gesicht entfernen", onClick: () => removeFace(i) },
                    React.createElement(Icon, { name: "x", size: 11 }))),
                React.createElement("div", { className: "face-name face-name-ed", onClick: () => setEditFace(i), title: "Person zuordnen" },
                  PF.personName(f.personId), React.createElement(Icon, { name: "pencil", size: 11, style: { opacity: .5 } })),
                React.createElement("div", { className: "face-score" }, (f.manual ? "manuell" : Math.round(f.score * 100) + "%") + " · " + f.age + "J")))),
            // top-5 quick matches for first face
            asset.faces.length > 0 && React.createElement(React.Fragment, null,
              React.createElement("div", { style: { fontSize: 10.5, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--text-3)", marginBottom: 8, marginTop: 8 } }, "Beste Treffer — Schnellzuweisung"),
              React.createElement("div", { className: "quick-assign", style: { display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 } },
                matches.slice(0, 5).map((m) => React.createElement("button", {
                  key: m.id, className: "quick-match", onClick: () => setFacePerson(0, m.id), title: "Person für Gesicht 1 zuweisen",
                },
                  React.createElement("div", { style: { position: "relative", width: 48, height: 48, borderRadius: 6, overflow: "hidden", flex: "none" } },
                    React.createElement(Img, { src: PF.personPhoto(m.id), bg: PF.personBg(m.id) })),
                  React.createElement("div", { className: "qm-label" }, PF.personName(m.id).split(" ")[0]),
                  React.createElement("div", { className: "qm-score" }, Math.round(m.score * 100) + "%"))))),
            // show more detailed matches + full search option
            React.createElement("div", { className: "face-assign-opts", style: { marginTop: 12, display: "flex", gap: 6 } },
              React.createElement("button", { className: "mini-btn", onClick: () => setEditFace(asset.faces.length > 0 ? 0 : -1) }, "Weitere Personen…"),
              asset.faces.length > 1 && React.createElement("button", { className: "mini-btn", onClick: () => setEditFace(-1) }, "Weitere Gesichter…"))),

          tab === "versions" && React.createElement(React.Fragment, null,
          React.createElement(Section, { title: "Versionen · " + asset.versions.length, action: "Vergleichen" },
            React.createElement("div", { className: "vers" },
              asset.versions.map((v, i) => React.createElement("div", {
                key: i, className: "vrow" + (i === curVer ? " cur" : ""), onClick: () => setCurVer(i),
              },
                React.createElement("div", { className: "vthumb" },
                  React.createElement(Img, { src: asset.photo, bg: asset.bg }),
                  v.type === "upscale" && React.createElement("div", { style: { position: "absolute", inset: 0, boxShadow: "inset 0 0 0 2px oklch(0.50 0.13 152 / .8)" } })),
                React.createElement("div", { style: { minWidth: 0, flex: 1 } },
                  React.createElement("div", { className: "vname" }, v.label,
                    i === curVer && React.createElement("span", { className: "vtag cur" }, "aktiv")),
                  React.createElement("div", { className: "vmeta" }, v.res + " · " + v.when.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit" }) +
                    (v.params && v.params.strength ? " · str " + v.params.strength : "") +
                    (v.params && v.params.model ? " · " + v.params.model : ""))),
                React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28 }, onClick: (e) => e.stopPropagation() },
                  React.createElement(Icon, { name: "rotate", size: 14 }))))),
            React.createElement("button", {
              className: "lb-newver" + (verDrag ? " drag" : ""), title: "Neue Version importieren",
              onClick: openNewVersion,
              onDragEnter: (e) => { e.preventDefault(); setVerDrag(true); }, onDragOver: (e) => e.preventDefault(),
              onDragLeave: (e) => { e.preventDefault(); setVerDrag(false); }, onDrop: onVerDrop,
            },
              React.createElement("div", { className: "nv-ico" }, React.createElement(Icon, { name: "upload", size: 16 })),
              React.createElement("div", { style: { minWidth: 0, flex: 1 } },
                React.createElement("div", { className: "nv-t" }, "Neue Version ergänzen"),
                React.createElement("div", { className: "nv-s" }, asset.source === "original" ? "Edit hierher ziehen oder klicken" : "Original/Edit hierher ziehen oder klicken")))),

          // relations: original + linked edits (retroactively add/remove)
          React.createElement(Section, { title: "Beziehungen" },
            React.createElement("div", { className: "rel-dir-lbl", style: { margin: "0 0 7px" } }, "Originalvorlage"),
            asset.originalId != null && allAssets.find((a) => a.id === asset.originalId)
              ? (() => { const o = allAssets.find((a) => a.id === asset.originalId); return React.createElement("div", { className: "rel-row" },
                  React.createElement("div", { className: "rr-thumb" }, React.createElement(Img, { src: o.photo, bg: o.bg })),
                  React.createElement("div", { className: "rr-body" },
                    React.createElement("div", { className: "rr-id" }, "#" + o.id, React.createElement("span", { className: "rel-tag orig" }, "Original")),
                    React.createElement("div", { className: "rr-cap" }, o.caption)),
                  React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28 }, title: "Anderes Original wählen", onClick: () => setRelPick("origin") }, React.createElement(Icon, { name: "pencil", size: 13 })),
                  React.createElement("button", { className: "rr-x", title: "Zuordnung entfernen", onClick: () => setOriginal(null) }, React.createElement(Icon, { name: "x", size: 15 }))); })()
              : React.createElement("button", { className: "rel-add", style: { height: 42 }, onClick: () => setRelPick("origin") }, React.createElement(Icon, { name: "link", size: 15 }), "Original zuordnen"),
            React.createElement("div", { className: "rel-dir-lbl", style: { margin: "14px 0 7px" } }, "Verknüpfte Edits · " + linkedEdits.length),
            linkedEdits.map((e) => React.createElement("div", { className: "rel-row", key: e.id },
              React.createElement("div", { className: "rr-thumb" }, React.createElement(Img, { src: e.photo, bg: e.bg })),
              React.createElement("div", { className: "rr-body" },
                React.createElement("div", { className: "rr-id" }, "#" + e.id, React.createElement("span", { className: "rel-tag edit" }, PF.sourceLabel(e.source))),
                React.createElement("div", { className: "rr-cap" }, e.caption)),
              React.createElement("button", { className: "rr-x", title: "Verknüpfung entfernen", onClick: () => onUpdateAsset(e.id, { originalId: null }) }, React.createElement(Icon, { name: "x", size: 15 })))),
            React.createElement("button", { className: "rel-add", style: { height: 42, marginTop: linkedEdits.length ? 4 : 0 }, onClick: () => setRelPick("edits") }, React.createElement(Icon, { name: "plus", size: 15 }), "Edit verknüpfen"))),

          tab === "wissen" && React.createElement(React.Fragment, null,
          headPid < 0
            ? React.createElement(Section, { title: "Wissen" },
                React.createElement("div", { className: "kw-empty-txt", style: { padding: 0 } }, "Keine Person zugeordnet — im Tab „Gesichter“ zuordnen, um Wissen anzuzeigen."))
            : !know
              ? React.createElement(Section, { title: "Wissen" },
                  React.createElement("p", { className: "kw-empty-txt", style: { padding: 0 } }, "Noch kein Wissen zu " + PF.personName(headPid) + " angelegt."),
                  React.createElement("button", { className: "mini-btn primary", onClick: () => onOpenKnowledge && onOpenKnowledge(headPid) },
                    React.createElement(Icon, { name: "sparkle", size: 13 }), "Interview starten"))
              : React.createElement(React.Fragment, null,
                  React.createElement(Section, { title: "Wissen · " + Math.round(know.completeness * 100) + "%", action: "Vollständiges Profil", onAction: () => onOpenKnowledge && onOpenKnowledge(headPid) },
                    React.createElement("p", { className: "caption-txt" }, know.body),
                    knowSugg && React.createElement("div", { className: "kw-ai-banner", style: { marginTop: 12 } },
                      React.createElement(Icon, { name: "sparkle", size: 14 }),
                      React.createElement("div", { className: "kw-ai-txt" }, knowSugg.text))),
                  relatedPics.length > 0 && React.createElement(Section, { title: "Ähnliche Bilder · " + relatedPics.length },
                    React.createElement("div", { className: "kw-photo-grid" },
                      relatedPics.map((a) => React.createElement("div", {
                        className: "kw-photo-cell", key: a.id, onClick: () => onJumpTo && onJumpTo(a.id),
                      }, React.createElement(Img, { src: a.photo, bg: a.bg })))))),
          ),

          tab === "details" && React.createElement(React.Fragment, null,
          React.createElement(Section, { title: "Metadaten" },
            React.createElement("dl", { className: "kv" },
              React.createElement("dt", null, "Quelle"),
              React.createElement("dd", null,
                React.createElement("select", { className: "kv-select", value: asset.source, onChange: (e) => setSource(e.target.value) },
                  ["original", "sdxl", "flux"].map((s) => React.createElement("option", { key: s, value: s }, PF.sourceLabel(s))))),
              React.createElement("dt", null, "Originalvorlage"),
              React.createElement("dd", null,
                asset.originalId != null
                  ? React.createElement("span", { className: "orig-chip" },
                      React.createElement("span", { className: "orig-thumb" }, React.createElement(Img, { src: (allAssets.find((a) => a.id === asset.originalId) || asset).photo, bg: asset.bg })),
                      "#" + asset.originalId,
                      React.createElement("button", { className: "orig-x", title: "Zuordnung ändern", onClick: () => setRelPick("origin") }, React.createElement(Icon, { name: "pencil", size: 11 })))
                  : React.createElement("button", { className: "orig-link", onClick: () => setRelPick("origin") },
                      React.createElement(Icon, { name: "link", size: 13 }), "Zuordnen")),
              React.createElement("dt", null, "Framing"),
              React.createElement("dd", null,
                React.createElement("select", { className: "kv-select", value: asset.framing, onChange: (e) => setFraming(e.target.value) },
                  ["close_up", "medium", "full_body"].map((f) => React.createElement("option", { key: f, value: f }, PF.framingLabel(f))))),
              React.createElement("dt", null, "Auflösung"), React.createElement("dd", null, asset.dims.w + "×" + asset.dims.h),
              React.createElement("dt", null, "Seitenverhältnis"), React.createElement("dd", null, asset.ar.w + ":" + asset.ar.h),
              React.createElement("dt", null, "Format"), React.createElement("dd", null, asset.format.toUpperCase()),
              React.createElement("dt", null, "Größe"), React.createElement("dd", null, (asset.fileSize / 1024).toFixed(1) + " MB"),
              React.createElement("dt", null, "Qualität"), React.createElement("dd", null,
                React.createElement("span", { style: { color: asset.quality > 0.75 ? "var(--good)" : asset.quality > 0.55 ? "var(--warn)" : "var(--text-2)" } }, Math.round(asset.quality * 100) + " / 100")),
              React.createElement("dt", null, "Hash"), React.createElement("dd", { style: { color: "var(--text-3)" } }, "sha256:" + (asset.id * 8821 + 100003).toString(16).padStart(8, "0").slice(0, 8) + "…"))),

          // generation meta viewer
          meta && React.createElement("div", { className: "panel-sec" },
            React.createElement("div", { className: "psec-title", style: { cursor: "pointer" }, onClick: () => setShowMeta((s) => !s) },
              React.createElement(Icon, { name: "sparkle", size: 13 }), "Generierungs-Metadaten",
              React.createElement("span", { className: "chev", style: { marginLeft: "auto", color: "var(--text-3)", transform: showMeta ? "" : "rotate(-90deg)" } }, React.createElement(Icon, { name: "chevronDown", size: 14 }))),
            showMeta && React.createElement("div", { className: "gmeta" },
              React.createElement("div", null, React.createElement("span", { className: "gk" }, "model: "), meta.model),
              React.createElement("div", null, React.createElement("span", { className: "gk" }, "sampler: "), meta.sampler, "  ",
                React.createElement("span", { className: "gk" }, "steps: "), meta.steps, "  ",
                React.createElement("span", { className: "gk" }, "cfg: "), meta.cfg),
              React.createElement("div", null, React.createElement("span", { className: "gk" }, "seed: "), meta.seed, "  ",
                React.createElement("span", { className: "gk" }, "size: "), meta.size),
              React.createElement("span", { className: "gk" }, "prompt:"),
              React.createElement("span", { className: "prompt" }, meta.prompt))))),

          // actions
          React.createElement("div", { className: "pbtn-row" },
            React.createElement("button", { className: "pbtn ghost" }, React.createElement(Icon, { name: "crop", size: 16 }), "Bearbeiten"),
            React.createElement("button", { className: "pbtn primary" }, React.createElement(Icon, { name: "export", size: 16 }), "Exportieren")))),
      relPick === "origin" && React.createElement(window.RelationBrowser, {
        assets: allAssets, multi: false,
        title: "Originalvorlage zuordnen", subtitle: "Wähle das Original-Bild zu diesem Edit",
        initialSelected: asset.originalId != null ? [asset.originalId] : [],
        excludeIds: [asset.id], defaultSource: "original", confirmLabel: "Als Original zuordnen",
        onConfirm: (ids) => { setOriginal(ids.length ? ids[0] : null); setRelPick(null); },
        onClose: () => setRelPick(null),
      }),
      relPick === "edits" && React.createElement(window.RelationBrowser, {
        assets: allAssets, multi: true,
        title: "Edits verknüpfen", subtitle: "Wähle Bilder, die als Edit dieses Bildes gelten",
        initialSelected: linkedEdits.map((a) => a.id), excludeIds: [asset.id], confirmLabel: "Verknüpfen",
        onConfirm: (ids) => {
          const prev = new Set(linkedEdits.map((a) => a.id)); const next = new Set(ids);
          ids.forEach((id) => { if (!prev.has(id)) onUpdateAsset(id, { originalId: asset.id }); });
          linkedEdits.forEach((a) => { if (!next.has(a.id)) onUpdateAsset(a.id, { originalId: null }); });
          setRelPick(null);
        },
        onClose: () => setRelPick(null),
      }),
      showCompare && React.createElement(window.VersionCompare, {
        asset, allAssets, onClose: () => setShowCompare(false),
      }),
      editFace >= 0 && asset.faces[editFace] && React.createElement(PersonPicker, {
        matches, currentId: asset.faces[editFace].personId,
        onPick: (pid) => setFacePerson(editFace, pid), onClose: () => setEditFace(-1),
        title: "Gesicht " + (editFace + 1) + " zuordnen",
      }));
  }

  window.Lightbox = Lightbox;
})();
