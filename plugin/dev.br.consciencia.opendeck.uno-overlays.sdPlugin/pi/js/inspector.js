/* Inspector core: settings, the form helpers every action uses, building by action and loading UNO lists.
   Features extend Inspector.prototype in the other files (overlay, obs, editors, definitions, status, pickers). */
'use strict';

const clone = value => JSON.parse(JSON.stringify(value));
const el = id => document.getElementById(id);
const icon = key => Object.assign(document.createElement('span'), {className: 'ms', textContent: GLYPHS[key] || '', ariaHidden: 'true'});
// Unbound controls for rows and lists: a <select> of [value, text] pairs with an optional empty first option, and an input.
const choose = (pairs, empty) => {
  const select = document.createElement('select');
  if (empty !== undefined) select.add(new Option(empty, ''));
  for (const [value, text] of pairs) select.add(new Option(text, value));
  return select;
};
const textBox = (type = 'text', placeholder = '') =>
  Object.assign(document.createElement(type === 'area' ? 'textarea' : 'input'), type === 'area' ? {placeholder} : {type, placeholder});
const FIELD_ACTIONS = ['clock', 'undo', 'swap', 'cycle', 'reset', 'datasource', 'template', 'vote', 'goal', 'reveal'];
// Shared definitions in the global settings: [settings key, global key, label].
const DEFS = {datasource: ['source', 'dataSources', () => t('Data source')], vote: ['poll', 'polls', () => t('Poll')],
  goal: ['goal', 'goals', () => t('Goal')]};
const NO_TOKEN = ['multiplier', 'visor', 'obsrefresh', 'shift', 'status', 'lockdesk'];
// Keys without the optional second-press confirmation: held keys, the desk lock and read-only keys.
const NO_CONFIRM = ['shift', 'reset', 'lockdesk', 'display', 'knob'];
const OBS_ACTIONS = ['obsscene', 'obsrefresh', 'macro'];
// Action -> method that draws its controls (files: builders, overlay, obs, editors, definitions, status).
const BUILDERS = {multiplier: 'buildMultiplier', toggle: 'buildToggle', numericfields: 'buildNumeric', display: 'buildNumeric',
  nextslot: 'buildSlots', prevslot: 'buildSlots', slotwheel: 'buildSlots', dialvalue: 'buildFieldKnob', timer: 'buildFieldKnob',
  clock: 'buildClock', undo: 'buildUndo', cycle: 'buildCycle', reset: 'buildReset', swap: 'buildSwap',
  datasource: 'buildDefinition', vote: 'buildDefinition', goal: 'buildDefinition', status: 'statusPanel',
  lockdesk: 'buildLockDesk', template: 'buildTemplate', macro: 'macroEditor', snapshot: 'buildScene', visor: 'buildVisor',
  obsscene: 'buildObsScene', obsrefresh: 'buildObsRefresh', knob: 'buildKnob', showall: 'buildAll', hideall: 'buildAll',
  reveal: 'buildReveal'};
// Settings that stay when the API token changes: they do not belong to one control app.
const KEEP = ['autoClose', 'delay', 'operation', 'multiplier', 'channel', 'sceneName', 'inputName', 'inputNames', 'refreshMode',
  'refreshScene', 'mode', 'duration', 'until', 'format', 'value', 'yellowAt', 'redAt', 'overtime', 'overtimeSign', 'flash',
  'flashField', 'pauseOffAir', 'knobStep', 'values', 'step', 'min', 'max', 'modelLimits', 'pointSeconds', 'obsOnlyScenes',
  'group', 'steps', 'name', 'pressAgain', 'source', 'poll', 'goal', 'option', 'row', 'amount', 'text', 'tokens', 'carousel',
  'shownValue', 'hiddenValue', 'liveEditDelay', 'confirmSeconds'];

// Accessible names for icon-only buttons (the glyph alone is not a name).
const ICON_LABELS = () => ({close: t('Remove'), up: t('Move up'), down: t('Move down'), star: t('Favorite overlay')});

class Inspector {
  constructor() {
    this.settings = {};
    this.version = 0;
    this.forms = new Map();
    this.modelVersions = new Map();
    this.overlays = [];
    this.serverSlots = new Map();
    this.pendingFields = new Map();
    this.editSerial = 0;
    this.bridge = new OpenDeckBridge((s, action) => this.receive(s, action), error => this.status(error, true));
    this.bridge.onChange = () => this.refreshContent();
    this.bridge.onLanguage = code => { if (code !== LANG.code) { setLanguage(code); if (this.action) this.build(); } };
    this.global = {};
    this.bridge.onGlobal = settings => {
      const enabled = !this.global.obsEnabled && settings.obsEnabled;
      this.global = settings;
      if (enabled) this.loadObs();
      // Keep what is being typed; redraw definitions changed elsewhere (another key, goal state).
      if (!el('def-body')?.contains(document.activeElement)) this.renderDef();
    };
    this.loadedToken = '';
    el('token').addEventListener('input', () => {
      this.settings.token = el('token').value.trim();
      this.version++;
      this.save();
    });
    el('token').addEventListener('change', () => this.changeToken());
    el('reload').addEventListener('click', () => this.changeToken());
    new MutationObserver(() => this.nameControls()).observe(el('controls'), {childList: true, subtree: true});
  }

  receive(settings, action) {
    if (stableStringify(settings) === this.lastSettings && this.action) return;
    this.settings = clone(settings);
    this.lastSettings = stableStringify(settings);
    this.action = action.split('.').pop();
    this.loadedToken = settings.token || '';
    el('token').value = this.loadedToken;
    this.build();
    this.load();
  }

  save() {
    this.lastSettings = stableStringify(this.settings);
    this.bridge.save(this.settings);
  }

  saveGlobal(changes) {
    // Global settings are shared by every action: merge, never replace.
    this.global = {...this.global, ...changes};
    this.bridge.send('setGlobalSettings', this.global);
  }

  status(text, error = false) {
    el('status').textContent = text;
    el('status').classList.toggle('error', error);
  }

  async changeToken() {
    const token = el('token').value.trim();
    if (token !== this.loadedToken) {
      // Payloads and presets belong to their original control app.
      const fresh = {token};
      for (const key of KEEP) if (key in this.settings) fresh[key] = this.settings[key];
      this.settings = fresh;
      this.loadedToken = token;
      this.build();
      this.save();
    }
    await this.load();
  }

  build() {
    this.version++;
    clearInterval(this.statusTimer);
    this.forms.clear();
    const root = el('controls'); root.replaceChildren();
    el('action-name').replaceChildren(icon(this.action), NAMES()[this.action] || 'UNO Overlays');
    el('token-section').classList.toggle('hidden', NO_TOKEN.includes(this.action));
    for (const tip of el('token-section').querySelectorAll('.tip')) tip.remove();
    el('token').removeAttribute('aria-describedby');
    const [tokenHelp, reloadHelp] = [helpText(this.action, 'token'), helpText(this.action, 'reload')];
    if (tokenHelp) el('token-label').after(helpTip(tokenHelp, t('API Token'), el('token')));
    if (reloadHelp) el('reload').after(helpTip(reloadHelp, t('Connect / Reload')));
    this.status('');
    el('help').textContent = helpText(this.action, '');
    if (BUILDERS[this.action]) this[BUILDERS[this.action]](root);
    if (!NO_CONFIRM.includes(this.action)) this.buildSafety(root);
  }

  async load() {
    const version = ++this.version;
    this.loadObs();
    if (NO_TOKEN.includes(this.action) || !this.settings.token) return;
    const api = new UnoApi(this.settings.token, this.bridge); this.api = api;
    this.status(t('Loading UNO…'));
    try {
      const overlays = await api.getOverlays();
      if (version !== this.version) return;
      this.overlays = overlays;
      if (!Array.isArray(this.overlays)) throw new Error(t('UNO returned an invalid overlay list.'));
      const gestures = this.action === 'toggle' ? [''] : this.action === 'knob' ? ['ccw', 'press', 'cw'] : [];
      for (const g of gestures) {
        PIData.populateOverlaySelect(el(this.key(g, 'overlayId')), this.overlays, this.settings[this.key(g, 'overlayId')]);
        this.slots(g);
      }
      if (['nextslot', 'prevslot', 'slotwheel', 'obsscene'].includes(this.action)) {
        PIData.populateOverlaySelect(el('overlayId'), this.overlays, this.settings.overlayId);
        if (this.action === 'obsscene') el('overlayId').options[0].text = t('None');
      }
      if (FIELD_ACTIONS.includes(this.action)) {
        this.allFields = await PIData.loadFields(api, this.overlays, f => f.type !== 'timecontrol');
        if (version !== this.version) return;
        for (const select of document.querySelectorAll('select[data-fields]')) {
          const key = select.dataset.fields;
          const fields = this.allFields.filter(f => this.action !== 'clock' || f.type === 'text');
          const empty = select.options[0].text;
          select.replaceChildren(...(key === 'fields' ? [] : [new Option(select.dataset.empty || empty, '')]),
            ...fields.map(f => new Option(f.label, f.composite)));
          if (key === 'fields') for (const o of select.options) o.selected = (this.settings.fields || []).includes(o.value);
          else select.value = key === 'insert' ? '' : this.settings[key] || '';
        }
        this.renderPairs();
        this.renderDef();
      }
      const firstOption = {shiftOverlayId: t('Same overlay'), pointOverlayId: t('None'), countdownTarget: t('The clock overlay')};
      for (const id of ['shiftOverlayId', 'safe', 'pointOverlayId', 'countdownTarget']) {
        const select = el(id);
        if (!select) continue;
        PIData.populateOverlaySelect(select, this.overlays, id === 'safe' ? '' : this.settings[id]);
        if (id !== 'safe') { select.options[0].text = firstOption[id]; continue; }
        select.remove(0);
        for (const o of select.options) o.selected = (this.settings.safe || []).includes(o.value);
      }
      if (this.action === 'macro') {
        this.allFields = await PIData.loadFields(api, this.overlays, () => true);
        if (version !== this.version) return;
        this.renderSteps();
      }
      // Load each configured form once. Model/content reads do not apply changes.
      await Promise.all(gestures.map(g => this.model(g, version)));
      if (version !== this.version) return;
      if (this.action === 'timer') {
        const timers = await PIData.loadFields(api, this.overlays, f => f.type === 'timecontrol');
        PIData.populateFieldSelect(el('fieldComposite'), timers, this.settings.fieldComposite);
      }
      if (['numericfields', 'display', 'knob', 'dialvalue'].includes(this.action)) {
        const fields = await PIData.loadNumericFields(api, this.overlays);
        if (version !== this.version) return;
        for (const g of this.action === 'knob' ? ['ccw', 'press', 'cw'] : ['']) {
          const key = this.key(g, 'fieldComposite');
          const selected = this.settings[key] || (this.settings.overlayId && this.settings.fieldId ? this.settings.overlayId + '::' + this.settings.fieldId : '');
          PIData.populateFieldSelect(el(key), fields, selected);
        }
        if (el('shiftFieldComposite')) {
          PIData.populateFieldSelect(el('shiftFieldComposite'), fields, this.settings.shiftFieldComposite);
          el('shiftFieldComposite').options[0].text = t('Same field');
        }
      }
      this.status(t('Connected. Field edits are saved to UNO automatically.'));
      this.enhanceSelects();
    } catch (e) {
      if (version === this.version) this.status(e.message, true);
    }
  }

  // ── form helpers: a label, the "?" help when the catalog has one, the control ──

  labelled(parent, key, label, control, helpKey = key) {
    const box = document.createElement('div'); box.className = 'section';
    const row = document.createElement('div'); row.className = 'label-row';
    const title = Object.assign(document.createElement('label'), {htmlFor: control.id, textContent: label});
    row.append(title);
    const help = helpText(this.action, helpKey);
    if (help) row.append(helpTip(help, label, control));
    box.append(row, control); parent.append(box);
    return control;
  }

  group(parent, glyph, title, helpKey) {
    const box = document.createElement('fieldset');
    const legend = document.createElement('legend'); legend.append(icon(glyph), title);
    const help = helpKey && helpText(this.action, helpKey);
    if (help) legend.append(helpTip(help, title));
    box.append(legend); parent.append(box);
    return box;
  }

  select(parent, key, label, options) {
    const select = choose(options); select.id = key;
    select.value = String(this.settings[key] ?? options[0]?.[0] ?? '');
    select.addEventListener('change', () => { this.settings[key] = select.value; this.save(); });
    return this.labelled(parent, key, label, select, this.helpKey(key));
  }

  input(parent, key, label, type = 'text', placeholder = '') {
    const input = Object.assign(document.createElement('input'), {id: key, type, placeholder, autocomplete: 'off'});
    input.value = this.settings[key] ?? '';
    input.addEventListener('input', () => { this.settings[key] = input.value; this.save(); });
    return this.labelled(parent, key, label, input, this.helpKey(key));
  }

  textarea(parent, key, label, placeholder = '') {
    const area = Object.assign(document.createElement('textarea'), {id: key, placeholder, value: this.settings[key] ?? ''});
    area.addEventListener('input', () => { this.settings[key] = area.value; this.save(); });
    return this.labelled(parent, key, label, area, this.helpKey(key));
  }

  fieldSelect(parent, key, label, empty = t('Enter an API token…')) {
    const select = this.select(parent, key, label, [['', empty]]);
    select.dataset.fields = key;
    if (empty === t('Enter an API token…')) select.dataset.empty = t('Select…');
    return select;
  }

  timer(parent, key, title) {
    const seconds = [1, 2, 3, 4, ...Array.from({length: 24}, (_, i) => 5 * (i + 1))];  // 1–4 s, then 5–120 s by 5
    const select = this.select(parent, key, title, [['0', t('Disabled')], ...seconds.map(s => [String(s), t('{n} s', {n: s})])]);
    select.value = String(this.settings[key] || '0');
  }

  // Knob gestures share the help of the same field without the prefix (ccwOverlayId → overlayId).
  helpKey(key) {
    return this.action === 'knob' ? key.replace(/^(ccw|cw|press)(?=[A-Z])/, '').replace(/^./, c => c.toLowerCase()) : key;
  }

  nameControls() {
    // Controls drawn in rows have no visible <label>: name them by their placeholder or empty option.
    for (const control of el('controls').querySelectorAll('input, select, textarea')) {
      if (control.labels?.length || control.hasAttribute('aria-label')) continue;
      const hint = control.placeholder || (control.tagName === 'SELECT' ? control.options[0]?.text : '');
      if (hint) control.setAttribute('aria-label', hint.replace(/…$/, ''));
    }
    const labels = ICON_LABELS();
    for (const button of el('controls').querySelectorAll('button:not([aria-label])')) {
      const glyph = Object.keys(GLYPHS).find(key => GLYPHS[key] === button.textContent);
      if (glyph && labels[glyph]) button.setAttribute('aria-label', labels[glyph]);
    }
  }

  key(g, name) { return g ? g + name[0].toUpperCase() + name.slice(1) : name; }
}
