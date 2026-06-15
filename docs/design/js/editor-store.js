/* Photofant — Editor Config Store
   Shared localStorage persistence for Flux2 templates + upscale settings.
   Loaded before editor-tools.jsx and settings.jsx.  → window.EditorStore */
(function () {
  const KEY = "pf_editor_cfg";

  const DEFAULT_TEMPLATES = [
    { id: 1, name: "Natürliche Verbesserung",     prompt: "A beautiful portrait photo of {person}, enhanced natural lighting, high quality, sharp details", strength: 0.65, steps: 20, guidance: 7.5, seed: -1 },
    { id: 2, name: "Studio-Licht",                prompt: "Studio portrait of {person}, professional soft-box lighting, clean gradient background, photorealistic", strength: 0.70, steps: 25, guidance: 8.0, seed: 42 },
    { id: 3, name: "Tageslicht Outdoor",           prompt: "Outdoor portrait of {person}, natural daylight, shallow depth of field, candid photography", strength: 0.60, steps: 20, guidance: 7.0, seed: -1 },
    { id: 4, name: "Cinematisch Kontrastreich",    prompt: "Cinematic portrait of {person}, dramatic side lighting, dark atmosphere, film grain, sharp", strength: 0.55, steps: 18, guidance: 6.5, seed: 777 },
    { id: 5, name: "Weich & Atmosphärisch",        prompt: "Soft dreamy portrait of {person}, ethereal lighting, pastel tones, artistic fine-art photography", strength: 0.70, steps: 22, guidance: 7.0, seed: -1 },
    { id: 6, name: "Schärfe-Boost",               prompt: "Ultra-sharp detailed portrait of {person}, crispy details, 4K quality, high dynamic range", strength: 0.45, steps: 15, guidance: 6.0, seed: -1 },
  ];

  const DEFAULT_UPSCALE = {
    defaultModel: "seedvr2_3b_fp8",
    targetSize: 2048,
    tileSize: 1024,
    tilePadding: 32,
    denoisingStrength: 0.2,
    refinePrompt: "sharp detailed portrait, high quality, photorealistic, crisp details",
    refineSteps: 1,
    refineGuidance: 7.0,
  };

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return {
          templates: parsed.templates || DEFAULT_TEMPLATES,
          upscale: { ...DEFAULT_UPSCALE, ...(parsed.upscale || {}) },
          _nextId: parsed._nextId || 100,
        };
      }
    } catch (e) {}
    return { templates: DEFAULT_TEMPLATES.map(t => ({...t})), upscale: { ...DEFAULT_UPSCALE }, _nextId: 100 };
  }

  function save(cfg) {
    try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) {}
  }

  let _cfg = load();
  const _listeners = new Set();

  function notify() { _listeners.forEach(fn => fn({ ..._cfg })); }

  window.EditorStore = {
    get: () => ({ ..._cfg, templates: _cfg.templates.map(t => ({...t})), upscale: { ..._cfg.upscale } }),

    subscribe: (fn) => { _listeners.add(fn); return () => _listeners.delete(fn); },

    // templates
    setTemplates: (templates) => {
      _cfg = { ..._cfg, templates };
      save(_cfg); notify();
    },
    addTemplate: (t) => {
      const id = _cfg._nextId++;
      _cfg = { ..._cfg, templates: [..._cfg.templates, { ...t, id }], _nextId: _cfg._nextId };
      save(_cfg); notify(); return id;
    },
    updateTemplate: (id, patch) => {
      _cfg = { ..._cfg, templates: _cfg.templates.map(t => t.id === id ? { ...t, ...patch } : t) };
      save(_cfg); notify();
    },
    deleteTemplate: (id) => {
      _cfg = { ..._cfg, templates: _cfg.templates.filter(t => t.id !== id) };
      save(_cfg); notify();
    },
    reorderTemplates: (ids) => {
      const map = Object.fromEntries(_cfg.templates.map(t => [t.id, t]));
      _cfg = { ..._cfg, templates: ids.map(id => map[id]).filter(Boolean) };
      save(_cfg); notify();
    },

    // upscale settings
    setUpscale: (patch) => {
      _cfg = { ..._cfg, upscale: { ..._cfg.upscale, ...patch } };
      save(_cfg); notify();
    },
  };
})();
