/* List editors: Macro steps (Companion Sequential + Wait) and Swap Sides pairs. */
'use strict';

Object.assign(Inspector.prototype, {
  macroEditor(root) {
    const box = this.group(root, 'macro', t('Steps (in order; Wait delays the rest)'), 'steps');
    const list = document.createElement('div'); list.id = 'steps';
    const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), t('Add step'));
    add.addEventListener('click', () => { (this.settings.steps ||= []).push({type: 'show'}); this.save(); this.renderSteps(); });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(add);
    box.append(list, actions);
    for (const [id, source] of [['scene-names', () => Object.keys(this.global.scenes || {})], ['obs-scenes', () => this.obsScenes || []]]) {
      const data = document.createElement('datalist'); data.id = id; box.append(data);
      this.lists = {...this.lists, [id]: source};
    }
    this.renderSteps();
  },

  renderSteps() {
    const list = el('steps');
    if (!list) return;
    const steps = this.settings.steps ||= [];
    for (const [id, source] of Object.entries(this.lists || {})) el(id)?.replaceChildren(...source().map(v => new Option(v)));
    const commit = () => this.save();
    list.replaceChildren(...steps.map((step, i) => {
      const row = document.createElement('div'); row.className = 'field-row';
      const type = document.createElement('select');
      for (const [value, text] of STEPS()) type.add(new Option(`${i + 1}. ${text}`, value));
      type.value = step.type;
      type.addEventListener('change', () => { steps[i] = {type: type.value}; commit(); this.renderSteps(); });
      row.append(type);
      const field = (key, element) => {
        element.value = step[key] ?? '';
        element.addEventListener('input', () => { step[key] = element.value; commit(); });
        element.addEventListener('change', () => { step[key] = element.value; commit(); });
        row.append(element);
      };
      if (['show', 'hide', 'toggle', 'takeslot', 'nextslot', 'prevslot'].includes(step.type))
        field('overlayId', choose(this.overlays.map(o => [o.id, o.name || o.id]), t('Overlay…')));
      if (step.type === 'takeslot') field('slot', textBox('number', t('Slot number (1 = first)')));
      if (['showall', 'hideall'].includes(step.type)) {
        const more = Object.assign(textBox('password', t('More control app tokens, comma-separated (optional)')),
          {autocomplete: 'off', value: (step.tokens || []).join(',')});
        more.addEventListener('input', () => {
          step.tokens = more.value.split(',').map(v => v.trim()).filter(Boolean); commit();
        });
        row.append(more);
      }
      if (step.type === 'setfield' || step.type === 'timer')
        field('fieldComposite', choose((this.allFields || []).filter(f => (f.type === 'timecontrol') === (step.type === 'timer'))
          .map(f => [f.composite, f.label]), t('Field…')));
      if (step.type === 'setfield') field('value', textBox('text', t('Value')));
      if (step.type === 'timer') field('operation', choose(TIMER_OPERATIONS(), t('Operation…')));
      if (step.type === 'obsscene') { const input = textBox('text', t('OBS scene name')); input.setAttribute('list', 'obs-scenes'); field('sceneName', input); }
      if (step.type === 'snapshot') { const input = textBox('text', t('Scene name')); input.setAttribute('list', 'scene-names'); field('name', input); }
      if (step.type === 'wait') field('ms', textBox('number', t('Milliseconds')));
      const buttons = document.createElement('div'); buttons.className = 'slot-actions';
      for (const [glyph, move] of [['up', -1], ['down', 1], ['close', 0]]) {
        const b = document.createElement('button'); b.type = 'button'; b.append(icon(glyph));
        b.addEventListener('click', () => {
          if (move) { const j = i + move; if (j < 0 || j >= steps.length) return; [steps[i], steps[j]] = [steps[j], steps[i]]; }
          else steps.splice(i, 1);
          commit(); this.renderSteps();
        });
        buttons.append(b);
      }
      row.append(buttons);
      return row;
    }));
    this.enhanceSelects();
  },

  renderPairs() {
    const list = el('pairs');
    if (!list) return;
    const pairs = this.settings.pairs ||= [];
    const fields = (this.allFields || []).map(f => [f.composite, f.label]);
    list.replaceChildren(...pairs.map((pair, i) => {
      const row = document.createElement('div'); row.className = 'field-row';
      for (const side of ['a', 'b']) {
        const select = choose(fields, side === 'a' ? t('Field A…') : t('Field B…'));
        select.value = pair[side] || '';
        select.addEventListener('change', () => { pair[side] = select.value; this.save(); });
        row.append(select);
      }
      const remove = document.createElement('button'); remove.type = 'button'; remove.append(icon('close'));
      remove.addEventListener('click', () => { pairs.splice(i, 1); this.save(); this.renderPairs(); });
      row.append(remove);
      return row;
    }));
    this.enhanceSelects();
  }
});
