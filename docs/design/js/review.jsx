/* Photofant — Review-Queue: Gesichts-Bestätigungs-Workflow */
(function () {
  const { Icon } = window;
  const { Img, Avatar, scoreClass } = window.UI;
  const { useState, useEffect, useRef } = React;

  function buildQueue(assets) {
    var r = window.PF.rng(7373);
    var pool = assets.filter(function(a) { return a.faces && a.faces.length > 0; });
    return pool.slice(0, 7).map(function(asset, i) {
      var face = asset.faces[0];
      var conf = 0.55 + r() * 0.42;
      var pid = r() < 0.25 ? -1 : (face.personId >= 0 && face.personId < window.PF.PERSONS.length ? face.personId : 0);
      return { id: i, asset: asset, personId: pid, confidence: conf, status: 'pending' };
    });
  }

  /* ── Sidebar item ── */
  function QueueItem({ it, idx, current, persons, onSelect }) {
    var p = it.personId >= 0 && it.personId < persons.length ? persons[it.personId] : null;
    var sc = it.confidence >= 0.9 ? 'high' : it.confidence >= 0.75 ? 'mid' : '';
    var stMeta = it.status === 'approved'  ? { bg: 'oklch(0.74 0.13 152 / .18)', col: 'var(--good)',   lbl: '✓' }
               : it.status === 'rejected'  ? { bg: 'var(--danger-weak)',           col: 'var(--danger)', lbl: '✗' }
               : it.status === 'reassigned'? { bg: 'var(--accent-weak)',            col: 'var(--accent)', lbl: '~' }
               : null;
    return React.createElement('button', {
      className: 'rq-qitem' + (idx === current ? ' active' : '') + (it.status !== 'pending' ? ' done' : ''),
      onClick: function() { onSelect(idx); },
    },
      React.createElement('span', { className: 'rq-qitem-num' }, idx + 1),
      React.createElement('div', { className: 'rq-qitem-thumb' },
        React.createElement(Img, { src: it.asset.photo, bg: it.asset.bg })),
      React.createElement('div', { className: 'rq-qitem-info' },
        React.createElement('div', { style: { fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } },
          p ? p.name : 'Unbekannt'),
        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 } },
          React.createElement('span', { className: 'score-pill ' + sc }, Math.round(it.confidence * 100) + '%'),
          stMeta && React.createElement('span', {
            style: { fontSize: 10, fontWeight: 700, padding: '2px 5px', borderRadius: 4, fontFamily: 'var(--mono)', background: stMeta.bg, color: stMeta.col }
          }, stMeta.lbl))));
  }

  /* ── Review panel (right side) ── */
  function ReviewPanel({ item, persons, assignOpen, assignQ, setAssignOpen, setAssignQ, current, onAct }) {
    var person = item.personId >= 0 && item.personId < persons.length ? persons[item.personId] : null;
    var filteredPersons = persons.filter(function(p) {
      return !assignQ || p.name.toLowerCase().includes(assignQ.toLowerCase());
    });

    return React.createElement('div', { className: 'rq-panel' },

      React.createElement('div', { className: 'panel-sec' },
        React.createElement('div', { className: 'psec-title' }, 'Ähnlichkeitswert'),
        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 } },
          React.createElement('div', { style: { flex: 1, height: 6, borderRadius: 3, background: 'var(--surface-2)', overflow: 'hidden' } },
            React.createElement('div', { style: {
              height: '100%', borderRadius: 3, transition: 'width .4s',
              width: Math.round(item.confidence * 100) + '%',
              background: item.confidence >= 0.85 ? 'var(--good)' : item.confidence >= 0.7 ? 'var(--warn)' : 'var(--danger)',
            }})),
          React.createElement('span', { className: 'score-pill ' + scoreClass(item.confidence) },
            Math.round(item.confidence * 100) + '%'))),

      React.createElement('div', { className: 'panel-sec' },
        React.createElement('div', { className: 'psec-title' }, 'Vorgeschlagene Zuordnung'),
        person
          ? React.createElement('div', { className: 'rq-match-card' },
              React.createElement(Avatar, { personId: item.personId, size: 52 }),
              React.createElement('div', { style: { flex: 1, minWidth: 0 } },
                React.createElement('div', { style: { fontSize: 15, fontWeight: 700 } }, person.name),
                React.createElement('div', { style: { fontSize: 11.5, color: 'var(--text-3)', fontFamily: 'var(--mono)', marginTop: 3 } },
                  person.count + ' Bilder in Sammlung')))
          : React.createElement('div', { className: 'rq-match-unknown' },
              React.createElement('div', { style: { width: 52, height: 52, borderRadius: '50%', background: 'var(--surface-2)', display: 'grid', placeItems: 'center', flexShrink: 0 } },
                React.createElement(Icon, { name: 'face', size: 24, style: { color: 'var(--text-3)' } })),
              React.createElement('div', null,
                React.createElement('div', { style: { fontSize: 14, fontWeight: 600 } }, 'Kein Treffer'),
                React.createElement('div', { style: { fontSize: 11.5, color: 'var(--text-3)', marginTop: 2 } }, 'Nicht in Datenbank')))),

      React.createElement('div', { className: 'panel-sec' },
        React.createElement('div', { className: 'pbtn-row', style: { padding: 0, marginBottom: 8 } },
          React.createElement('button', {
            className: 'pbtn primary', disabled: item.status !== 'pending',
            style: item.status !== 'pending' ? { opacity: 0.45 } : {},
            onClick: function() { onAct(current, 'approved'); },
          }, React.createElement(Icon, { name: 'check', size: 15 }), person ? 'Bestätigen' : 'Als unbekannt'),
          React.createElement('button', {
            className: 'pbtn ghost', disabled: item.status !== 'pending',
            style: item.status !== 'pending' ? { opacity: 0.45 } : {},
            onClick: function() { onAct(current, 'rejected'); },
          }, React.createElement(Icon, { name: 'x', size: 15 }), 'Ablehnen')),
        React.createElement('button', {
          className: 'rq-assign-btn',
          onClick: function() { setAssignOpen(function(o) { return !o; }); setAssignQ(''); },
        }, React.createElement(Icon, { name: 'people', size: 15 }), 'Andere Person\u2026')),

      assignOpen && React.createElement('div', { className: 'panel-sec' },
        React.createElement('div', { className: 'tag-search', style: { marginBottom: 8 } },
          React.createElement(Icon, { name: 'search', size: 13, style: { color: 'var(--text-3)' } }),
          React.createElement('input', {
            autoFocus: true, placeholder: 'Person suchen\u2026',
            value: assignQ, onChange: function(e) { setAssignQ(e.target.value); },
          })),
        filteredPersons.slice(0, 5).map(function(p) {
          return React.createElement('button', {
            key: p.id, className: 'matchrow',
            onClick: function() { onAct(current, 'reassigned', p.id); setAssignQ(''); },
          },
            React.createElement('div', { className: 'match-av' }, React.createElement(Avatar, { personId: p.id, size: 34 })),
            React.createElement('div', null,
              React.createElement('div', { className: 'match-name' }, p.name),
              React.createElement('div', { className: 'match-meta' }, p.count + ' Bilder')));
        })),

      React.createElement('div', { className: 'panel-sec', style: { borderBottom: 'none' } },
        React.createElement('div', { className: 'psec-title' }, 'Bilddaten'),
        React.createElement('dl', { className: 'kv' },
          React.createElement('dt', null, 'ID'),          React.createElement('dd', null, '#' + item.asset.id),
          React.createElement('dt', null, 'Datum'),       React.createElement('dd', null, item.asset.date.toLocaleDateString('de-DE')),
          React.createElement('dt', null, 'Bildschnitt'), React.createElement('dd', null, window.PF.framingLabel(item.asset.framing)),
          React.createElement('dt', null, 'Quelle'),      React.createElement('dd', null, window.PF.sourceLabel(item.asset.source))))
    );
  }

  /* ── Root component ── */
  function ReviewQueue({ assets }) {
    const [items, setItems] = useState(function() { return buildQueue(assets); });
    const [current, setCurrent] = useState(0);
    const [assignOpen, setAssignOpen] = useState(false);
    const [assignQ, setAssignQ] = useState('');
    const itemsRef = useRef(items);
    const currentRef = useRef(current);
    const assignOpenRef = useRef(assignOpen);
    itemsRef.current = items;
    currentRef.current = current;
    assignOpenRef.current = assignOpen;

    var item = items[current];
    var persons = window.PF.PERSONS;
    var done = items.filter(function(i) { return i.status !== 'pending'; }).length;
    var total = items.length;
    var allDone = items.every(function(i) { return i.status !== 'pending'; });

    var act = function(idx, status, pid) {
      setItems(function(prev) {
        return prev.map(function(it, i) {
          if (i !== idx) return it;
          var patch = { status: status };
          if (pid !== undefined) patch.personId = pid;
          return Object.assign({}, it, patch);
        });
      });
      setAssignOpen(false);
      if (idx + 1 < items.length) setCurrent(idx + 1);
    };

    useEffect(function() {
      var h = function(e) {
        if (assignOpenRef.current) return;
        var c = currentRef.current;
        var its = itemsRef.current;
        if (e.key === 'ArrowRight') { e.preventDefault(); setCurrent(function(x) { return Math.min(x + 1, its.length - 1); }); }
        if (e.key === 'ArrowLeft')  { e.preventDefault(); setCurrent(function(x) { return Math.max(x - 1, 0); }); }
        if ((e.key === 'y' || e.key === 'Enter') && its[c] && its[c].status === 'pending') {
          setItems(function(prev) { return prev.map(function(it, i) { return i === c ? Object.assign({}, it, { status: 'approved' }) : it; }); });
          setCurrent(function(x) { return Math.min(x + 1, its.length - 1); });
        }
        if (e.key === 'n' && its[c] && its[c].status === 'pending') {
          setItems(function(prev) { return prev.map(function(it, i) { return i === c ? Object.assign({}, it, { status: 'rejected' }) : it; }); });
          setCurrent(function(x) { return Math.min(x + 1, its.length - 1); });
        }
      };
      window.addEventListener('keydown', h);
      return function() { window.removeEventListener('keydown', h); };
    }, []);

    /* ── Build sections as variables for clarity ── */
    var header = React.createElement('div', { className: 'rq-header' },
      React.createElement('div', { className: 'rq-prog-row' },
        React.createElement('div', { className: 'rq-prog-bar' },
          React.createElement('div', { className: 'rq-prog-fill', style: { width: (done / total * 100) + '%' } })),
        React.createElement('span', { className: 'rq-prog-label' }, done + ' / ' + total + ' abgeschlossen')),
      React.createElement('div', { style: { display: 'flex', gap: 14 } },
        [
          { n: items.filter(function(i) { return i.status === 'approved'; }).length,  label: 'bestätigt', col: 'var(--good)'   },
          { n: items.filter(function(i) { return i.status === 'rejected'; }).length,  label: 'abgelehnt', col: 'var(--danger)' },
          { n: items.filter(function(i) { return i.status === 'pending'; }).length,   label: 'offen',     col: 'var(--text-3)' },
        ].map(function(s) {
          return React.createElement('span', { key: s.label, style: { fontSize: 11.5, fontFamily: 'var(--mono)', color: s.col } }, s.n + '\u00a0' + s.label);
        })));

    var doneScreen = React.createElement('div', { className: 'placeholder-view' },
      React.createElement(Icon, { name: 'check', size: 44, style: { color: 'var(--good)' } }),
      React.createElement('h3', null, 'Review abgeschlossen'),
      React.createElement('p', null, 'Alle Gesichter wurden geprüft und zugeordnet.'));

    var sidebar = React.createElement('div', { className: 'rq-sidebar' },
      React.createElement('div', { className: 'nav-group-label' }, 'Warteschlange'),
      items.map(function(it, idx) {
        return React.createElement(QueueItem, { key: it.id, it: it, idx: idx, current: current, persons: persons, onSelect: setCurrent });
      }));

    var mainArea = item && React.createElement('div', { className: 'rq-main' },
      React.createElement('div', { className: 'rq-photo-area' },
        React.createElement('div', { className: 'rq-photo-frame' },
          React.createElement('div', { className: 'rq-ratio-box' },
            React.createElement(Img, { src: item.asset.photo, bg: item.asset.bg }),
            React.createElement('div', { className: 'rq-face-box' }),
            item.personId >= 0 && item.personId < persons.length && persons[item.personId] &&
              React.createElement('div', { className: 'rq-face-label' }, persons[item.personId].name.toUpperCase())))),
      React.createElement(ReviewPanel, {
        item: item, persons: persons, assignOpen: assignOpen, assignQ: assignQ,
        setAssignOpen: setAssignOpen, setAssignQ: setAssignQ, current: current, onAct: act,
      }));

    var footer = React.createElement('div', { className: 'rq-footer' },
      React.createElement('button', { className: 'iconbtn', style: { width: 32, height: 32 }, disabled: current === 0, onClick: function() { setCurrent(function(c) { return Math.max(c - 1, 0); }); } },
        React.createElement(Icon, { name: 'arrowLeft', size: 16 })),
      React.createElement('span', { style: { fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--mono)' } }, (current + 1) + ' / ' + total),
      React.createElement('button', { className: 'iconbtn', style: { width: 32, height: 32 }, disabled: current === items.length - 1, onClick: function() { setCurrent(function(c) { return Math.min(c + 1, items.length - 1); }); } },
        React.createElement(Icon, { name: 'arrowRight', size: 16 })),
      React.createElement('div', { style: { flex: 1 } }),
      [['Enter / Y', 'Bestätigen'], ['N', 'Ablehnen'], ['\u2190 \u2192', 'Navigieren']].map(function(pair) {
        return React.createElement('span', { key: pair[0], style: { display: 'flex', alignItems: 'center', gap: 6 } },
          React.createElement('span', { className: 'kbd' }, pair[0]),
          React.createElement('span', { style: { fontSize: 11.5, color: 'var(--text-3)' } }, pair[1]));
      }));

    return React.createElement('div', { className: 'rq-container' },
      header,
      allDone ? doneScreen : React.createElement('div', { className: 'rq-body' }, sidebar, mainArea),
      footer);
  }

  window.ReviewQueue = ReviewQueue;
})();
