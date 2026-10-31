/* Controls of the simpler actions: numbers, slots, knobs, clock, scoreboard tools, scene, visor, desk lock. */
'use strict';

Object.assign(Inspector.prototype, {
  buildMultiplier(root) {
    this.select(root, 'multiplier', t('Multiplier'), Array.from({length: 50}, (_, i) => [i + 1, `× ${i + 1}`]));
  },

  buildAll(root) {
    this.tokenList(root, 'tokens', t('More control apps (optional)'));
  },

  // Extra control apps of Show All / Hide All (the API Token above is the first): one password field per row.
  tokenList(root, key, title) {
    const box = this.group(root, 'add', title, this.helpKey(key));
    const list = document.createElement('div'); list.id = key + '-list';
    const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), t('Add token'));
    add.addEventListener('click', () => { (this.settings[key] ||= []).push(''); this.save(); this.renderTokens(key); });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(add);
    box.append(list, actions);
    this.renderTokens(key);
  },

  renderTokens(key) {
    const list = el(key + '-list');
    if (!list) return;
    const tokens = this.settings[key] ||= [];
    list.replaceChildren(...tokens.map((value, i) => {
      const row = document.createElement('div'); row.className = 'field-row inline-row';
      const input = Object.assign(textBox('password', t('Control API token')), {value, autocomplete: 'off', spellcheck: false});
      input.setAttribute('aria-label', t('Control app {n}: API token', {n: i + 2}));
      input.addEventListener('input', () => { tokens[i] = input.value.trim(); this.save(); });
      const remove = document.createElement('button'); remove.type = 'button'; remove.append(icon('close'));
      remove.addEventListener('click', () => { tokens.splice(i, 1); this.save(); this.renderTokens(key); });
      row.append(input, remove);
      return row;
    }));
  },

  buildNumeric(root) {
    const numeric = this.action === 'numericfields';
    if (numeric) {
      this.timer(root, 'delay', t('Delay')); this.timer(root, 'autoClose', t('Auto Close'));
      this.select(root, 'operation', t('Operation'), [['increment', t('Increment (+)')], ['decrement', t('Decrement (−)')]]);
    }
    const field = this.select(root, 'fieldComposite', t('Numeric Field'), [['', t('Enter an API token…')]]);
    if (!numeric) return;
    field.addEventListener('change', () => {
      const [overlayId, ...rest] = field.value.split('::');
      this.settings.overlayId = rest.length ? overlayId : '';
      this.settings.fieldId = rest.join('::');
      this.save();
    });
    // Optional scoreboard settings; empty keeps the previous behaviour.
    const box = this.group(root, 'numericfields', t('Score options (optional)'), 'scoreOptions');
    this.input(box, 'step', t('Fixed step (e.g. 2 or 3; empty = global multiplier)'), 'number');
    this.input(box, 'min', t('Minimum'), 'number'); this.input(box, 'max', t('Maximum'), 'number');
    this.select(box, 'modelLimits', t('Overlay model min/max'), [['', t('Ignore')], ['true', t('Apply (like the official client)')]]);
    this.select(box, 'pointOverlayId', t('After a point, show overlay'), [['', t('None')]]);
    this.timer(box, 'pointSeconds', t('for'));
  },

  buildSlots(root) {
    this.timer(root, 'autoClose', t('Auto Close'));
    this.select(root, 'overlayId', t('Overlay'), [['', t('Enter an API token…')]]);
    if (this.action !== 'slotwheel') return;
    // Optional and off by default: the wheel keeps "choose, then press" unless the carousel is on.
    this.select(root, 'carousel', t('Turning'), [['', t('Chooses a slot; press takes it')],
      ['true', t('Takes the next or previous slot on air (carousel); press shows or hides')]]);
    this.select(root, 'channel', t('Visor channel'), CHANNELS());
    this.select(root, 'shiftOverlayId', t('While Shift is held (optional)'), [['', t('Same overlay')]]);
  },

  buildReveal(root) {
    this.fieldSelect(root, 'fieldComposite', t('Field that shows the answer'));
    this.input(root, 'shownValue', t('Value when revealed'), 'text', 'true');
    this.input(root, 'hiddenValue', t('Value when hidden'), 'text', 'false');
    const box = this.group(root, 'reveal', t('Highlight the correct answer (optional)'), 'highlight');
    this.fieldSelect(box, 'copyFrom', t('Field with the correct answer'), t('None'));
    this.fieldSelect(box, 'copyTo', t('Field that receives it while revealed'), t('None'));
  },

  buildFieldKnob(root) {
    this.select(root, 'fieldComposite', this.action === 'timer' ? t('Timer Field') : t('Numeric Field'), [['', t('Enter an API token…')]]);
    if (this.action === 'timer') {
      this.select(root, 'operation', t('Operation'), TIMER_OPERATIONS());
      return;
    }
    this.select(root, 'channel', t('Visor channel'), CHANNELS());
    this.select(root, 'shiftFieldComposite', t('While Shift is held (optional)'), [['', t('Same field')]]);
  },

  buildClock(root) {
    this.fieldSelect(root, 'fieldComposite', t('Text field'));
    this.select(root, 'mode', t('Appearance'), [['countdown', t('Countdown')], ['countup', t('Count up')],
      ['timeofday', t('Time of day')], ['until', t('Until finish time')]]);
    this.input(root, 'duration', t('Duration (hh:mm:ss)'), 'text', '05:00');
    this.input(root, 'until', t('Finish time (HH:MM or HH:MM:SS)'), 'text', '19:30');
    this.select(root, 'format', t('Format'), [['mm:ss', t('230:59 (mmm:ss) · clock 19:30')],
      ['hh:mm:ss', t('41:30:59 (hhh:mm:ss) · clock 19:30:05')], ['sss', t('92 (seconds only)')]]);
    this.select(root, 'operation', t('Press'), [['pause', t('Pause / Resume (PauseCountdown)')], ['start', t('Start (StartCountdown)')],
      ['suspend', t('Pause only (SuspendCountdown)')], ['stop', t('Stop and reset (StopCountdown)')],
      ['set', t('Set duration (SetCountdown)')], ['change', t('Change time (ChangeCountdown)')],
      ['adjust', t('Add/subtract seconds (AdjustCountdown)')]]);
    this.input(root, 'value', t('Value for Set / Change (hh:mm:ss) or Adjust (± seconds)'));
    const wrap = this.group(root, 'clock', t('Wrap-up and end (optional)'), 'wrapUp');
    this.input(wrap, 'yellowAt', t('Yellow at (time left, e.g. 1:00)')); this.input(wrap, 'redAt', t('Red at (time left, e.g. 0:30)'));
    this.select(wrap, 'overtime', t('At 0:00'), [['', t('Continue counting past 0:00')], ['stop', t('Stop counting at 0:00')]]);
    this.select(wrap, 'overtimeSign', t('Overtime shows'), [['', t('Negative (-0:01)')], ['+', t('Positive (+0:01)')]]);
    this.select(wrap, 'flash', t('Flash at 0:00'), [['', t('No')], ['1', '1×'], ['2', '2×'], ['3', '3×'], ['inf', t('Until stopped (∞)')]]);
    this.select(wrap, 'flashField', t('Flash in the overlay too'), [['', t('No, only the key')], ['true', t('Yes')]]);
    this.select(wrap, 'countdownFunction', t('When it completes'), FUNCTIONS());
    this.select(wrap, 'countdownTarget', t('Overlay'), [['', t('The clock overlay')]]);
    this.input(wrap, 'countdownDelay', t('Delay (ms, max 30000)'), 'number', '0');
    this.select(wrap, 'pauseOffAir', t('While the overlay is off air'), [['', t('Keep running')], ['true', t('Pause, resume on air')]]);
    this.select(root, 'channel', t('Visor channel (knob)'), CHANNELS());
    this.input(root, 'knobStep', t('Knob step (seconds per tick)'), 'number', '10');
  },

  buildUndo(root) {
    this.fieldSelect(root, 'fieldComposite', t('Only this field (optional)'), t('Any field'));
  },

  buildCycle(root) {
    this.fieldSelect(root, 'fieldComposite', t('Field'));
    this.textarea(root, 'values', t('Values, one per line'), '1º tempo');
    this.fieldSelect(root, 'resetClock', t('Also stop and reset the clock of (optional)'), t('None'));
  },

  buildReset(root) {
    const fields = this.fieldSelect(root, 'fields', t('Fields to reset (Ctrl+click)'));
    fields.multiple = true; fields.size = 6;
    fields.addEventListener('change', () => { this.settings.fields = [...fields.selectedOptions].map(o => o.value); this.save(); });
  },

  buildSwap(root) {
    const box = this.group(root, 'swap', t('Pairs'), 'pairs');
    const list = document.createElement('div'); list.id = 'pairs';
    const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), t('Add pair'));
    add.addEventListener('click', () => { (this.settings.pairs ||= []).push({a: '', b: ''}); this.save(); this.renderPairs(); });
    box.append(list, add);
    this.renderPairs();
  },

  buildTemplate(root) {
    this.fieldSelect(root, 'fieldComposite', t('Field that receives the text'));
    this.textarea(root, 'text', t('Text: {Overlay::Field} is replaced by the field value'), '{OV::Name} – {OV::Role}');
    const insert = document.createElement('select'); insert.id = 'insert'; insert.dataset.fields = 'insert';
    insert.add(new Option(t('Insert a field…'), ''));
    insert.addEventListener('change', () => {
      if (!insert.value) return;
      this.settings.text = (this.settings.text || '') + `{${insert.value}}`;
      el('text').value = this.settings.text; insert.value = ''; this.save();
    });
    this.labelled(root, 'insert', t('Insert a field into the text'), insert);
  },

  buildScene(root) {
    const name = this.input(root, 'name', t('Scene name'));
    name.setAttribute('list', 'scene-list');
    const list = document.createElement('datalist'); list.id = 'scene-list';
    list.append(...Object.keys(this.global.scenes || {}).map(v => new Option(v))); root.append(list);
    this.select(root, 'operation', t('Press to'), [['recall', t('Recall')], ['store', t('Store (overwrite)')]]);
    const safe = this.select(root, 'safe', t('Recall safe: overlays left unchanged (Ctrl+click)'), []);
    safe.multiple = true; safe.size = 5;
    safe.addEventListener('change', () => { this.settings.safe = [...safe.selectedOptions].map(o => o.value); this.save(); });
    // A stored scene keeps overlay content, which may include people's names: it can be deleted here.
    const remove = document.createElement('button'); remove.type = 'button'; remove.append(icon('delete'), t('Delete stored scene'));
    remove.addEventListener('click', async () => {
      try {
        await this.bridge.request({type: 'scene.delete', name: el('name').value.trim()});
        this.status(t('Scene deleted.'));
      } catch (e) { this.status(e.message, true); }
    });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(remove);
    const help = helpText(this.action, 'delete');
    if (help) actions.append(helpTip(help, t('Delete stored scene')));
    root.append(actions);
  },

  buildVisor(root) {
    this.select(root, 'channel', t('Channel'), CHANNELS());
    root.append(Object.assign(document.createElement('p'), {className: 'hint',
      textContent: t('Limitation: the Visor and its knob work only while both are on screen (the knob keeps the choice).')}));
  },

  buildLockDesk(root) {
    // A global setting (every Lock Desk key shares it), so it is not saved in this key's settings.
    const after = Object.assign(document.createElement('input'), {id: 'lockAfter', type: 'number', min: 0, placeholder: '0',
      autocomplete: 'off', value: this.global.lockAfter || ''});
    after.addEventListener('input', () => this.saveGlobal({lockAfter: after.value}));
    this.labelled(root, 'lockAfter', t('Lock after N seconds without use (0 = off; Companion Pin Timeout)'), after);
  },

  buildSafety(root) {
    // Optional for every key: the first press arms it (blinking), a second press in time runs it.
    const box = this.group(root, 'lockdesk', t('Safety (optional)'), 'safety');
    this.select(box, 'confirmSeconds', t('Confirm with a second press'), [['', t('Off: one press runs')],
      ...[2, 3, 5, 10].map(n => [String(n), t('Second press within {n} s (the key blinks)', {n})])]);
  }
});
