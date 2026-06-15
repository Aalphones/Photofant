/* Photofant — Trainingssets: Bild-fokussierter Editor */
(function () {
  var Icon      = window.Icon;
  var Img       = window.UI.Img;
  var Avatar    = window.UI.Avatar;
  var useState  = React.useState;
  var useEffect = React.useEffect;
  var useRef    = React.useRef;
  var useMemo   = React.useMemo;

  /* ── data ── */
  function buildSets(assets) {
    var lena   = assets.filter(function(a){ return a.personId===0; }).sort(function(a,b){ return b.quality-a.quality; }).slice(0,14).map(function(a){ return a.id; });
    var felix  = assets.filter(function(a){ return a.personId===3; }).sort(function(a,b){ return b.quality-a.quality; }).slice(0,11).map(function(a){ return a.id; });
    var studio = assets.filter(function(a){ return a.tags.some(function(t){ return t.name==='studio'; }) && a.source==='original'; }).sort(function(a,b){ return b.quality-a.quality; }).slice(0,18).map(function(a){ return a.id; });
    return [
      { id:'ts1', name:'Lena · Portrait LoRA',  personId:0,    imageIds:lena,   triggerWord:'lena_v1',         captionStyle:'Florence-2 Detailliert', targetModel:'FLUX.1 [dev]',     status:'ready',    created:'12. Mai 2026',   exported:'14. Mai 2026' },
      { id:'ts2', name:'Felix · Full-Body',      personId:3,    imageIds:felix,  triggerWord:'felix_v1',        captionStyle:'Florence-2 Kurz',        targetModel:'SDXL 1.0',         status:'draft',    created:'3. Juni 2026',   exported:null },
      { id:'ts3', name:'Studio-Sessions',        personId:null, imageIds:studio, triggerWord:'studio_portrait', captionStyle:'Florence-2 Detailliert', targetModel:'FLUX.1 [schnell]', status:'exported', created:'28. April 2026', exported:'1. Mai 2026' },
    ];
  }

  var STATUS = {
    draft:    { label:'Entwurf',    bg:'var(--surface-2)',           col:'var(--text-3)' },
    ready:    { label:'Bereit',     bg:'oklch(0.74 0.13 152 / .18)', col:'var(--good)'   },
    exported: { label:'Exportiert', bg:'var(--accent-weak)',          col:'var(--accent)' },
  };

  /* ── Context Menu ── */
  function TSContextMenu(props) {
    var imgId      = props.imgId;
    var x          = props.x;
    var y          = props.y;
    var isSelected = props.isSelected;
    var selCount   = props.selCount;
    var onClose    = props.onClose;
    var onOpen     = props.onOpen;
    var onToggle   = props.onToggle;
    var onAddTag   = props.onAddTag;
    var onRemove   = props.onRemove;

    var menuRef      = useRef(null);
    var posState     = useState({ x: x, y: y });
    var pos = posState[0]; var setPos = posState[1];
    var tagState     = useState('');
    var tag = tagState[0]; var setTag = tagState[1];
    var modeState    = useState('main'); /* 'main' | 'tag' | 'crop' */
    var mode = modeState[0]; var setMode = modeState[1];
    var FMTS = ['1:1','4:5','3:4','2:3','9:16'];
    var applyLabel = isSelected && selCount > 1 ? ' (' + selCount + ')' : '';

    /* close on Escape */
    useEffect(function() {
      function onKey(e) { if (e.key === 'Escape') onClose(); }
      document.addEventListener('keydown', onKey);
      return function() { document.removeEventListener('keydown', onKey); };
    }, []);

    /* nudge menu inside viewport after first render + whenever mode changes */
    useEffect(function() {
      if (!menuRef.current) return;
      var rect = menuRef.current.getBoundingClientRect();
      var vw = window.innerWidth; var vh = window.innerHeight;
      var nx = x; var ny = y;
      if (nx + rect.width  > vw - 8) nx = Math.max(8, vw - rect.width  - 8);
      if (ny + rect.height > vh - 8) ny = Math.max(8, vh - rect.height - 8);
      setPos({ x: nx, y: ny });
    }, [mode]);

    function item(label, iconName, cb, cls) {
      return React.createElement('button', {
        className: 'ts-ctx-item' + (cls ? ' ' + cls : ''),
        onMouseDown: function(e) { e.preventDefault(); },
        onClick: function(e) { e.stopPropagation(); cb(); },
      }, React.createElement(Icon, { name: iconName, size: 13 }), label);
    }

    var body;
    if (mode === 'tag') {
      body = React.createElement('div', { className: 'ts-ctx-tag-row' },
        React.createElement('input', {
          autoFocus: true,
          className: 'ts-ctx-tag-input',
          placeholder: 'Tag-Name…',
          value: tag,
          onChange: function(e) { setTag(e.target.value); },
          onKeyDown: function(e) {
            if (e.key === 'Enter') { if (tag.trim()) onAddTag(imgId, tag.trim()); onClose(); }
            if (e.key === 'Escape') { setMode('main'); setTag(''); }
          },
          onClick: function(e) { e.stopPropagation(); },
        }),
        React.createElement('button', {
          className: 'ts-ctx-tag-ok',
          onMouseDown: function(e) { e.preventDefault(); },
          onClick: function(e) { e.stopPropagation(); if (tag.trim()) onAddTag(imgId, tag.trim()); onClose(); },
        }, 'OK'),
        React.createElement('button', {
          className: 'ts-ctx-item muted', style: { padding: '0 7px', minWidth: 0 },
          onMouseDown: function(e) { e.preventDefault(); },
          onClick: function(e) { e.stopPropagation(); setMode('main'); setTag(''); },
        }, React.createElement(Icon, { name: 'x', size: 12 })));
    } else if (mode === 'crop') {
      body = React.createElement(React.Fragment, null,
        React.createElement('div', { className: 'ts-ctx-crop-list' },
          FMTS.map(function(f) {
            return React.createElement('button', {
              key: f, className: 'ts-ctx-crop-opt',
              onClick: function(e) { e.stopPropagation(); onClose(); },
            }, f);
          })),
        item('← Zurück', 'arrowLeft', function() { setMode('main'); }));
    } else {
      body = React.createElement(React.Fragment, null,
        item('Öffnen', 'image', function() { onOpen(imgId); onClose(); }),
        isSelected
          ? item('Abwählen', 'x', function() { onToggle(imgId); onClose(); })
          : item('Auswählen', 'check', function() { onToggle(imgId); onClose(); }),
        React.createElement('div', { className: 'ts-ctx-sep' }),
        item('Tag hinzufügen' + applyLabel, 'tag', function() { setMode('tag'); }),
        item('Upscale' + applyLabel, 'upscale', function() { onClose(); }),
        item('Zuschneiden' + applyLabel, 'crop', function() { setMode('crop'); }),
        React.createElement('div', { className: 'ts-ctx-sep' }),
        item('Aus Set entfernen', 'trash', function() { onRemove(imgId); onClose(); }, 'danger'));
    }

    return React.createElement(React.Fragment, null,
      React.createElement('div', {
        style: { position: 'fixed', inset: 0, zIndex: 199 },
        onMouseDown: onClose,
        onTouchStart: onClose,
      }),
      React.createElement('div', {
        ref: menuRef,
        className: 'ts-ctx-menu',
        style: { left: pos.x, top: pos.y },
        onClick: function(e) { e.stopPropagation(); },
      }, body));
  }

  /* ── Lightbox ── */
  function TSLightbox(props) {
    var img      = props.img;
    var onClose  = props.onClose;
    var onRemove = props.onRemove;
    var onUpdate = props.onUpdate;

    var captionState = useState(img.caption);
    var caption = captionState[0]; var setCaption = captionState[1];
    var tagsState = useState(img.tags.slice());
    var tags = tagsState[0]; var setTags = tagsState[1];
    var newTagState = useState('');
    var newTag = newTagState[0]; var setNewTag = newTagState[1];
    var dirtyState = useState(false);
    var dirty = dirtyState[0]; var setDirty = dirtyState[1];

    function save() { onUpdate(img.id, { caption: caption, tags: tags }); setDirty(false); }
    function removeTag(name) { setTags(function(t){ return t.filter(function(x){ return x.name!==name; }); }); setDirty(true); }
    function addTag() {
      var t = newTag.trim();
      if (!t || tags.some(function(x){ return x.name===t; })) return;
      setTags(function(ts){ return ts.concat([{ name:t, kind:'manual' }]); });
      setNewTag(''); setDirty(true);
    }

    var chipEls = tags.map(function(t) {
      return React.createElement('div', { key: t.name, className:'ts-tag-chip' + (t.kind==='manual' ? ' manual' : '') },
        React.createElement('span', null, t.name),
        React.createElement('button', { className:'ts-tag-x', onClick: function(){ removeTag(t.name); } },
          React.createElement(Icon, { name:'x', size:10, stroke:2.5 })));
    });

    var metaDl = React.createElement('dl', { className:'kv' },
      React.createElement('dt', null, 'ID'),          React.createElement('dd', null, '#' + img.id),
      React.createElement('dt', null, 'Auflösung'),   React.createElement('dd', null, img.dims.w + '×' + img.dims.h),
      React.createElement('dt', null, 'Format'),      React.createElement('dd', null, img.format.toUpperCase()),
      React.createElement('dt', null, 'Bildschnitt'), React.createElement('dd', null, window.PF.framingLabel(img.framing)),
      React.createElement('dt', null, 'Qualität'),    React.createElement('dd', null, Math.round(img.quality*100) + '%'),
      React.createElement('dt', null, 'Captioner'),   React.createElement('dd', null, img.captioner));

    var actionBtns = React.createElement('div', null,
      dirty && React.createElement('button', {
        className:'pbtn primary', style:{ width:'100%', marginBottom:8, justifyContent:'center', gap:7 },
        onClick: save,
      }, React.createElement(Icon, { name:'check', size:14 }), 'Speichern'),
      React.createElement('div', { className:'pbtn-row', style:{ padding:0 } },
        React.createElement('button', { className:'pbtn ghost', style:{ flex:1, gap:6 } },
          React.createElement(Icon, { name:'upscale', size:13 }), 'Upscale'),
        React.createElement('button', { className:'pbtn ghost', style:{ flex:1, gap:6 } },
          React.createElement(Icon, { name:'crop', size:13 }), 'Zuschnitt')),
      React.createElement('button', {
        className:'pbtn ghost',
        style:{ width:'100%', marginTop:6, color:'var(--danger)', gap:6, justifyContent:'center' },
        onClick: function(){ onRemove(img.id); onClose(); },
      }, React.createElement(Icon, { name:'trash', size:13 }), 'Aus Set entfernen'));

    return React.createElement('div', { className:'ts-lb-overlay', onClick: onClose },
      React.createElement('div', { className:'ts-lb-box', onClick: function(e){ e.stopPropagation(); } },
        React.createElement('button', { className:'ts-lb-close', onClick: onClose },
          React.createElement(Icon, { name:'x', size:18 })),
        React.createElement('div', { className:'ts-lb-img' },
          React.createElement('div', { className:'ts-lb-ratio', style:{ paddingBottom:(img.ar.h/img.ar.w*100)+'%' } },
            React.createElement(Img, { src:img.photo, bg:img.bg }))),
        React.createElement('div', { className:'ts-lb-panel' },
          React.createElement('div', { className:'panel-sec' },
            React.createElement('div', { className:'psec-title' }, 'Caption'),
            React.createElement('textarea', {
              className:'ts-caption-area', value:caption, rows:5,
              onChange: function(e){ setCaption(e.target.value); setDirty(true); },
            })),
          React.createElement('div', { className:'panel-sec' },
            React.createElement('div', { className:'psec-title' }, 'Tags'),
            React.createElement('div', { className:'ts-tag-chips' }, chipEls),
            React.createElement('div', { className:'tag-search', style:{ marginTop:8 } },
              React.createElement(Icon, { name:'plus', size:13, style:{ color:'var(--text-3)' } }),
              React.createElement('input', {
                placeholder:'Tag hinzufügen…', value:newTag,
                onChange: function(e){ setNewTag(e.target.value); },
                onKeyDown: function(e){ if(e.key==='Enter') addTag(); },
              }))),
          React.createElement('div', { className:'panel-sec' }, metaDl),
          React.createElement('div', { className:'panel-sec', style:{ borderBottom:'none' } }, actionBtns))));
  }

  /* ── Search & Replace Modal ── */
  function TSSearchReplace(props) {
    var onClose      = props.onClose;
    var onApply      = props.onApply;
    var hasSelection = props.hasSelection;

    var findState  = useState(''); var find = findState[0]; var setFind = findState[1];
    var replState  = useState(''); var repl = replState[0]; var setRepl = replState[1];
    var scopeState = useState(hasSelection ? 'selection' : 'all');
    var scope = scopeState[0]; var setScope = scopeState[1];

    function apply() { if (!find.trim()) return; onApply(find, repl, scope); onClose(); }

    var scopeBtns = ['all','selection'].map(function(s) {
      return React.createElement('button', {
        key: s,
        className:'pbtn ' + (scope===s ? 'primary' : 'ghost'),
        style:{ flex:1, justifyContent:'center', fontSize:12.5 },
        onClick: function(){ setScope(s); },
      }, s==='all' ? 'Alle Bilder' : 'Auswahl (' + (hasSelection ? '…' : '0') + ')');
    });

    return React.createElement('div', { className:'ts-lb-overlay', onClick: onClose },
      React.createElement('div', { className:'ts-sr-modal', onClick: function(e){ e.stopPropagation(); } },
        React.createElement('div', { className:'ts-modal-head' },
          React.createElement('span', { style:{ fontWeight:700, fontSize:15 } }, 'Suchen & Ersetzen in Captions'),
          React.createElement('button', { className:'iconbtn', onClick: onClose },
            React.createElement(Icon, { name:'x', size:16 }))),
        React.createElement('div', { className:'ts-modal-body' },
          React.createElement('label', { className:'ts-field-label' }, 'Suchen'),
          React.createElement('input', { className:'ts-modal-input', placeholder:'Suchbegriff…', value:find, onChange:function(e){ setFind(e.target.value); } }),
          React.createElement('label', { className:'ts-field-label', style:{ marginTop:12 } }, 'Ersetzen durch'),
          React.createElement('input', { className:'ts-modal-input', placeholder:'Ersatz (leer = entfernen)…', value:repl, onChange:function(e){ setRepl(e.target.value); } }),
          React.createElement('label', { className:'ts-field-label', style:{ marginTop:12 } }, 'Bereich'),
          React.createElement('div', { style:{ display:'flex', gap:8, marginTop:6 } }, scopeBtns),
          React.createElement('button', {
            className:'pbtn primary',
            style:{ width:'100%', marginTop:14, justifyContent:'center' },
            disabled: !find.trim(), onClick: apply,
          }, React.createElement(Icon, { name:'refresh', size:14 }), 'Anwenden'))));
  }

  /* ── Image Cell ── */
  function TSImgCell(props) {
    var img           = props.img;
    var selected      = props.selected;
    var anySelected   = props.anySelected;
    var onToggle      = props.onToggle;
    var onOpen        = props.onOpen;
    var onRangeSelect = props.onRangeSelect;
    var onContextMenu = props.onContextMenu;

    var hoverState = useState(false);
    var hover = hoverState[0]; var setHover = hoverState[1];

    /* touch long-press refs */
    var timerRef          = useRef(null);
    var touchMovedRef     = useRef(false);
    var touchStartPosRef  = useRef({ x: 0, y: 0 });
    var longFiredRef      = useRef(false);

    var showCheck = hover || anySelected;
    var pb = (img.ar.h / img.ar.w * 100) + '%';

    /* ── click (desktop keyboard modifiers) ── */
    function handleClick(e) {
      if (longFiredRef.current) { longFiredRef.current = false; return; } /* swallow post-longpress click */
      if (e.ctrlKey || e.metaKey) { e.preventDefault(); onToggle(img.id); return; }
      if (e.shiftKey)              { e.preventDefault(); onRangeSelect(img.id); return; }
      if (anySelected)             { onToggle(img.id); return; }
      onOpen(img.id);
    }

    /* ── touch long-press ── */
    function handleTouchStart(e) {
      touchStartPosRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      touchMovedRef.current = false;
      longFiredRef.current  = false;
      timerRef.current = setTimeout(function() {
        if (!touchMovedRef.current) {
          longFiredRef.current = true;
          onToggle(img.id);
          if (navigator.vibrate) navigator.vibrate(40);
        }
      }, 600);
    }
    function handleTouchMove(e) {
      var dx = e.touches[0].clientX - touchStartPosRef.current.x;
      var dy = e.touches[0].clientY - touchStartPosRef.current.y;
      if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
        touchMovedRef.current = true;
        if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
      }
    }
    function handleTouchEnd() {
      if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
    }

    /* ── right-click context menu ── */
    function handleContextMenu(e) {
      e.preventDefault();
      onContextMenu(img.id, e.clientX, e.clientY);
    }

    return React.createElement('div', {
      className: 'ts-img-cell' + (selected ? ' ts-img-sel' : ''),
      onMouseEnter:   function() { setHover(true); },
      onMouseLeave:   function() { setHover(false); },
      onClick:        handleClick,
      onTouchStart:   handleTouchStart,
      onTouchMove:    handleTouchMove,
      onTouchEnd:     handleTouchEnd,
      onContextMenu:  handleContextMenu,
    },
      React.createElement('div', { style:{ position:'relative', borderRadius:8, overflow:'hidden', width:'100%', paddingBottom:pb } },
        React.createElement(Img, { src:img.photo, bg:img.bg }),
        (hover || selected) && React.createElement('div', { className:'veil' }),
        showCheck && React.createElement('button', {
          className: 'ts-cell-check' + (selected ? ' on' : ''),
          onClick: function(e) { e.stopPropagation(); onToggle(img.id); },
        }, selected && React.createElement(Icon, { name:'check', size:11, stroke:3 })),
        React.createElement('div', { className:'ts-cell-foot' },
          React.createElement('span', { className:'ts-cell-framing' }, window.PF.framingLabel(img.framing)),
          React.createElement('span', { className:'ts-cell-size' }, img.dims.w + '×' + img.dims.h),
          React.createElement('span', { className:'ts-cell-tagcount' }, img.tags.length + ' Tags'))));
  }

  /* ── Selection Bar ── */
  function TSSelBar(props) {
    var count    = props.count;
    var onAddTag = props.onAddTag;
    var onRemove = props.onRemove;
    var onClear  = props.onClear;

    var showTagState  = useState(false);
    var showTag = showTagState[0]; var setShowTag = showTagState[1];
    var tagInputState = useState('');
    var tagInput = tagInputState[0]; var setTagInput = tagInputState[1];
    var showCropState = useState(false);
    var showCrop = showCropState[0]; var setShowCrop = showCropState[1];
    var FMTS = ['1:1','4:5','3:4','2:3','9:16'];

    if (count === 0) return null;

    var tagSection = showTag
      ? React.createElement('div', { style:{ display:'flex', gap:6, alignItems:'center' } },
          React.createElement('input', {
            autoFocus:true, className:'ts-selbar-input',
            placeholder:'Tag-Name…', value:tagInput,
            onChange: function(e){ setTagInput(e.target.value); },
            onKeyDown: function(e){
              if (e.key==='Enter'){ onAddTag(tagInput); setTagInput(''); setShowTag(false); }
              if (e.key==='Escape'){ setTagInput(''); setShowTag(false); }
            },
          }),
          React.createElement('button', { className:'pbtn primary', style:{ height:28, padding:'0 10px', fontSize:12, gap:5 },
            onClick: function(){ onAddTag(tagInput); setTagInput(''); setShowTag(false); }
          }, 'OK'),
          React.createElement('button', { className:'pbtn ghost', style:{ height:28, padding:'0 8px', fontSize:12 },
            onClick: function(){ setTagInput(''); setShowTag(false); }
          }, React.createElement(Icon, { name:'x', size:13 })))
      : React.createElement('button', { className:'ts-selbar-btn', onClick: function(){ setShowTag(true); } },
          React.createElement(Icon, { name:'tag', size:14 }), 'Tag hinzufügen');

    var cropOpts = showCrop && React.createElement('div', { className:'ts-crop-menu' },
      FMTS.map(function(f){
        return React.createElement('button', {
          key:f, className:'ts-crop-opt',
          onClick: function(){ setShowCrop(false); },
        }, f);
      }));

    return React.createElement('div', { className:'ts-selbar' },
      React.createElement('span', { className:'ts-selbar-count' }, count + ' ausgewählt'),
      React.createElement('div', { className:'ts-selbar-sep' }),
      tagSection,
      React.createElement('button', { className:'ts-selbar-btn' },
        React.createElement(Icon, { name:'upscale', size:14 }), 'Upscale'),
      React.createElement('div', { style:{ position:'relative' } },
        React.createElement('button', { className:'ts-selbar-btn', onClick: function(){ setShowCrop(function(o){ return !o; }); } },
          React.createElement(Icon, { name:'crop', size:14 }), 'Zuschneiden',
          React.createElement(Icon, { name:'chevronDown', size:11 })),
        cropOpts),
      React.createElement('button', { className:'ts-selbar-btn danger', onClick: onRemove },
        React.createElement(Icon, { name:'trash', size:14 }), 'Entfernen'),
      React.createElement('div', { style:{ flex:1 } }),
      React.createElement('button', { className:'ts-selbar-btn muted', onClick: onClear },
        React.createElement(Icon, { name:'x', size:13 }), 'Auswahl aufheben'));
  }

  /* ── Main Editor ── */
  function TSEditor(props) {
    var set    = props.set;
    var assets = props.assets;
    var onBack = props.onBack;

    var initPool = useMemo(function(){ return assets.filter(function(a){ return set.imageIds.includes(a.id); }); }, [set, assets]);
    var imagesState   = useState(initPool);    var images = imagesState[0];    var setImages   = imagesState[1];
    var selectedState = useState(new Set());   var selected = selectedState[0]; var setSelected = selectedState[1];
    var tagFiltState  = useState([]);           var tagFilters = tagFiltState[0]; var setTagFilters = tagFiltState[1];
    var searchState   = useState('');           var search = searchState[0];    var setSearch   = searchState[1];
    var sizeState     = useState('medium');     var gridSize = sizeState[0];    var setGridSize = sizeState[1];
    var lbState       = useState(null);         var lightboxId = lbState[0];    var setLbId     = lbState[1];
    var srState       = useState(false);        var showSR = srState[0];        var setShowSR   = srState[1];
    var lastSelState  = useState(null);         var lastSelId = lastSelState[0]; var setLastSelId = lastSelState[1];
    var ctxState      = useState(null);         var ctxMenu = ctxState[0];      var setCtxMenu  = ctxState[1];
    var sortState     = useState('default');    var sortBy = sortState[0];      var setSortBy   = sortState[1];
    var groupState    = useState('none');       var groupBy = groupState[0];    var setGroupBy  = groupState[1];

    var st = STATUS[set.status];

    var tagCounts = useMemo(function(){
      var c = {};
      images.forEach(function(img){ img.tags.forEach(function(t){ c[t.name]=(c[t.name]||0)+1; }); });
      return Object.entries(c).sort(function(a,b){ return b[1]-a[1]; }).slice(0,14).map(function(e){ return { name:e[0], count:e[1] }; });
    }, [images]);

    var filtered = useMemo(function(){
      var base = images.filter(function(img){
        if (tagFilters.length>0 && !tagFilters.every(function(tf){ return img.tags.some(function(t){ return t.name===tf; }); })) return false;
        if (search && !img.caption.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
      });

      /* ── Sorting ── */
      var sorted = base.slice();
      if (sortBy === 'width-asc')      sorted.sort(function(a,b){ return a.dims.w - b.dims.w; });
      else if (sortBy === 'width-desc') sorted.sort(function(a,b){ return b.dims.w - a.dims.w; });
      else if (sortBy === 'height-asc')      sorted.sort(function(a,b){ return a.dims.h - b.dims.h; });
      else if (sortBy === 'height-desc') sorted.sort(function(a,b){ return b.dims.h - a.dims.h; });
      else if (sortBy === 'area-asc')       sorted.sort(function(a,b){ return (a.dims.w*a.dims.h) - (b.dims.w*b.dims.h); });
      else if (sortBy === 'area-desc')      sorted.sort(function(a,b){ return (b.dims.w*b.dims.h) - (a.dims.w*a.dims.h); });

      /* ── Grouping ── */
      if (groupBy === 'none') return sorted;

      if (groupBy === 'ar') {
        var groups = {};
        sorted.forEach(function(img){
          var ar = (img.ar.w + ':' + img.ar.h);
          if (!groups[ar]) groups[ar] = [];
          groups[ar].push(img);
        });
        return { _isGrouped: true, groups: groups, sorted: sorted };
      }

      if (groupBy === 'tags' && tagFilters.length > 0) {
        var tgroups = {};
        sorted.forEach(function(img){
          var key = tagFilters.filter(function(tf){ return img.tags.some(function(t){ return t.name===tf; }); }).join('+') || 'sonst';
          if (!tgroups[key]) tgroups[key] = [];
          tgroups[key].push(img);
        });
        return { _isGrouped: true, groups: tgroups, sorted: sorted };
      }

      return sorted;
    }, [images, tagFilters, search, sortBy, groupBy]);

    var lightboxImg = lightboxId != null ? images.find(function(i){ return i.id===lightboxId; }) : null;
    var anySelected = selected.size > 0;

    /* ── selection helpers ── */
    function toggleSel(id) {
      setLastSelId(id);
      setSelected(function(prev){ var n = new Set(prev); if(n.has(id)) n.delete(id); else n.add(id); return n; });
    }
    function rangeSelect(id) {
      if (!lastSelId) { toggleSel(id); return; }
      var ids = filtered.map(function(i){ return i.id; });
      var from = ids.indexOf(lastSelId); var to = ids.indexOf(id);
      if (from===-1 || to===-1) { toggleSel(id); return; }
      var lo = Math.min(from,to); var hi = Math.max(from,to);
      setSelected(function(prev){ var n = new Set(prev); ids.slice(lo,hi+1).forEach(function(rid){ n.add(rid); }); return n; });
      setLastSelId(id);
    }
    function selectAll() { setSelected(new Set(filtered.map(function(i){ return i.id; }))); }
    function clearSel()  { setSelected(new Set()); }

    /* ── batch / single mutations ── */
    function batchRemove() {
      setImages(function(p){ return p.filter(function(i){ return !selected.has(i.id); }); });
      setSelected(new Set());
    }
    function batchAddTag(name) {
      if (!name.trim()) return;
      setImages(function(p){ return p.map(function(img){
        if (!selected.has(img.id)) return img;
        if (img.tags.some(function(t){ return t.name===name; })) return img;
        return Object.assign({}, img, { tags: img.tags.concat([{ name:name, kind:'manual' }]) });
      }); });
    }
    /* context-menu variants: operate on target img OR whole selection if target is in it */
    function imgAddTag(imgId, name) {
      if (!name.trim()) return;
      var ids = (selected.has(imgId) && selected.size>0) ? selected : new Set([imgId]);
      setImages(function(p){ return p.map(function(img){
        if (!ids.has(img.id)) return img;
        if (img.tags.some(function(t){ return t.name===name; })) return img;
        return Object.assign({}, img, { tags: img.tags.concat([{ name:name, kind:'manual' }]) });
      }); });
    }
    function imgRemove(imgId) {
      var ids = (selected.has(imgId) && selected.size>0) ? selected : new Set([imgId]);
      setImages(function(p){ return p.filter(function(i){ return !ids.has(i.id); }); });
      setSelected(function(prev){ var n = new Set(prev); ids.forEach(function(id){ n.delete(id); }); return n; });
    }
    function applySR(find, repl, scope) {
      var ids = scope==='selection' ? selected : new Set(images.map(function(i){ return i.id; }));
      setImages(function(p){ return p.map(function(img){
        if (!ids.has(img.id)) return img;
        return Object.assign({}, img, { caption: img.caption.split(find).join(repl) });
      }); });
    }
    function updateImg(id, patch) {
      setImages(function(p){ return p.map(function(img){ return img.id===id ? Object.assign({},img,patch) : img; }); });
    }
    function removeImg(id) {
      setImages(function(p){ return p.filter(function(i){ return i.id!==id; }); });
      setSelected(function(prev){ var n = new Set(prev); n.delete(id); return n; });
    }

    var colMap = { small:'repeat(auto-fill,minmax(96px,1fr))', medium:'repeat(auto-fill,minmax(148px,1fr))', large:'repeat(auto-fill,minmax(220px,1fr))' };

    /* header */
    var hdr = React.createElement('div', { className:'ts-detail-head' },
      React.createElement('button', { className:'back-row', onClick:onBack },
        React.createElement(Icon, { name:'arrowLeft', size:15 }), 'Alle Sets'),
      React.createElement('div', { style:{ flex:1, display:'flex', alignItems:'center', gap:10, minWidth:0 } },
        set.personId!=null && React.createElement(Avatar, { personId:set.personId, size:36 }),
        React.createElement('div', { style:{ minWidth:0 } },
          React.createElement('div', { style:{ fontSize:16, fontWeight:700, letterSpacing:'-.01em', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' } }, set.name),
          React.createElement('div', { style:{ fontSize:11, color:'var(--text-3)', fontFamily:'var(--mono)', marginTop:1, overflow:'hidden', whiteSpace:'nowrap', textOverflow:'ellipsis' } }, images.length + ' Bilder · ' + set.targetModel))),
      React.createElement('span', { style:{ fontSize:11, fontWeight:700, padding:'4px 9px', borderRadius:7, background:st.bg, color:st.col, flexShrink:0 } }, st.label),
      React.createElement('button', { className:'pbtn ghost ts-head-zip', style:{ height:34, fontSize:12.5, padding:'0 12px', flexShrink:0, gap:7 } },
        React.createElement(Icon, { name:'export', size:14 }),
        React.createElement('span', { className:'ts-zip-lbl' }, 'Als ZIP')));

    /* toolbar */
    var allChip = React.createElement('button', {
      key:'__all',
      className:'ts-tag-filter-chip' + (tagFilters.length===0 ? ' active' : ''),
      onClick: function(){ setTagFilters([]); },
    }, 'Alle ' + images.length);

    var filterChips = tagCounts.map(function(tc){
      var on = tagFilters.includes(tc.name);
      return React.createElement('button', {
        key:tc.name,
        className:'ts-tag-filter-chip' + (on ? ' active' : ''),
        onClick: function(){ setTagFilters(function(prev){ return on ? prev.filter(function(t){ return t!==tc.name; }) : prev.concat([tc.name]); }); },
      }, tc.name, React.createElement('span', { className:'ts-tfc-badge' }, tc.count));
    });

    var sizeBtns = [['small','grid'],['medium','layers'],['large','gallery']].map(function(p){
      return React.createElement('button', {
        key:p[0], title:p[0],
        className:'iconbtn' + (gridSize===p[0] ? ' active' : ''),
        onClick: function(){ setGridSize(p[0]); },
      }, React.createElement(Icon, { name:p[1], size:15 }));
    });

    /* Sort menu */
    var sortOpts = [
      { key:'default', label:'Standard' },
      { key:'width-asc',  label:'Breite (aufsteigend)' },
      { key:'width-desc', label:'Breite (absteigend)' },
      { key:'height-asc',  label:'Höhe (aufsteigend)' },
      { key:'height-desc', label:'Höhe (absteigend)' },
      { key:'area-asc',   label:'Fläche (aufsteigend)' },
      { key:'area-desc',  label:'Fläche (absteigend)' },
    ];
    var sortMenuState = useState(false);
    var sortMenuOpen = sortMenuState[0]; var setSortMenuOpen = sortMenuState[1];
    var sortBtnRef = useRef(null);
    var sortPosState = useState({ top: 0, left: 0 });
    var sortPos = sortPosState[0]; var setSortPos = sortPosState[1];

    useEffect(function() {
      if (!sortMenuOpen || !sortBtnRef.current) return;
      var rect = sortBtnRef.current.getBoundingClientRect();
      setSortPos({ top: rect.bottom + 6, left: rect.left });
    }, [sortMenuOpen]);

    /* Group menu */
    var groupOpts = [
      { key:'none', label:'Keine Gruppierung' },
      { key:'ar', label:'Nach Seitenverhältnis' },
    ];
    if (tagFilters.length > 0) {
      groupOpts.push({ key:'tags', label:'Nach ausgewählten Tags' });
    }
    var groupMenuState = useState(false);
    var groupMenuOpen = groupMenuState[0]; var setGroupMenuOpen = groupMenuState[1];
    var groupBtnRef = useRef(null);
    var groupPosState = useState({ top: 0, left: 0 });
    var groupPos = groupPosState[0]; var setGroupPos = groupPosState[1];

    useEffect(function() {
      if (!groupMenuOpen || !groupBtnRef.current) return;
      var rect = groupBtnRef.current.getBoundingClientRect();
      setGroupPos({ top: rect.bottom + 6, left: rect.left });
    }, [groupMenuOpen]);

    var toolbar = React.createElement('div', { className:'ts-toolbar' },
      React.createElement('div', { className:'ts-tag-filter-row' }, allChip, filterChips),
      React.createElement('div', { style:{ flex:1 } }),
      React.createElement('div', { className:'tag-search', style:{ width:190 } },
        React.createElement(Icon, { name:'search', size:13, style:{ color:'var(--text-3)' } }),
        React.createElement('input', { placeholder:'Caption suchen…', value:search, onChange:function(e){ setSearch(e.target.value); } })),
      React.createElement('div', { style:{ display:'flex', gap:3 } }, sizeBtns),
      React.createElement('div', { style:{ position:'relative' } },
        React.createElement('button', { ref:sortBtnRef, className:'ts-toolbar-btn', onClick: function(){ setSortMenuOpen(function(o){ return !o; }); } },
          React.createElement(Icon, { name:'sort', size:14 }), 'Sortieren',
          React.createElement(Icon, { name:'chevronDown', size:11 })),
        sortMenuOpen && React.createElement('div', { className:'ts-sort-menu', style:{ position:'fixed', top:sortPos.top, left:sortPos.left, zIndex:101 } },
          sortOpts.map(function(opt){
            return React.createElement('button', {
              key: opt.key,
              className: 'ts-sort-opt' + (sortBy===opt.key ? ' active' : ''),
              onClick: function(){ setSortBy(opt.key); setSortMenuOpen(false); },
            }, opt.label);
          }))),
      React.createElement('div', { style:{ position:'relative' } },
        React.createElement('button', { ref:groupBtnRef, className:'ts-toolbar-btn', onClick: function(){ setGroupMenuOpen(function(o){ return !o; }); } },
          React.createElement(Icon, { name:'stack', size:14 }), 'Gruppieren',
          React.createElement(Icon, { name:'chevronDown', size:11 })),
        groupMenuOpen && React.createElement('div', { className:'ts-sort-menu', style:{ position:'fixed', top:groupPos.top, left:groupPos.left, zIndex:101 } },
          groupOpts.map(function(opt){
            return React.createElement('button', {
              key: opt.key,
              className: 'ts-sort-opt' + (groupBy===opt.key ? ' active' : ''),
              onClick: function(){ setGroupBy(opt.key); setGroupMenuOpen(false); },
            }, opt.label);
          }))),
      React.createElement('button', { className:'ts-toolbar-btn', onClick: anySelected ? clearSel : selectAll },
        React.createElement(Icon, { name: anySelected ? 'x' : 'select', size:14 }),
        anySelected ? 'Aufheben' : 'Alle wählen'),
      React.createElement('button', { className:'ts-toolbar-btn', onClick:function(){ setShowSR(true); } },
        React.createElement(Icon, { name:'refresh', size:14 }), 'Such. & Ers.'));

    /* grid */
    /* grid */
    var gridEl;
    if (filtered.length === 0 || (filtered._isGrouped && Object.keys(filtered.groups).length === 0)) {
      gridEl = React.createElement('div', { className:'ts-editor-grid-wrap' },
        React.createElement('div', { className:'placeholder-view', style:{ minHeight:200 } },
          React.createElement(Icon, { name:'search', size:32, style:{ color:'var(--text-3)' } }),
          React.createElement('p', null, 'Keine Bilder für diesen Filter')));
    } else if (filtered._isGrouped) {
      /* Grouped view */
      var groupKeys = Object.keys(filtered.groups).sort();
      var groupEls = groupKeys.map(function(gKey){
        var groupImgs = filtered.groups[gKey];
        var groupLabel = gKey;
        if (groupBy === 'ar') {
          groupLabel = 'Seitenverhältnis ' + gKey;
        } else if (groupBy === 'tags') {
          groupLabel = gKey === 'sonst' ? 'Andere' : 'Tags: ' + gKey;
        }
        var cellsInGroup = groupImgs.map(function(img){
          return React.createElement(TSImgCell, {
            key:img.id, img:img,
            selected:selected.has(img.id), anySelected:anySelected,
            onToggle:      toggleSel,
            onOpen:        function(id){ setLbId(id); },
            onRangeSelect: rangeSelect,
            onContextMenu: function(id, x, y){ setCtxMenu({ imgId:id, x:x, y:y }); },
          });
        });
        return React.createElement('div', { key:gKey, className:'ts-group-section' },
          React.createElement('div', { className:'ts-group-header' }, groupLabel + ' (' + groupImgs.length + ')'),
          React.createElement('div', { className:'ts-editor-grid', style:{ gridTemplateColumns:colMap[gridSize] } }, cellsInGroup));
      });
      gridEl = React.createElement('div', { className:'ts-editor-grid-wrap' }, groupEls);
    } else {
      /* Flat view */
      var cells = filtered.map(function(img){
        return React.createElement(TSImgCell, {
          key:img.id, img:img,
          selected:selected.has(img.id), anySelected:anySelected,
          onToggle:      toggleSel,
          onOpen:        function(id){ setLbId(id); },
          onRangeSelect: rangeSelect,
          onContextMenu: function(id, x, y){ setCtxMenu({ imgId:id, x:x, y:y }); },
        });
      });
      gridEl = React.createElement('div', { className:'ts-editor-grid-wrap' },
        React.createElement('div', { className:'ts-editor-grid', style:{ gridTemplateColumns:colMap[gridSize] } }, cells));
    }

    return React.createElement('div', { className:'ts-detail' },
      hdr,
      toolbar,
      gridEl,
      React.createElement(TSSelBar, { count:selected.size, onAddTag:batchAddTag, onRemove:batchRemove, onClear:clearSel }),
      lightboxImg && React.createElement(TSLightbox, { img:lightboxImg, onClose:function(){ setLbId(null); }, onRemove:removeImg, onUpdate:updateImg }),
      showSR && React.createElement(TSSearchReplace, { hasSelection:selected.size>0, onApply:applySR, onClose:function(){ setShowSR(false); } }),
      ctxMenu && React.createElement(TSContextMenu, {
        imgId:       ctxMenu.imgId,
        x:           ctxMenu.x,
        y:           ctxMenu.y,
        isSelected:  selected.has(ctxMenu.imgId),
        selCount:    selected.size,
        onClose:     function(){ setCtxMenu(null); },
        onOpen:      function(id){ setCtxMenu(null); setLbId(id); },
        onToggle:    toggleSel,
        onAddTag:    imgAddTag,
        onRemove:    imgRemove,
      }));
  }

  /* ── Overview card ── */
  function SetCard(props) {
    var set = props.set; var assets = props.assets; var onClick = props.onClick;
    var imgs = useMemo(function(){ return assets.filter(function(a){ return set.imageIds.includes(a.id); }).slice(0,4); }, [set, assets]);
    var avgQ = useMemo(function(){
      var pool = assets.filter(function(a){ return set.imageIds.includes(a.id); });
      return pool.length ? pool.reduce(function(s,a){ return s+a.quality; },0)/pool.length : 0;
    }, [set, assets]);
    var st = STATUS[set.status];

    var coverInner = imgs.length>0
      ? React.createElement('div', { className:'ts-cover-grid' + (imgs.length<4 ? ' single' : '') },
          imgs.map(function(img){
            return React.createElement('div', { key:img.id, className:'ts-cover-cell' },
              React.createElement(Img, { src:img.photo, bg:img.bg }));
          }))
      : React.createElement('div', { className:'ts-cover-empty' },
          React.createElement(Icon, { name:'training', size:28, style:{ color:'var(--text-3)' } }));

    return React.createElement('div', { className:'ts-card', onClick:onClick },
      React.createElement('div', { className:'ts-cover' },
        coverInner,
        set.personId!=null && React.createElement('div', { className:'ts-person-badge' },
          React.createElement(Avatar, { personId:set.personId, size:28 })),
        React.createElement('div', { style:{ position:'absolute', top:9, right:9, fontSize:10, fontWeight:700, letterSpacing:'.03em', padding:'3px 8px', borderRadius:6, background:st.bg, color:st.col } }, st.label)),
      React.createElement('div', { className:'ts-card-info' },
        React.createElement('div', { className:'ts-card-name' }, set.name),
        React.createElement('div', { className:'ts-card-meta' },
          React.createElement('span', { className:'mono' }, set.imageIds.length + ' Bilder'),
          React.createElement('span', { className:'dotsep' }, '·'),
          React.createElement('span', null, set.targetModel),
          React.createElement('span', { className:'dotsep' }, '·'),
          React.createElement('span', { className:'mono', style:{ fontSize:'10px' } }, 'Ø ' + (imgs.length > 0 ? (imgs.reduce(function(s,img){ return s + img.dims.w; }, 0) / imgs.length).toFixed(0) + 'px' : '—'))),
        React.createElement('div', { style:{ marginTop:8 } },
          React.createElement('div', { style:{ height:4, borderRadius:3, background:'var(--surface)', overflow:'hidden' } },
            React.createElement('div', { style:{ height:'100%', borderRadius:3, width:Math.round(avgQ*100)+'%', background:'linear-gradient(90deg,var(--warn),var(--good))' } })),
          React.createElement('div', { style:{ fontSize:10.5, color:'var(--text-3)', marginTop:4, fontFamily:'var(--mono)' } }, 'Qualität ⌀ ' + Math.round(avgQ*100)+'%'))));
  }

  /* ── Root ── */
  function Training(props) {
    var assets    = props.assets;
    var setsState = useState(function(){ return buildSets(assets); });
    var sets      = setsState[0];
    var detailState = useState(null);
    var detailId = detailState[0]; var setDetailId = detailState[1];
    var detail = detailId ? sets.find(function(s){ return s.id===detailId; }) : null;

    if (detail) {
      return React.createElement(TSEditor, { set:detail, assets:assets, onBack:function(){ setDetailId(null); } });
    }

    var cards = sets.map(function(set){
      return React.createElement(SetCard, { key:set.id, set:set, assets:assets, onClick:function(){ setDetailId(set.id); } });
    });

    var newCard = React.createElement('div', { className:'ts-card ts-card-new' },
      React.createElement('div', { className:'ts-cover ts-cover-empty' },
        React.createElement(Icon, { name:'plus', size:28, style:{ color:'var(--text-3)' } })),
      React.createElement('div', { className:'ts-card-info' },
        React.createElement('div', { className:'ts-card-name', style:{ color:'var(--text-3)' } }, 'Neues Set erstellen')));

    return React.createElement('div', { className:'grid-wrap' },
      React.createElement('div', { className:'alb-sec-head', style:{ padding:'22px 22px 14px' } },
        React.createElement('h3', null, 'Trainingssets'),
        React.createElement('span', { className:'m-count' }, sets.length),
        React.createElement('div', { className:'m-line' }),
        React.createElement('button', { className:'selectbtn', style:{ height:34, gap:7 } },
          React.createElement(Icon, { name:'plus', size:15 }), 'Neues Set')),
      React.createElement('div', { className:'ts-grid', style:{ padding:'0 22px 28px' } }, cards, newCard));
  }

  window.Training = Training;
})();
