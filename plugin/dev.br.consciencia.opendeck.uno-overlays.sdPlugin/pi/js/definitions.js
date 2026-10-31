/* Shared definitions in the global settings: data sources (vMix), polls and goals (Streamlabs). */
'use strict';

Object.assign(Inspector.prototype, {
  buildDefinition(root) {
    this.defManager(root);
    if (this.action === 'datasource') {
      this.select(root, 'operation', t('Press'), [['next', t('Next row (DataSourceNextRow)')],
        ['prev', t('Previous row (DataSourcePreviousRow)')], ['select', t('Select row (DataSourceSelectRow)')],
        ['autonext', t('Auto Next on / off')]]);
      this.input(root, 'row', t('Row for Select row (1 = first)'), 'number', '1');
      this.select(root, 'channel', t('Visor channel (knob)'), CHANNELS());
    } else if (this.action === 'vote') {
      this.select(root, 'option', t('Votes for option'), [['1', t('Option {n}', {n: 1})]]);
    } else {
      this.select(root, 'operation', t('Press'), [['add', t('Add amount')], ['start', t('Start goal')], ['end', t('End goal')]]);
      this.input(root, 'amount', t('Amount (knob: per tick)'), 'number', '1');
    }
    this.renderDef();
  },

  defManager(root) {
    const [key, kind, label] = DEFS[this.action];
    const box = this.group(root, this.action, t('{name} (shared by every key)', {name: label()}), 'definition');
    const select = document.createElement('select'); select.id = 'def-name';
    select.setAttribute('aria-label', label());
    select.addEventListener('change', () => { this.settings[key] = select.value; this.save(); this.renderDef(); });
    const name = Object.assign(document.createElement('input'), {id: 'def-new', type: 'text', placeholder: t('New name')});
    const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), t('Create'));
    add.addEventListener('click', () => {
      const value = name.value.trim();
      if (!value || this.defs(kind)[value]) return this.status(value ? t('That name exists.') : t('Type a name.'), true);
      this.settings[key] = value; name.value = ''; this.save();
      this.saveDef(kind, value, {token: this.settings.token || ''}); this.renderDef();
    });
    const remove = document.createElement('button'); remove.type = 'button'; remove.id = 'def-delete'; remove.append(icon('delete'), t('Delete'));
    remove.addEventListener('click', () => {
      if (!this.settings[key]) return;
      this.saveDef(kind, this.settings[key], null); this.settings[key] = ''; this.save(); this.renderDef();
    });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(add, remove);
    const body = document.createElement('div'); body.id = 'def-body';
    box.append(select, name, actions, body);
  },

  defs(kind) {
    // Start, end and reached are set by the plugin: always keep its latest values.
    const merged = {...(this.global[kind] || {})};
    for (const [name, d] of Object.entries(this.pendingDefs?.[kind] || {})) {
      if (d === null) { delete merged[name]; continue; }
      const own = Object.fromEntries(['state', 'reached', 'started'].filter(k => k in (merged[name] || {})).map(k => [k, merged[name][k]]));
      merged[name] = {...d, ...own};
    }
    return merged;
  },

  saveDef(kind, name, d) {
    // Global settings are shared by every action: merge the change when it is sent, never replace.
    (this.pendingDefs ||= {})[kind] = {...(this.pendingDefs[kind] || {}), [name]: d};
    clearTimeout(this.defTimer);
    this.defTimer = setTimeout(() => {
      const next = {...this.global};
      for (const [k, items] of Object.entries(this.pendingDefs)) next[k] = this.defs(k);
      this.pendingDefs = {}; this.global = next;
      this.bridge.send('setGlobalSettings', next);
    }, 300);
  },

  renderDef() {
    if (!DEFS[this.action] || !el('def-body')) return;
    const [key, kind] = DEFS[this.action];
    const names = Object.keys(this.defs(kind)).sort();
    el('def-name').replaceChildren(new Option(names.length ? t('Choose…') : t('Create one below'), ''), ...names.map(n => new Option(n, n)));
    el('def-name').value = names.includes(this.settings[key]) ? this.settings[key] : '';
    el('def-delete').disabled = !el('def-name').value;
    const body = el('def-body'); body.replaceChildren();
    const name = el('def-name').value;
    if (!name) return;
    const d = clone(this.defs(kind)[name]);
    const commit = () => {
      d.token = this.settings.token || d.token || ''; this.saveDef(kind, name, d);
      if (kind === 'dataSources') { clearTimeout(this.previewTimer); this.previewTimer = setTimeout(() => this.previewSource(d), 500); }
    };
    const fields = (this.allFields || []).map(f => [f.composite, f.label]);
    const bind = (parent, prop, label, element, redraw = false) => {
      const box = document.createElement('div'); box.className = 'section';
      element.id = 'def-' + prop;
      const row = document.createElement('div'); row.className = 'label-row';
      row.append(Object.assign(document.createElement('label'), {htmlFor: element.id, textContent: label}));
      const help = helpText(this.action, 'def.' + prop);
      if (help) row.append(helpTip(help, label, element));
      element.value = d[prop] ?? '';
      element.addEventListener(element.tagName === 'SELECT' ? 'change' : 'input', () => {
        d[prop] = element.value; commit(); if (redraw) this.renderDef();
      });
      box.append(row, element); parent.append(box);
      return element;
    };
    const list = (prop, addLabel, row) => {
      const items = d[prop] ||= [];
      const box = document.createElement('div');
      items.forEach((item, i) => {
        const line = document.createElement('div'); line.className = 'field-row';
        row(item, line, i);
        const x = document.createElement('button'); x.type = 'button'; x.append(icon('close'));
        x.addEventListener('click', () => { items.splice(i, 1); commit(); this.renderDef(); });
        line.append(x); box.append(line);
      });
      const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), addLabel);
      add.addEventListener('click', () => { items.push({}); commit(); this.renderDef(); });
      box.append(add); body.append(box);
    };
    const cell = (item, prop, element, line) => {
      element.value = item[prop] ?? '';
      element.addEventListener(element.tagName === 'SELECT' ? 'change' : 'input', () => { item[prop] = element.value; commit(); });
      line.append(element);
    };
    if (kind === 'dataSources') {
      bind(body, 'kind', t('Type'), choose([['list', t('Typed list (one row per line)')], ['text', t('Text file (one row per line)')],
        ['csv', t('CSV file')]]), true);
      if ((d.kind || 'list') === 'list') bind(body, 'text', t('Rows'), textBox('area', t('First message\nSecond message')));
      else bind(body, 'path', t('File path on this computer'), textBox('text', '/home/you/ticker.csv'));
      if (d.kind === 'csv') {
        bind(body, 'header', t('Use first row as column names'), choose([['', t('No')], ['true', t('Yes')]]), true);
        bind(body, 'delimiter', t('Separator'), choose([['', t('Comma ,')], [';', t('Semicolon ;')], ['tab', t('Tab')]]), true);
      }
      const preview = document.createElement('p'); preview.className = 'hint'; preview.id = 'def-preview'; body.append(preview);
      const title = document.createElement('p'); title.className = 'label-row'; title.append(t('Mapping: field ← column (Auto = same name, else field order), Row, Format'));
      const mapHelp = helpText(this.action, 'def.map');
      if (mapHelp) title.append(helpTip(mapHelp, t('Mapping')));
      body.append(title);
      const columns = this.previewColumns || [];
      list('map', t('Map a field'), (item, line) => {
        cell(item, 'field', choose(fields, t('Field…')), line);
        cell(item, 'column', choose(columns.map(c => [c, c]), t('Auto')), line);
        cell(item, 'row', textBox('number', t('Selected')), line);
        cell(item, 'format', textBox('text', '{0}'), line);
      });
      bind(body, 'seconds', t('Auto Next: seconds between rows'), textBox('number', '10'));
      bind(body, 'loop', t('Loop'), choose([['', t('Stop at the last row')], ['true', t('Jump to the start after the last row')]]));
      this.previewSource(d);
    } else if (kind === 'polls') {
      const title = document.createElement('p'); title.className = 'label-row'; title.append(t('Options: votes field, percent field (optional)'));
      const optionsHelp = helpText(this.action, 'def.options');
      if (optionsHelp) title.append(helpTip(optionsHelp, t('Options')));
      body.append(title);
      list('options', t('Add option'), (item, line, i) => {
        line.prepend(Object.assign(document.createElement('span'), {textContent: `${i + 1}.`}));
        cell(item, 'votes', choose(fields, t('Votes field…')), line);
        cell(item, 'percent', choose(fields, t('Percent field…')), line);
      });
      bind(body, 'total', t('Total votes field (optional)'), choose(fields, t('None')));
      bind(body, 'format', t('Percent format'), textBox('text', '{0}%'));
      const option = el('option');
      if (option) {
        option.replaceChildren(...(d.options || []).map((o, i) => new Option(t('Option {n}', {n: i + 1}), String(i + 1))));
        option.value = this.settings.option || '1';
      }
    } else {
      const active = d.state === 'active';
      const state = document.createElement('p'); state.className = 'hint';
      state.textContent = active
        ? t('Active since {date}{reached}. An existing goal cannot be edited: End it and start a new one.',
          {date: String(d.started || '').replace('T', ' '), reached: d.reached ? t(' · reached') : ''})
        : d.state === 'ended' ? t('Ended.') : t('Not started.');
      body.append(state);
      for (const [prop, label, type] of [['title', t('Title'), 'text'], ['goal', t('Goal Amount'), 'number'],
        ['start', t('Starting Amount'), 'number'], ['end', t('End After'), 'datetime-local']]) bind(body, prop, label, textBox(type)).disabled = active;
      bind(body, 'titleField', t('Title field'), choose(fields, t('None')));
      bind(body, 'current', t('Current amount field (numbers)'), choose(fields, t('Select…')));
      bind(body, 'goalField', t('Goal amount field'), choose(fields, t('None')));
      bind(body, 'goalFormat', t('Goal format'), textBox('text', '{0}'));
      bind(body, 'percent', t('Percent field'), choose(fields, t('None')));
      bind(body, 'percentFormat', t('Percent format'), textBox('text', '{0}%'));
      bind(body, 'reachedFunction', t('When the goal is reached'), choose(FUNCTIONS()));
      bind(body, 'reachedTarget', t('Overlay'), choose(this.overlays.map(o => [String(o.id), o.name || o.id]), t('Select…')));
      bind(body, 'reachedDelay', t('Delay (ms, max 30000)'), textBox('number', '0'));
    }
    this.enhanceSelects();
  },

  async previewSource(d) {
    const serial = this.previewSerial = (this.previewSerial || 0) + 1;
    try {
      const data = await this.bridge.request({type: 'source.preview', definition: d});
      if (serial !== this.previewSerial || !el('def-preview')) return;
      const changed = stableStringify(data.columns) !== stableStringify(this.previewColumns || []);
      this.previewColumns = data.columns;
      el('def-preview').textContent = t('{count} rows · columns: {columns}', {count: data.count, columns: data.columns.join(', ') || '—'}) +
        (data.rows[0] ? ' · ' + t('row 1: {row}', {row: data.rows[0].join(' | ')}) : '');
      if (changed && !el('def-body').contains(document.activeElement)) this.renderDef();
    } catch (e) { if (el('def-preview')) el('def-preview').textContent = e.message; }
  }
});
