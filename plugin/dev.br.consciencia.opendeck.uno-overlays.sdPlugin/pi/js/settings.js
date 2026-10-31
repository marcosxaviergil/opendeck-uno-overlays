/* Plugin settings page (OpenDeck: Plugins → UNO Overlays → Settings), served by the plugin on 127.0.0.1.
   The token arrives in the URL fragment and goes back in the X-UNO-Token header (uno/localpage.py).
   Lists save as they change, like the Macro editor of the inspector; the OBS form saves on submit. */
'use strict';

const token = location.hash.slice(1);
history.replaceState(null, '', location.pathname);  // keep the token out of the address bar and history
const el = id => document.getElementById(id);
const EVENTS = () => [['obsIn', t('OBS: scene goes to program')], ['obsOut', t('OBS: scene leaves program')],
  ['obsStreamStart', t('OBS: streaming starts')], ['obsStreamStop', t('OBS: streaming stops')],
  ['obsRecordStart', t('OBS: recording starts')], ['obsRecordStop', t('OBS: recording stops')],
  ['unoIn', t('UNO: overlay goes on air')], ['unoOut', t('UNO: overlay goes off air')]];
const STATUS = () => ({
  off: t('OBS is off. Keys that use OBS show an alert until you turn it on.'),
  connected: t('Connected to OBS.'),
  'not connected': t('Not connected to OBS. Check that OBS is open, then check host, port and password.'),
});
let state = {apps: [], triggers: [], groups: {}};
const overlayCache = new Map();  // app id → [{id, name}]
const slotCache = new Map();  // app id + overlay id → [{id, name}]
let scenes = [];

async function api(method, body, path = '/api/settings') {
  const headers = {'X-UNO-Token': token, ...(body ? {'Content-Type': 'application/json'} : {})};
  const response = await fetch(path, {method, headers, body: body && JSON.stringify(body)});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || t('The plugin did not answer. Open the settings again from OpenDeck.'));
  return data;
}

function say(text, error = false) {
  el('status').textContent = text;
  el('status').classList.toggle('error', error);
}

// The "?" next to a field, with the text of the catalog ("?settings.<key>").
function tipAfter(rowId, key, label, control) {
  const text = helpText('settings', key);
  if (text && el(rowId)) el(rowId).append(helpTip(text, label, control));
}

const pair = (pairs, empty) => {
  const select = document.createElement('select');
  if (empty !== undefined) select.add(new Option(empty, ''));
  for (const [value, text] of pairs) select.add(new Option(text, value));
  return select;
};
const named = (control, name) => { control.setAttribute('aria-label', name); return control; };
const removeButton = (name, onClick) => {
  const button = Object.assign(document.createElement('button'), {type: 'button', textContent: '×'});
  button.setAttribute('aria-label', name);
  button.addEventListener('click', onClick);
  return button;
};
const appName = app => app.name || t('UNO app {app}', {app: app.id});

// ── saving ──

// Typing waits 500 ms; every section changed meanwhile goes in the same save, so none is dropped.
let saveTimer;
const dirty = new Set();
function saveSoon(section) {
  dirty.add(section);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const body = Object.fromEntries([...dirty].map(name => [name, state[name]]));
    dirty.clear();
    save(body);
  }, 500);
}

async function save(body, message = t('Saved.')) {
  say(t('Saving…'));
  try {
    const answer = await api('POST', body);
    if (answer.language?.current !== LANG.code) { setLanguage(answer.language.current); show(answer); }
    else state = {...state, apps: answer.apps};
    say(message);
    return answer;
  } catch (e) { say(e.message, true); return null; }
}

async function overlaysOf(app) {
  if (!app) return [];
  if (!overlayCache.has(app)) {
    try { overlayCache.set(app, await api('POST', {app}, '/api/overlays')); }
    catch (e) { say(e.message, true); overlayCache.set(app, []); }
  }
  return overlayCache.get(app);
}

async function slotsOf(app, overlay) {
  if (!app || !overlay) return [];
  const key = `${app}::${overlay}`;
  if (!slotCache.has(key)) {
    try { slotCache.set(key, await api('POST', {app, overlay}, '/api/slots')); }
    catch (e) { say(e.message, true); slotCache.set(key, []); }
  }
  return slotCache.get(key);
}

// An overlay picker of one control app; the saved value stays even before the list arrives.
function overlaySelect(app, value, name, onChange) {
  const select = named(pair(value ? [[value, value]] : [], t('Overlay…')), name);
  select.value = value || '';
  overlaysOf(app).then(list => {
    select.replaceChildren(new Option(t('Overlay…'), ''), ...list.map(o => new Option(o.name, o.id)));
    if (value && !list.some(o => o.id === value)) select.add(new Option(value, value));
    select.value = value || '';
  });
  select.addEventListener('change', () => onChange(select.value));
  return select;
}

function slotSelect(app, overlay, number, slotId, name, onChange) {
  const select = named(pair([['0', t('Live / current slot')]]), name);
  select.value = '0';
  slotsOf(app, overlay).then(list => {
    select.replaceChildren(new Option(t('Live / current slot'), '0'));
    list.forEach((slot, index) => select.add(new Option(slot.name || t('Slot {n}', {n: index + 1}), String(index + 1))));
    const index = slotId ? list.findIndex(slot => slot.id === slotId) : Number(number || 0) - 1;
    select.value = String(index + 1);
    if (slotId && index < 0) {
      select.add(new Option(t('Selected slot was removed — select another'), '-1'));
      select.value = '-1';
    }
  });
  select.addEventListener('change', () => {
    const value = Number(select.value);
    const key = `${app}::${overlay}`;
    const item = slotCache.get(key)?.[value - 1];
    onChange(Math.max(0, value), item?.id || '');
  });
  return select;
}

function autoCloseSelect(value, name, onChange) {
  const seconds = [1, 2, 3, 4, ...Array.from({length: 24}, (_, i) => 5 * (i + 1))];
  const select = named(pair([['0', t('Disabled')], ...seconds.map(s => [String(s), t('{n} s', {n: s})])]), name);
  select.value = String(value || 0);
  select.addEventListener('change', () => onChange(Number(select.value) || 0));
  return select;
}

const appSelect = (value, name, onChange) => {
  const select = named(pair(state.apps.map(a => [a.id, appName(a)]), t('Control app…')), name);
  if (value && !state.apps.some(a => a.id === value)) select.add(new Option(t('{app} (not registered)', {app: value}), value));
  select.value = value || '';
  select.addEventListener('change', () => onChange(select.value));
  return select;
};

// ── sections ──

function show(data) {
  state = {...state, ...data};
  el('language').replaceChildren(new Option(t('Automatic (OpenDeck language)'), ''),
    ...Object.entries(LANGUAGE_NAMES).map(([code, name]) => new Option(name, code)));
  el('language').value = data.language.choice;
  el('enabled').checked = data.obs.enabled;
  el('host').value = data.obs.host;
  el('port').value = data.obs.port;
  el('password').value = '';
  el('password').placeholder = data.obs.hasPassword ? t('Saved (type to replace)') : t('None');
  el('clear').checked = false;
  el('clear-row').classList.toggle('hidden', !data.obs.hasPassword);
  el('live').value = data.liveEditDelay;
  for (const tip of document.querySelectorAll('.tip')) tip.remove();
  for (const control of document.querySelectorAll('[aria-describedby]')) control.removeAttribute('aria-describedby');
  tipAfter('language-row', 'language', t('Language'), el('language'));
  tipAfter('obs-legend', 'obs', t('Connect to OBS'));
  tipAfter('host-row', 'host', t('Host'), el('host'));
  tipAfter('port-row', 'port', t('Port'), el('port'));
  tipAfter('password-row', 'password', t('Password'), el('password'));
  tipAfter('live-legend', 'liveEditDelay', t('Edits while on air'), el('live'));
  tipAfter('apps-legend', 'apps', t('Control apps'));
  tipAfter('triggers-legend', 'triggers', t('Triggers'));
  tipAfter('groups-legend', 'groups', t('Exclusive groups'));
  tipAfter('new-token-row', 'addToken', t('Add a control app: API token'), el('new-token'));
  tipAfter('new-group-row', 'newGroup', t('New group name'), el('new-group'));
  renderApps(); renderTriggers(); renderGroups();
}

function renderApps() {
  el('apps').replaceChildren(...state.apps.map((app, i) => {
    const row = document.createElement('div'); row.className = 'field-row inline-row';
    const name = named(Object.assign(document.createElement('input'), {type: 'text', value: app.name, placeholder: app.id}),
      t('Name of control app {app}', {app: app.id}));
    name.addEventListener('input', () => { app.name = name.value; saveSoon('apps'); });
    const id = Object.assign(document.createElement('code'), {textContent: app.id});
    row.append(id, name, removeButton(t('Forget control app {app}', {app: app.id}), () => {
      state.apps.splice(i, 1); renderApps(); save({apps: state.apps}, t('Control app forgotten.'));
    }));
    return row;
  }));
}

function renderTriggers() {
  el('triggers').replaceChildren(...state.triggers.map((trigger, i) => {
    const row = document.createElement('fieldset'); row.className = 'trigger';
    const legend = Object.assign(document.createElement('legend'), {textContent: t('Trigger {n}', {n: i + 1})});
    const change = redraw => { saveSoon('triggers'); if (redraw) renderTriggers(); };
    const on = Object.assign(document.createElement('input'), {type: 'checkbox', checked: trigger.on !== false});
    on.addEventListener('change', () => { trigger.on = on.checked; change(); });
    const onLabel = document.createElement('label'); onLabel.className = 'inline'; onLabel.append(on, t('On'));
    const event = named(pair(EVENTS()), t('Event of trigger {n}', {n: i + 1}));
    event.value = trigger.event;
    event.addEventListener('change', () => { trigger.event = event.value; change(true); });
    row.append(legend, onLabel, event);
    if (['obsIn', 'obsOut'].includes(trigger.event)) {
      const scene = named(Object.assign(document.createElement('input'), {type: 'text', value: trigger.scene || '',
        placeholder: t('OBS scene name')}), t('OBS scene of trigger {n}', {n: i + 1}));
      scene.setAttribute('list', 'obs-scenes');
      scene.addEventListener('input', () => { trigger.scene = scene.value; change(); });
      row.append(scene);
    }
    if (['unoIn', 'unoOut'].includes(trigger.event)) {
      row.append(appSelect(trigger.sourceApp, t('Control app watched by trigger {n}', {n: i + 1}),
        value => { trigger.sourceApp = value; trigger.sourceOverlay = ''; change(true); }));
      row.append(overlaySelect(trigger.sourceApp, trigger.sourceOverlay, t('Overlay watched by trigger {n}', {n: i + 1}),
        value => { trigger.sourceOverlay = value; change(); }));
    }
    const fn = named(pair([['show', t('Show')], ['hide', t('Hide')]]), t('Function of trigger {n}', {n: i + 1}));
    fn.value = trigger.function;
    fn.addEventListener('change', () => { trigger.function = fn.value; change(true); });
    const target = appSelect(trigger.app, t('Control app of trigger {n}', {n: i + 1}),
      value => {
        trigger.app = value; trigger.overlay = ''; trigger.slotNumber = 0; trigger.serverSlotId = '';
        change(true);
      });
    const overlay = overlaySelect(trigger.app, trigger.overlay, t('Overlay of trigger {n}', {n: i + 1}),
      value => {
        trigger.overlay = value; trigger.slotNumber = 0; trigger.serverSlotId = '';
        change(true);
      });
    row.append(fn, target, overlay);
    if (trigger.function === 'show') {
      row.append(slotSelect(
        trigger.app, trigger.overlay, trigger.slotNumber, trigger.serverSlotId,
        t('Server Slot'),
        (number, id) => { trigger.slotNumber = number; trigger.serverSlotId = id; change(); }
      ));
      row.append(autoCloseSelect(
        trigger.autoClose, t('Auto Close'), value => { trigger.autoClose = value; change(); }
      ));
    }
    const delay = named(Object.assign(document.createElement('input'), {type: 'number', min: 0, max: 30000, step: 100,
      value: trigger.delay || 0}), t('Delay of trigger {n} (ms, max 30000)', {n: i + 1}));
    delay.addEventListener('input', () => { trigger.delay = Number(delay.value) || 0; change(); });
    const delayLabel = Object.assign(document.createElement('span'), {className: 'hint', textContent: t('Delay (ms, max 30000)')});
    row.append(delayLabel, delay,
      removeButton(t('Remove trigger {n}', {n: i + 1}), () => { state.triggers.splice(i, 1); change(true); }));
    return row;
  }));
  if (!el('obs-scenes')) document.body.append(Object.assign(document.createElement('datalist'), {id: 'obs-scenes'}));
  el('obs-scenes').replaceChildren(...scenes.map(name => new Option(name)));
}

function renderGroups() {
  el('groups').replaceChildren(...Object.entries(state.groups).map(([name, group]) => {
    const box = document.createElement('fieldset'); box.className = 'trigger';
    box.append(Object.assign(document.createElement('legend'), {textContent: name}));
    const delay = named(Object.assign(document.createElement('input'), {type: 'number', min: -30, max: 30, step: 0.5,
      value: group.delay || 0}), t('Time of group {name} (s)', {name}));
    delay.addEventListener('input', () => { group.delay = Number(delay.value) || 0; saveSoon('groups'); });
    const time = Object.assign(document.createElement('span'), {className: 'hint',
      textContent: t('Time (s): > 0 waits before this one goes in; < 0 old ones go out later')});
    box.append(time, delay);
    group.members.forEach((member, i) => {
      const row = document.createElement('div'); row.className = 'field-row inline-row';
      row.append(appSelect(member.app, t('Control app of member {n} of {name}', {n: i + 1, name}),
        value => { member.app = value; member.overlay = ''; saveSoon('groups'); renderGroups(); }));
      row.append(overlaySelect(member.app, member.overlay, t('Overlay of member {n} of {name}', {n: i + 1, name}),
        value => { member.overlay = value; saveSoon('groups'); }));
      row.append(removeButton(t('Remove member {n} of {name}', {n: i + 1, name}),
        () => { group.members.splice(i, 1); saveSoon('groups'); renderGroups(); }));
      box.append(row);
    });
    const add = Object.assign(document.createElement('button'), {type: 'button', textContent: t('Add overlay')});
    add.addEventListener('click', () => { group.members.push({app: state.apps[0]?.id || '', overlay: ''}); renderGroups(); });
    const remove = Object.assign(document.createElement('button'), {type: 'button', textContent: t('Delete group')});
    remove.addEventListener('click', () => { delete state.groups[name]; saveSoon('groups'); renderGroups(); });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(add, remove);
    box.append(actions);
    return box;
  }));
}

// ── events ──

el('obs').addEventListener('submit', async event => {
  event.preventDefault();
  say(t('Saving…'));
  try {
    let data = await api('POST', {obs: {enabled: el('enabled').checked, host: el('host').value, port: el('port').value,
      password: el('password').value, clearPassword: el('clear').checked}});
    show(data);
    say(t('Saved. Connecting…'));
    for (let i = 0; i < 10 && data.status === 'not connected'; i++) {  // the plugin connects in the background
      await new Promise(resolve => setTimeout(resolve, 1000));
      data = await api('GET');
    }
    say(STATUS()[data.status], data.status === 'not connected');
    if (data.status === 'connected') loadScenes();
  } catch (e) { say(e.message, true); }
});

el('language').addEventListener('change', () => save({language: el('language').value}));
el('live').addEventListener('change', () => save({liveEditDelay: Number(el('live').value) || 0}));
el('add-app').addEventListener('click', async () => {
  const answer = await save({addToken: el('new-token').value.trim(), addName: el('new-name').value.trim()}, t('Control app added.'));
  if (answer) { el('new-token').value = ''; el('new-name').value = ''; show(answer); }
});
el('add-trigger').addEventListener('click', () => {
  state.triggers.push({on: true, event: 'obsIn', scene: '', function: 'show', app: state.apps[0]?.id || '', overlay: '',
    slotNumber: 0, serverSlotId: '', autoClose: 0, delay: 0});
  renderTriggers();
  el('triggers').lastElementChild?.querySelector('select')?.focus();
});
el('add-group').addEventListener('click', () => {
  const name = el('new-group').value.trim();
  if (!name || state.groups[name]) return say(name ? t('That name exists.') : t('Type a name.'), true);
  state.groups[name] = {delay: 0, members: []};
  el('new-group').value = '';
  saveSoon('groups'); renderGroups();
});

async function loadScenes() {
  try { scenes = (await api('POST', {}, '/api/obs')).scenes || []; renderTriggers(); } catch { /* OBS off: type the name */ }
}

api('GET').then(data => {
  setLanguage(data.language.current);
  show(data);
  say(STATUS()[data.status]);
  if (data.status === 'connected') loadScenes();
}).catch(e => say(e.message, true));