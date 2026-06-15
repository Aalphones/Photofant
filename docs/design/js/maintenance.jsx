/* Photofant — Wartung (Maintenance Page)
   FS↔DB Abgleich · Thumbnail-Rebuild · Face-Rebuild  → window.Maintenance */
(function () {
  const { Icon } = window;
  const { useState, useRef } = React;

  /* ---- mock scan results ---- */
  const MOCK_ISSUES = [
    // Verwaist: in FS, not in DB
    { id: 1, type: "orphan",  path: "~/Bilder/person_03/photos/IMG_8812.jpg",       person: "Sophie Mayer",   size: "3.4 MB",  detail: "Keine DB-Eintragszeile" },
    { id: 2, type: "orphan",  path: "~/Bilder/person_03/photos/IMG_8813.jpg",       person: "Sophie Mayer",   size: "2.9 MB",  detail: "Keine DB-Eintragszeile" },
    { id: 3, type: "orphan",  path: "~/Bilder/_unknown/photos/unknown_0049.jpg",    person: "_unknown",       size: "1.8 MB",  detail: "Wahrscheinlich manuell verschoben" },
    { id: 4, type: "orphan",  path: "~/Bilder/person_11/edits/flux_edit_007.png",   person: "Leon Fischer",   size: "5.1 MB",  detail: "Edit ohne Versions-Eintrag" },
    // Fehlend: in DB, not in FS
    { id: 5, type: "missing", path: "~/Bilder/person_07/photos/DSC09173.jpg",       person: "Mia Hoffmann",   size: "4.2 MB",  detail: "asset.id=2847 · zuletzt gesehen 2026-04-18" },
    { id: 6, type: "missing", path: "~/Bilder/person_07/favourites/DSC09201.jpg",   person: "Mia Hoffmann",   size: "4.0 MB",  detail: "asset.id=2901 · Favorit" },
    { id: 7, type: "missing", path: "~/Bilder/person_02/faces/face_crop_0031.jpg",  person: "Emma Schmidt",   size: "220 KB",  detail: "face.id=441 · Face-Crop" },
    // Pfad-Drift: DB path doesn't match FS
    { id: 8, type: "drift",   path: "~/Bilder/person_05/photos/portrait_001.jpg",   person: "Jonas Weber",    size: "3.8 MB",  detail: "DB-Pfad: ~/Bilder/person_05/old/portrait_001.jpg" },
    { id: 9, type: "drift",   path: "~/Bilder/person_09/photos/session_042.jpg",    person: "Clara Bauer",    size: "2.5 MB",  detail: "DB-Pfad: ~/Dokumente/Photos/session_042.jpg" },
  ];

  const TYPE_LABEL = { orphan: "Verwaist", missing: "Fehlend", drift: "Pfad-Drift" };
  const TYPE_ICON  = { orphan: "alertTriangle", missing: "x", drift: "refresh" };

  /* ---- helpers ---- */
  function IssueRow({ issue, selected, onToggle, onAction }) {
    return React.createElement("div", { className: "mnt-issue" },
      React.createElement("div", { className: "mi-chk" + (selected ? " on" : ""), onClick: onToggle },
        selected && React.createElement(Icon, { name: "check", size: 12, stroke: 3 })),
      React.createElement("div", { className: "mi-body" },
        React.createElement("div", { className: "mi-path" }, issue.path),
        React.createElement("div", { className: "mi-meta" },
          React.createElement("span", { className: "mnt-badge " + issue.type }, TYPE_LABEL[issue.type]),
          React.createElement("span", null, issue.person),
          React.createElement("span", null, issue.size),
          React.createElement("span", null, issue.detail))),
      React.createElement("div", { className: "mi-acts" },
        issue.type === "orphan" && React.createElement(React.Fragment, null,
          React.createElement("button", { className: "mnt-btn ghost sm", onClick: () => onAction(issue, "index") },
            React.createElement(Icon, { name: "plus", size: 13 }), "Indizieren"),
          React.createElement("button", { className: "mnt-btn danger sm", onClick: () => onAction(issue, "trash") },
            React.createElement(Icon, { name: "trash", size: 13 }), "Papierkorb")),
        issue.type === "missing" && React.createElement(React.Fragment, null,
          React.createElement("button", { className: "mnt-btn warn sm", onClick: () => onAction(issue, "mark_missing") },
            React.createElement(Icon, { name: "alertTriangle", size: 13 }), "Als fehlend markieren"),
          React.createElement("button", { className: "mnt-btn danger sm", onClick: () => onAction(issue, "delete_db") },
            React.createElement(Icon, { name: "trash", size: 13 }), "DB-Eintrag löschen")),
        issue.type === "drift" && React.createElement(React.Fragment, null,
          React.createElement("button", { className: "mnt-btn ghost sm", onClick: () => onAction(issue, "update_path") },
            React.createElement(Icon, { name: "refresh", size: 13 }), "Pfad aktualisieren"),
          React.createElement("button", { className: "mnt-btn danger sm", onClick: () => onAction(issue, "delete_db") },
            React.createElement(Icon, { name: "trash", size: 13 }), "Ignorieren"))));
  }

  /* ---- scan section ---- */
  function ScanSection() {
    const [scanState, setScanState] = useState("idle"); // idle | running | done
    const [pct, setPct] = useState(0);
    const [issues, setIssues] = useState([]);
    const [tab, setTab] = useState("orphan");
    const [sel, setSel] = useState(new Set());
    const timerRef = useRef(null);
    const lastScan = "2026-06-10 · 14:32";

    const startScan = () => {
      setScanState("running"); setPct(0); setSel(new Set());
      let p = 0;
      timerRef.current = setInterval(() => {
        p += Math.random() * 14 + 6;
        if (p >= 100) { p = 100; clearInterval(timerRef.current); setScanState("done"); setIssues(MOCK_ISSUES); }
        setPct(Math.min(Math.round(p), 100));
      }, 200);
    };

    const counts = { orphan: issues.filter(i=>i.type==="orphan").length, missing: issues.filter(i=>i.type==="missing").length, drift: issues.filter(i=>i.type==="drift").length };
    const tabIssues = issues.filter(i => i.type === tab);
    const allTabSel = tabIssues.length > 0 && tabIssues.every(i => sel.has(i.id));

    const toggleSel = (id) => setSel(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
    const toggleAll = () => {
      const ids = tabIssues.map(i=>i.id);
      if (allTabSel) setSel(s => { const n = new Set(s); ids.forEach(id=>n.delete(id)); return n; });
      else setSel(s => { const n = new Set(s); ids.forEach(id=>n.add(id)); return n; });
    };

    const onAction = (issue, action) => {
      setIssues(prev => prev.filter(i => i.id !== issue.id));
      setSel(s => { const n = new Set(s); n.delete(issue.id); return n; });
    };
    const onBulkAction = (action) => {
      setIssues(prev => prev.filter(i => !sel.has(i.id)));
      setSel(new Set());
    };

    const selInTab = tabIssues.filter(i => sel.has(i.id)).length;
    const totalIssues = issues.length;

    return React.createElement("div", { className: "mnt-sec" },
      React.createElement("div", { className: "mnt-sec-head" },
        React.createElement("div", { className: "mnt-sec-ico" + (totalIssues > 0 && scanState === "done" ? " warn" : "") },
          React.createElement(Icon, { name: "refresh", size: 18 })),
        React.createElement("div", { style: { flex: 1, minWidth: 0 } },
          React.createElement("div", { className: "mnt-sec-title" }, "FS\u2194DB Abgleich"),
          React.createElement("div", { className: "mnt-sec-sub" }, "Findet verwaiste Dateien (FS vorhanden, DB fehlt), fehlende Dateien (DB vorhanden, FS fehlt) und Pfad-Drift nach manuellen Verschiebungen.")),
        React.createElement("div", { className: "mnt-sec-actions" },
          scanState !== "running" && React.createElement("button", { className: "mnt-btn accent", onClick: startScan },
            React.createElement(Icon, { name: "refresh", size: 15 }), scanState === "done" ? "Erneut scannen" : "Scan starten"))),

      React.createElement("div", { className: "mnt-card" },
        // scan bar
        React.createElement("div", { className: "mnt-scan-bar" },
          scanState === "idle" && React.createElement("div", { className: "sb-info" }, "Letzter Scan: ", React.createElement("b", null, lastScan), " \u00b7 0 Abweichungen"),
          scanState === "running" && React.createElement("div", { className: "mnt-progress", style: { flex: 1 } },
            React.createElement("div", { className: "mp-label" }, React.createElement("div", { className: "mp-spin" }), "Scan l\u00e4uft \u2026 " + pct + " %"),
            React.createElement("div", { className: "mp-bar" }, React.createElement("i", { style: { width: pct + "%" } }))),
          scanState === "done" && React.createElement("div", { className: "sb-info" },
            totalIssues === 0
              ? React.createElement("span", { style: { color: "var(--good)", fontWeight: 600 } }, "\u2714\ufe0f Alles konsistent \u2014 keine Abweichungen gefunden.")
              : React.createElement("span", { style: { color: "var(--warn)", fontWeight: 600 } }, totalIssues + " Abweichung" + (totalIssues === 1 ? "" : "en") + " gefunden")),
          scanState === "done" && totalIssues > 0 && React.createElement("button", { className: "mnt-btn ghost", style: { marginLeft: "auto" }, onClick: () => { setIssues([]); setScanState("idle"); } },
            "Bericht schlie\u00dfen")),

        // tabs (only when results exist)
        scanState === "done" && totalIssues > 0 && React.createElement(React.Fragment, null,
          React.createElement("div", { className: "mnt-tabs" },
            [["orphan","Verwaist"],["missing","Fehlend"],["drift","Pfad-Drift"]].map(([t,l]) =>
              React.createElement("button", { key: t, className: "mnt-tab" + (tab===t?" on":""), onClick: () => { setTab(t); setSel(new Set()); } },
                l, counts[t] > 0 && React.createElement("span", { className: "tab-badge " + (t==="missing"?"err":t==="orphan"?"warn":"") }, counts[t])))),

          // bulk bar
          selInTab > 0 && React.createElement("div", { className: "mnt-bulk" },
            React.createElement("span", { className: "bk-count" }, selInTab + " ausgew\u00e4hlt"),
            tab === "orphan" && React.createElement(React.Fragment, null,
              React.createElement("button", { className: "mnt-btn ghost sm", onClick: () => onBulkAction("index") }, React.createElement(Icon, { name: "plus", size: 12 }), "Alle indizieren"),
              React.createElement("button", { className: "mnt-btn danger sm", onClick: () => onBulkAction("trash") }, React.createElement(Icon, { name: "trash", size: 12 }), "Alle in Papierkorb")),
            tab === "missing" && React.createElement("button", { className: "mnt-btn warn sm", onClick: () => onBulkAction("mark_missing") }, "Alle als fehlend markieren"),
            tab === "drift" && React.createElement("button", { className: "mnt-btn ghost sm", onClick: () => onBulkAction("update_path") }, "Alle Pfade aktualisieren"),
            React.createElement("button", { className: "bk-clr", onClick: () => setSel(new Set()) }, "Auswahl aufheben")),

          // issue list
          React.createElement("div", { className: "mnt-issues" },
            tabIssues.length === 0
              ? React.createElement("div", { className: "mnt-empty" },
                  React.createElement(Icon, { name: "check", size: 36 }),
                  React.createElement("div", { className: "me-t" }, "Keine " + TYPE_LABEL[tab] + " Eintr\u00e4ge"),
                  React.createElement("div", { className: "me-s" }, "Dieser Bereich ist sauber."))
              : React.createElement(React.Fragment, null,
                  React.createElement("div", { className: "mnt-issue", style: { background: "var(--bg-2)", paddingTop: 8, paddingBottom: 8 } },
                    React.createElement("div", { className: "mi-chk" + (allTabSel ? " on" : ""), onClick: toggleAll },
                      allTabSel && React.createElement(Icon, { name: "check", size: 12, stroke: 3 })),
                    React.createElement("div", { className: "mi-body" },
                      React.createElement("div", { style: { fontSize: 11, color: "var(--text-3)", fontWeight: 600, letterSpacing: ".06em", textTransform: "uppercase" } },
                        "Alle ausw\u00e4hlen \u00b7 " + tabIssues.length + " Eintr\u00e4ge"))),
                  tabIssues.map(issue =>
                    React.createElement(IssueRow, { key: issue.id, issue, selected: sel.has(issue.id), onToggle: () => toggleSel(issue.id), onAction })))))));
  }

  /* ---- rebuild op row ---- */
  function OpRow({ icon, iconCls, title, sub, warning, btnLabel, btnCls = "ghost", onStart }) {
    const [state, setState] = useState("idle"); // idle | running | done
    const [pct, setPct] = useState(0);
    const [result, setResult] = useState(null);
    const timerRef = useRef(null);

    const start = () => {
      setState("running"); setPct(0); setResult(null);
      let p = 0;
      timerRef.current = setInterval(() => {
        p += Math.random() * 8 + 3;
        if (p >= 100) { p = 100; clearInterval(timerRef.current); setState("done"); setResult(onStart()); }
        setPct(Math.min(Math.round(p), 100));
      }, 250);
    };

    return React.createElement("div", { className: "mnt-op" },
      React.createElement("div", { className: "mnt-sec-ico " + iconCls }, React.createElement(Icon, { name: icon, size: 18 })),
      React.createElement("div", { className: "mnt-op-body" },
        React.createElement("div", { className: "mnt-op-title" }, title),
        React.createElement("div", { className: "mnt-op-sub" }, sub),
        warning && React.createElement("div", { className: "mnt-note warn", style: { marginTop: 10, marginBottom: 0 } },
          React.createElement(Icon, { name: "alertTriangle", size: 14 }), React.createElement("span", null, warning)),
        state === "running" && React.createElement("div", { className: "mnt-op-result running", style: { marginTop: 10 } },
          React.createElement("div", { style: { width: "100%" } },
            React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--accent)", marginBottom: 6 } },
              React.createElement("div", { className: "mnt-progress" },
                React.createElement("div", { className: "mp-bar" }, React.createElement("i", { style: { width: pct + "%" } })))),
            React.createElement("div", { style: { fontSize: 11, color: "var(--text-3)" } }, pct + " % abgeschlossen"))),
        state === "done" && result && React.createElement("div", { className: "mnt-op-result ok" },
          React.createElement(Icon, { name: "check", size: 14 }), result)),
      React.createElement("div", { className: "mnt-op-ctrl" },
        React.createElement("button", { className: "mnt-btn " + btnCls, disabled: state === "running", onClick: start },
          state === "running" ? React.createElement(React.Fragment, null, React.createElement("div", { className: "mnt-progress", style: {width:14,height:14,borderRadius:"50%",border:"2px solid rgba(255,255,255,.3)",borderTopColor:"#fff",animation:"mnt-spin .7s linear infinite",flexShrink:0} }), "L\u00e4uft \u2026") :
          state === "done"    ? React.createElement(React.Fragment, null, React.createElement(Icon, { name: "refresh", size: 14 }), "Erneut ausf\u00fchren") :
                                React.createElement(React.Fragment, null, React.createElement(Icon, { name: icon, size: 14 }), btnLabel))));
  }

  /* ---- main page ---- */
  function Maintenance() {
    return React.createElement("div", { className: "grid-wrap" },
      React.createElement("div", { className: "month-head", style: { padding: "20px 22px 6px" } },
        React.createElement("h3", null, "Wartung"),
        React.createElement("div", { className: "m-line" }),
        React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)" } }, "Dateisystem-Abgleich, Cache-Rebuilds \u00b7 keine Skripte n\u00f6tig")),

      React.createElement("div", { className: "mnt-page" },

        // status bar
        React.createElement("div", { className: "mnt-statusbar" },
          React.createElement("div", { className: "mnt-stat" },
            React.createElement("div", { className: "mnt-stat-lbl" }, "Letzter FS\u2194DB Scan"),
            React.createElement("div", { className: "mnt-stat-val muted" }, "2026-06-10 \u00b7 14:32"),
            React.createElement("div", { className: "mnt-stat-sub" }, "0 Abweichungen")),
          React.createElement("div", { className: "mnt-stat" },
            React.createElement("div", { className: "mnt-stat-lbl" }, "Datenbank"),
            React.createElement("div", { className: "mnt-stat-val ok" }, React.createElement(Icon, { name: "check", size: 14 }), "Konsistent"),
            React.createElement("div", { className: "mnt-stat-sub" }, "db.sqlite \u00b7 42 MB")),
          React.createElement("div", { className: "mnt-stat" },
            React.createElement("div", { className: "mnt-stat-lbl" }, "Thumbnails"),
            React.createElement("div", { className: "mnt-stat-val ok" }, React.createElement(Icon, { name: "check", size: 14 }), "Aktuell"),
            React.createElement("div", { className: "mnt-stat-sub" }, "2 847 Thumbnails \u00b7 890 MB")),
          React.createElement("div", { className: "mnt-stat" },
            React.createElement("div", { className: "mnt-stat-lbl" }, "Face-Crops"),
            React.createElement("div", { className: "mnt-stat-val ok" }, React.createElement(Icon, { name: "check", size: 14 }), "Vollst\u00e4ndig"),
            React.createElement("div", { className: "mnt-stat-sub" }, "481 Crops \u00b7 " + 12 + " manuell"))),

        // scan section
        React.createElement(ScanSection),

        // rebuilds
        React.createElement("div", { className: "mnt-sec" },
          React.createElement("div", { className: "mnt-sec-head" },
            React.createElement("div", { className: "mnt-sec-ico" }, React.createElement(Icon, { name: "refresh", size: 18 })),
            React.createElement("div", { style: { flex: 1, minWidth: 0 } },
              React.createElement("div", { className: "mnt-sec-title" }, "Cache & Thumbnails"),
              React.createElement("div", { className: "mnt-sec-sub" }, "Thumbnails und Face-Crops k\u00f6nnen jederzeit gefahrlos neu aufgebaut werden \u2014 sie sind reiner Cache."))),
          React.createElement("div", { className: "mnt-card" },
            React.createElement(OpRow, {
              icon: "gallery", iconCls: "accent", btnCls: "accent",
              title: "Thumbnails neu aufbauen",
              sub: "Generiert thumbnails.sqlite vollst\u00e4ndig aus den vorhandenen Bilddateien neu. Sicher \u2014 keine Originale werden ver\u00e4ndert.",
              btnLabel: "Thumbnails rebuilden",
              onStart: () => "Abgeschlossen \u00b7 2 847 Thumbnails neu erzeugt",
            }),
            React.createElement(OpRow, {
              icon: "face", iconCls: "", btnCls: "ghost",
              title: "Face-Crops neu extrahieren",
              sub: "Re-extrahiert abgeleitete Face-Crops aus allen Bildern in den personX/photos/-Ordnern. Nur Crops neu, keine Embeddings.",
              warning: "Manuelle Face-Originale (origin\u00a0=\u00a0manual_original) werden dabei nie \u00fcberschrieben \u2014 nur automatisch extrahierte Crops werden erneuert.",
              btnLabel: "Face-Rebuild starten",
              onStart: () => "481 Crops \u00b7 Queue gestartet",
            })))));
  }

  window.Maintenance = Maintenance;
})();
