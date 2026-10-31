// Property inspector in Chromium: every action builds without console errors, every control has an
// accessible name, shared definitions merge into the global settings, search and favorites work.
// OpenDeck's WebSocket is replaced by a stub that answers like the plugin (tests/support.py covers the plugin).
// The plugin settings page runs behind a stand-in of its server (tests/test_settings_page.py covers the real one).
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

let chromium = null;
try { ({chromium} = require('playwright')); } catch { /* skipped below */ }
const skip = chromium ? false : 'playwright is not installed (npm install -g playwright)';

const PLUGIN = path.resolve(__dirname, '../../plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin');
const PAGE = pathToFileURL(path.join(PLUGIN, 'pi/index.html')).href;
const manifest = require(path.join(PLUGIN, 'manifest.json'));
const PREFIX = 'dev.br.consciencia.opendeck.uno-overlays.';

const GLOBAL = {
  obsEnabled: true, obsPort: '4455', favorites: ['OV3'],
  dataSources: {Ticker: {token: 'TOKEN1', kind: 'csv', path: '/tmp/x.csv', header: 'true',
    map: [{field: 'OV1::Score', column: 'Cargo', format: 'Nome: {0}'}]}},
  polls: {Enquete: {token: 'TOKEN1', options: [{votes: 'OV1::Score'}, {votes: 'OV1::Time'}], format: '{0}%'}},
  goals: {Meta: {token: 'TOKEN1', title: 'Meta', goal: '100', state: 'active', started: '2026-09-29T10:00'}},
};

// Answers of the plugin process, keyed by request type or App API command.
const REPLIES = {
  'status.get': {category: 'good', calls: 12, cap: 10000, locked: false,
    items: [{name: 'UNO app 1a2b3c', level: 'good', detail: 'realtime: connected · API: OK · 12 calls today'},
      {name: 'OBS', level: 'error', detail: 'not connected'}],
    log: ['10:00:01  UNO app 1a2b3c: GetOverlays → OK (80 ms)', '10:00:00  Desk locked.']},
  'source.preview': {columns: ['Nome', 'Cargo'], count: 2, rows: [['Maria', 'CEO']]},
  'obs.list': {scenes: ['Main', 'Cam'], browsers: ['UNO Browser']},
  GetOverlays: [{id: 'OV1', name: 'Placar', slots: []}, {id: 'OV2', name: 'Lower third', slots: []},
    {id: 'OV3', name: 'Ticker', slots: []}],
  GetOverlayModel: {groups: [], model: [{id: 'Score', type: 'number', title: 'Score'},
    {id: 'Clock', type: 'timecontrol', title: 'Clock'}, {id: 'Time', type: 'text', title: 'Time'},
    {id: 'TeamA', type: 'text', title: 'Team A'}]},
  GetOverlayContent: {Score: 3, Clock: {UTC: 0, isRunning: false, value: 0}},
  GetSlots: {active: true, currentSlotId: 's1', data: [{id: 's1', name: 'One', payload: {}}]},
};

function stub({global, replies}) {  // addInitScript passes one argument
  window.__sent = [];
  class FakeWS {
    constructor() { this.readyState = 1; setTimeout(() => this.onopen && this.onopen(), 0); }
    send(raw) {
      const m = JSON.parse(raw);
      window.__sent.push(m);
      const deliver = data => setTimeout(() => this.onmessage({data: JSON.stringify(data)}), 5);
      if (m.event === 'getGlobalSettings') deliver({event: 'didReceiveGlobalSettings', payload: {settings: global}});
      if (m.event !== 'sendToPlugin') return;
      const p = m.payload;
      const data = replies[p.type] ?? replies[p.command] ?? null;
      deliver({event: 'sendToPropertyInspector', context: 'ctx', payload: {type: 'uno.result', requestId: p.requestId, data}});
    }
  }
  window.WebSocket = FakeWS;
  WebSocket.OPEN = 1;
}

const SETTINGS = {
  token: 'TOKEN1', overlayId: 'OV1', name: 'Abertura', safe: ['OV1'], channel: '1', mode: 'countdown',
  duration: '00:05:00', yellowAt: '1:00', pairs: [{a: 'OV1::TeamA', b: 'OV1::Score'}], values: '1º\n2º',
  fields: ['OV1::Score'], source: 'Ticker', poll: 'Enquete', goal: 'Meta', option: '2', text: '{OV1::Score}',
  sceneName: 'Cam', inputName: 'UNO Browser',
  steps: [{type: 'show', overlayId: 'OV1'}, {type: 'setfield', fieldComposite: 'OV1::Score', value: '2'},
    {type: 'timer', fieldComposite: 'OV1::Clock'}, {type: 'wait', ms: '500'}, {type: 'obsscene', sceneName: 'Cam'}],
};

async function open(browser, action, settings, replies = REPLIES) {
  const page = await browser.newPage({viewport: {width: 430, height: 1400}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.text()); });
  await page.addInitScript(stub, {global: GLOBAL, replies});
  await page.goto(PAGE);
  await page.evaluate(([uuid, s]) => connectOpenActionSocket(1, 'ctx', 'registerPropertyInspector', '{}',
    JSON.stringify({context: 'ctx', action: uuid, payload: {settings: s}})), [PREFIX + action, settings]);
  await page.waitForTimeout(700);
  return {page, errors};
}

const lastSent = (page, event) => page.evaluate(e => window.__sent.filter(m => m.event === e).map(m => m.payload).pop(), event);

test('property inspector', {skip}, async t => {
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {});
  t.after(() => browser.close());

  for (const action of manifest.Actions.map(a => a.UUID.slice(PREFIX.length))) {
    await t.test(`${action}: builds, no console errors, every control named`, async () => {
      const {page, errors} = await open(browser, action,
        {...SETTINGS, fieldComposite: action === 'timer' ? 'OV1::Clock' : 'OV1::Score'});
      const unnamed = await page.evaluate(() =>
        [...document.querySelectorAll('#controls input, #controls select, #controls textarea, #controls button, #token, #reload')]
          .filter(c => !(c.labels?.length || c.getAttribute('aria-label') || (c.tagName === 'BUTTON' && c.textContent.trim().length > 1)))
          .map(c => `${c.tagName}#${c.id || c.className || '?'}`));
      const title = await page.textContent('#action-name');
      // Item 6 of 2.0.0: a "?" with help next to every field and every group of the action.
      const noHelp = await page.evaluate(() => [...document.querySelectorAll('#controls .label-row, #controls legend, #token-section .label-row')]
        .filter(row => !row.querySelector('.tip')).map(row => row.textContent.trim()));
      const actionHelp = await page.textContent('#help');
      await page.close();
      assert.deepStrictEqual(errors, []);
      assert.deepStrictEqual(unnamed, []);
      assert.deepStrictEqual(noHelp, []);
      assert.ok(actionHelp.trim().length > 10, 'the action has its help text');
      assert.ok(title.trim().length > 1, 'action title shown');
    });
  }

  await t.test('language: the inspector draws in the language the plugin answers (pt-BR)', async () => {
    const {page, errors} = await open(browser, 'clock', {...SETTINGS, fieldComposite: 'OV1::Time'},
      {...REPLIES, 'i18n.get': {language: 'pt-BR'}});
    const seen = await page.evaluate(() => ({
      lang: document.documentElement.lang,
      title: document.querySelector('#action-name').lastChild.textContent.trim(),  // after the icon glyph
      reload: document.querySelector('#reload [data-t]').textContent.trim(),
      help: document.querySelector('#help').textContent,
      tips: [...document.querySelectorAll('#controls .tip')].map(tip => tip.getAttribute('aria-describedby') || tip.id),
    }));
    await page.close();
    assert.deepStrictEqual(errors, []);
    assert.strictEqual(seen.lang, 'pt-BR');
    assert.strictEqual(seen.title, 'Relógio');
    assert.strictEqual(seen.reload, 'Conectar / Recarregar');
    assert.match(seen.help, /Escreve um relógio num campo de texto/);
    assert.ok(seen.tips.length > 5, 'the clock fields have their help');
  });

  await t.test('shared definitions: create and delete merge into the global settings', async () => {
    const {page, errors} = await open(browser, 'datasource', {token: 'TOKEN1', source: 'Ticker'});
    await page.fill('#def-new', 'Novo');
    await page.click('button:has-text("Create")');
    await page.waitForTimeout(100);
    await page.selectOption('#def-body select', 'list');
    await page.fill('#def-body textarea', 'Um\nDois');
    await page.waitForTimeout(900);
    const saved = await lastSent(page, 'setGlobalSettings');
    const key = await lastSent(page, 'setSettings');
    assert.deepStrictEqual(saved.dataSources.Novo, {token: 'TOKEN1', kind: 'list', text: 'Um\nDois', map: []});
    assert.ok(saved.dataSources.Ticker && saved.polls.Enquete && saved.obsEnabled === true, 'other global settings kept');
    assert.strictEqual(key.source, 'Novo');
    await page.click('#def-delete');
    await page.waitForTimeout(500);
    const after = await lastSent(page, 'setGlobalSettings');
    await page.close();
    assert.ok(!after.dataSources.Novo && after.dataSources.Ticker, 'deleted only the chosen one');
    assert.deepStrictEqual(errors, []);
  });

  await t.test('overlay lists: search ignores accents and case, favorites first with ★', async () => {
    const {page, errors} = await open(browser, 'toggle', {token: 'TOKEN1', overlayId: 'OV1'});
    const texts = () => page.evaluate(() => [...document.getElementById('overlayId').options].map(o => o.text));
    const picker = page.locator('#overlayId').locator('xpath=preceding-sibling::div[1]');
    const first = await texts();
    await picker.locator('input').fill('LOWÉR');
    const filtered = await texts();
    await picker.locator('input').fill('');
    await page.selectOption('#overlayId', 'OV2');
    await picker.locator('button').click();
    await page.waitForTimeout(200);
    const starred = await texts();
    const saved = await lastSent(page, 'setGlobalSettings');
    const key = await lastSent(page, 'setSettings');
    await page.close();
    assert.strictEqual(first[1], '★ Ticker');
    assert.ok(filtered.includes('Lower third') && !filtered.includes('★ Ticker'), filtered.join());
    assert.ok(starred.slice(1, 3).every(text => text.startsWith('★ ')), starred.join());
    assert.deepStrictEqual([...saved.favorites].sort(), ['OV2', 'OV3']);
    assert.strictEqual(saved.obsEnabled, true);
    assert.strictEqual(key.overlayId, 'OV2');
    assert.deepStrictEqual(errors, []);
  });
  await t.test('settings page: same-origin scripts under the CSP, token only in a header, OBS, lists and help', async () => {
    // Same headers as uno/localpage.py, so an inline script or style would be blocked and reported.
    const csp = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";
    const files = {'/': ['settings.html', 'text/html'], '/js/i18n.js': ['js/i18n.js', 'text/javascript'],
      '/js/lang.js': ['js/lang.js', 'text/javascript'], '/js/tips.js': ['js/tips.js', 'text/javascript'],
      '/js/settings.js': ['js/settings.js', 'text/javascript'], '/css/styles.css': ['css/styles.css', 'text/css']};
    const posts = [];
    let state = {obs: {enabled: false, host: '127.0.0.1', port: 4455, hasPassword: false}, status: 'off',
      language: {choice: '', current: 'en', opendeck: null}, liveEditDelay: 1000,
      apps: [{id: '1a2b3c', name: 'Placar'}], triggers: [], groups: {}};
    const server = http.createServer((req, res) => {
      const send = (status, body, type = 'application/json') => {
        res.writeHead(status, {'Content-Security-Policy': csp, 'Content-Type': type});
        res.end(body);
      };
      if (req.url.startsWith('/api/')) {
        if (req.headers['x-uno-token'] !== 'tok123') return send(403, '{"error": "no token"}');
        if (req.method === 'GET') return send(200, JSON.stringify(state));
        let body = '';
        req.on('data', chunk => { body += chunk; });
        return req.on('end', () => {
          const data = JSON.parse(body);
          if (req.url === '/api/overlays') return send(200, JSON.stringify([{id: 'OV1', name: 'Lower third'}]));
          if (req.url === '/api/obs') return send(200, JSON.stringify({scenes: ['Main', 'Cam'], browsers: []}));
          posts.push({type: req.headers['content-type'], ...data});
          if (data.obs) state = {...state, obs: {...data.obs, hasPassword: true}, status: 'connected'};
          if (data.triggers) state = {...state, triggers: data.triggers};
          send(200, JSON.stringify(state));
        });
      }
      const file = files[req.url];
      if (!file) return send(404, '{}');
      send(200, fs.readFileSync(path.join(PLUGIN, 'pi', file[0])), file[1]);
    });
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    t.after(() => server.close());
    const page = await browser.newPage({viewport: {width: 520, height: 1400}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.text()); });
    await page.goto(`http://127.0.0.1:${server.address().port}/#tok123`);
    await page.waitForFunction(() => document.getElementById('status').textContent !== '');
    const url = page.url();
    const unnamed = () => page.evaluate(() => [...document.querySelectorAll('input, button, select')]
      .filter(c => !(c.labels?.length || c.getAttribute('aria-label') || (c.tagName === 'BUTTON' && c.textContent.trim())))
      .map(c => c.id || c.tagName));
    const hiddenClear = await page.isHidden('#clear-row');
    // Help: hover or keyboard focus shows the text, Esc hides it, the field is described by it.
    const tip = page.locator('#host-row .tip');
    await tip.locator('button').focus();
    const shownOnFocus = await tip.locator('[role=tooltip]').isVisible();
    await page.keyboard.press('Escape');
    const hiddenOnEsc = await tip.locator('[role=tooltip]').isHidden();
    const described = await page.evaluate(() => !!document.getElementById(document.getElementById('host').getAttribute('aria-describedby') || 'x'));
    await page.check('#enabled');
    await page.fill('#port', '4456');
    await page.fill('#password', 'segredo');
    await page.press('#password', 'Enter');
    await page.waitForFunction(() => document.getElementById('status').textContent === 'Connected to OBS.');
    const after = {password: await page.inputValue('#password'), placeholder: await page.getAttribute('#password', 'placeholder'),
      clearShown: await page.isVisible('#clear-row')};
    await page.click('#add-trigger');
    await page.selectOption('select[aria-label="Event of trigger 1"]', 'obsOut');
    await page.fill('#triggers input[list="obs-scenes"]', 'Cam');
    await page.waitForTimeout(400);
    await page.selectOption('select[aria-label="Overlay of trigger 1"]', 'OV1');
    await page.fill('input[aria-label="Name of control app 1a2b3c"]', 'Placar A');  // another section, same 500 ms
    await page.waitForTimeout(900);
    const lists = await unnamed();
    await page.close();
    assert.ok(!url.includes('tok123'), 'the token leaves the address bar');
    assert.deepStrictEqual(lists, []);
    assert.ok(hiddenClear, '"Remove the saved password" only when one is saved');
    assert.ok(shownOnFocus && hiddenOnEsc && described, 'help on focus, Esc dismisses, aria-describedby');
    assert.deepStrictEqual(posts[0], {type: 'application/json',
      obs: {enabled: true, host: '127.0.0.1', port: '4456', password: 'segredo', clearPassword: false}});
    assert.deepStrictEqual(after, {password: '', placeholder: 'Saved (type to replace)', clearShown: true});
    const triggers = posts.filter(p => p.triggers).pop()?.triggers;
    assert.deepStrictEqual(triggers, [{on: true, event: 'obsOut', scene: 'Cam', function: 'show', app: '1a2b3c', overlay: 'OV1', delay: 0}],
      'a change in another section within the save delay does not drop the triggers');
    assert.deepStrictEqual(posts.filter(p => p.apps).pop()?.apps, [{id: '1a2b3c', name: 'Placar A'}]);
    assert.deepStrictEqual(errors, []);
  });
});
