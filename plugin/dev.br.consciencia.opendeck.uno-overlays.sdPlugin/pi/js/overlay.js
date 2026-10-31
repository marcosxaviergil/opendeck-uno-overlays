/* Overlay and Knob Control: overlay, server slots (presets), the dynamic model form and optional behaviour. */
'use strict';

// Outside a secure context crypto.randomUUID is missing: fall back to time + random hex.
const hex4 = () => Math.floor((1 + Math.random()) * 0x10000).toString(16).slice(1);
const newSlotId = () => crypto.randomUUID?.() ?? `${Date.now().toString(16)}-${hex4()}-${hex4()}-${hex4()}-${hex4()}${hex4()}${hex4()}`;

Object.assign(Inspector.prototype, {
  buildToggle(root) {
    this.timer(root, 'autoClose', t('Auto Close'));
    this.select(root, 'pressAgain', t('Press again while Auto Close counts'), [['', t('Hide now')], ['add', t('Add the Auto Close time')]]);
    this.overlayControl(root, '');
    this.presetControls(root);
    this.formContainer(root, '');
    this.overlayOptions(root);
  },

  buildKnob(root) {
    for (const [g, label] of [['ccw', t('Counterclockwise')], ['press', t('Press')], ['cw', t('Clockwise')]]) {
      const box = document.createElement('fieldset');
      const legend = document.createElement('legend'); legend.textContent = label; box.append(legend);
      legend.append(helpTip(helpText(this.action, g), label));
      root.append(box);
      const selector = this.select(box, g + 'Action', t('Action'), [
        ['none', t('None')], ['toggle', t('Toggle Overlay')], ['showAll', t('Show All')], ['hideAll', t('Hide All')],
        ['increment', t('Increment (+)')], ['decrement', t('Decrement (−)')]]);
      this.overlayControl(box, g);
      this.select(box, g + 'FieldComposite', t('Numeric Field'), [['', t('Enter an API token…')]]);
      this.timer(box, g + 'Delay', t('Delay')); this.timer(box, g + 'AutoClose', t('Auto Close'));
      this.tokenList(box, g + 'Tokens', t('More control apps (optional)'));
      this.formContainer(box, g);
      selector.addEventListener('change', () => this.gestureVisibility(g));
      this.gestureVisibility(g);
    }
  },

  overlayControl(root, g) {
    const idKey = this.key(g, 'overlayId');
    const select = this.select(root, idKey, t('Overlay'), [['', t('Enter an API token…')]]);
    const slotSelect = this.select(root, this.key(g, 'slotNumber'), t('Server Slot'), [[0, t('Live / current slot')]]);
    slotSelect.addEventListener('change', async () => {
      const number = Number(slotSelect.value);
      const item = this.serverSlots.get(g)?.data?.[number - 1];
      this.settings[this.key(g, 'serverSlotId')] = item?.id || '';
      this.save();
      if (!g) this.presets();
      await this.refreshContent(g);
    });
    select.addEventListener('change', async () => {
      delete this.settings[this.key(g, 'content')];
      this.settings[this.key(g, 'slotNumber')] = 0;
      delete this.settings[this.key(g, 'serverSlotId')];
      this.serverSlots.delete(g);
      if (!g) this.presets();
      this.forms.get(g)?.container.replaceChildren();
      this.slots(g);
      this.save();
      try { await this.model(g, this.version); }
      catch (e) { this.status(e.message, true); }
    });
  },

  formContainer(root, g) {
    const help = helpText(this.action, 'form');
    if (help && !g) {
      const title = Object.assign(document.createElement('p'), {className: 'label-row', textContent: t('Overlay content')});
      title.append(helpTip(help, t('Overlay content')));
      root.append(title);
    }
    const container = document.createElement('div'); container.id = g + '-fields';
    container.className = 'section'; root.append(container);
    const fb = new FormBuilder(container); fb.prefix = g ? g + '_' : ''; this.forms.set(g, fb);
    const edited = event => {
      if (!fb.fieldMap.size) return;
      try {
        const changed = [...fb.fieldMap].find(([, info]) => info.element === event.target);
        if (!changed) return;
        const values = fb.extractValues();
        const patch = {[changed[0]]: values[changed[0]]};
        const key = `${g}:${changed[0]}`;
        const serial = ++this.editSerial;
        this.pendingFields.set(key, serial);
        const version = this.version;
        this.status(t('Saving to UNO…'));
        this.bridge.request({type: 'uno.edit', token: this.settings.token,
          id: this.settings[this.key(g, 'overlayId')],
          slotNumber: Number(this.settings[this.key(g, 'slotNumber')] || 0),
          slotId: this.settings[this.key(g, 'serverSlotId')] || '', patch
        }).then(() => {
          if (this.pendingFields.get(key) === serial) this.pendingFields.delete(key);
          if (version === this.version && !this.pendingFields.size) this.status(t('Saved to UNO.'));
        }).catch(error => {
          if (this.pendingFields.get(key) === serial) this.pendingFields.delete(key);
          if (version === this.version) this.status(`${error.message} ${t('Edit the field again to retry.')}`, true);
        });
      } catch (e) { this.status(e.message, true); }
    };
    // Save on input, before blur or switching the selected action/preset.
    container.addEventListener('input', edited);
    container.addEventListener('change', edited);
    // On air the plugin waits until the typing stops; moving to another field sends what is waiting now.
    container.addEventListener('focusin', event => {
      if (this.editing && this.editing !== event.target) this.bridge.send('sendToPlugin', {type: 'uno.flush'});
      this.editing = event.target;
    });
    this.bridge.onWaiting = () => { if (this.pendingFields.size) this.status(t('Waiting to send (on air)…')); };
  },

  presetControls(root) {
    this.select(root, 'slotsEnabled', t('Mode'), [['', t('Normal toggle')], ['true', t('Always show (Slots)')]]);
    el('slotsEnabled').value = this.settings.slotsEnabled ? 'true' : '';
    el('slotsEnabled').addEventListener('change', () => {
      this.settings.slotsEnabled = el('slotsEnabled').value === 'true'; this.save();
    });
    const box = document.createElement('fieldset'); root.append(box);
    const name = document.createElement('input'); name.id = 'slotName'; name.type = 'text';
    this.labelled(box, 'slotName', t('Server Slot Name'), name);
    const buttons = document.createElement('div'); buttons.className = 'slot-actions';
    for (const [id, title, operation, glyph] of [['add', t('Add'), 'add', 'add'], ['rename', t('Rename'), 'rename', 'dialvalue'],
      ['delete', t('Remove'), 'remove', 'delete']]) {
      const button = document.createElement('button'); button.type = 'button'; button.id = 'slot-' + id;
      button.replaceChildren(icon(glyph), title);
      button.addEventListener('click', () => this.changeSlot(operation)); buttons.append(button);
    }
    box.append(buttons);
    // Keep old local presets as recoverable drafts; never overwrite server data
    // merely because an inspector opened after upgrading from 1.0.0.
    if ((this.settings.slots || []).length || Object.keys(this.settings.content || {}).length) {
      const importButton = document.createElement('button'); importButton.type = 'button'; importButton.id = 'import-legacy';
      importButton.replaceChildren(icon('upload'), t('Import 1.0 drafts as server slots'));
      importButton.addEventListener('click', () => this.importLegacy()); box.append(importButton);
    }
    this.presets();
  },

  selectedPreset(g = '') {
    const slots = this.serverSlots.get(g)?.data || [];
    const id = this.settings[this.key(g, 'serverSlotId')];
    if (id) return slots.find(slot => slot.id === id) || null;
    return slots[Number(this.settings[this.key(g, 'slotNumber')] || 0) - 1] || null;
  },

  presets() {
    if (!el('slotName')) return;
    const slot = this.selectedPreset();
    el('slotName').value = slot?.name || '';
    el('slot-rename').disabled = !slot;
    el('slot-delete').disabled = !slot;
  },

  async changeSlot(operation, draft = null) {
    const id = this.settings.overlayId, token = this.settings.token, version = this.version;
    if (!id || !token) return;
    const slotId = operation === 'add' ? newSlotId() : this.selectedPreset()?.id;
    const content = draft?.payload || this.forms.get('')?.extractValues() || {};
    this.status(t('Saving server slot…'));
    try {
      const result = await this.bridge.request({type: 'uno.slot', token, id, operation, slotId,
        name: draft?.name || el('slotName').value || t('New Slot'), content});
      if (version !== this.version || id !== this.settings.overlayId || token !== this.settings.token) return;
      this.serverSlots.set('', result);
      this.settings.serverSlotId = operation === 'remove' ? '' : slotId;
      this.settings.slotNumber = operation === 'remove' ? 0 : result.data.findIndex(slot => slot.id === slotId) + 1;
      this.slots(''); this.presets(); this.save();
      await this.refreshContent('');
      this.status(t('Server slot saved to UNO.'));
      return true;
    } catch (error) { this.status(error.message, true); return false; }
  },

  async importLegacy() {
    const drafts = [...(this.settings.slots || [])];
    if (Object.keys(this.settings.content || {}).length) drafts.unshift({name: t('1.0 saved content'), payload: this.settings.content});
    for (const draft of drafts) if (!await this.changeSlot('add', draft)) return;
    delete this.settings.slots; delete this.settings.content; delete this.settings.selectedSlotId;
    this.save(); el('import-legacy')?.remove();
  },

  slots(g) {
    const select = el(this.key(g, 'slotNumber'));
    const slots = this.serverSlots.get(g)?.data;
    if (slots) {
      select.replaceChildren(new Option(t('Live / current slot'), '0'));
      slots.forEach((slot, index) => select.add(new Option(slot.name || t('Slot {n}', {n: index + 1}), String(index + 1))));
      const id = this.settings[this.key(g, 'serverSlotId')];
      const index = id ? slots.findIndex(slot => slot.id === id) : Number(this.settings[this.key(g, 'slotNumber')] || 0) - 1;
      select.value = String(index + 1);
      if (id && index < 0) {
        select.add(new Option(t('Selected slot was removed — select another'), '-1')); select.value = '-1';
      }
    } else {
      const overlay = this.overlays.find(o => String(o.id) === this.settings[this.key(g, 'overlayId')]);
      PIData.populateSlotSelect(select, overlay, this.settings[this.key(g, 'slotNumber')]);
    }
  },

  async refreshContent(onlyGesture) {
    const version = this.version, token = this.settings.token;
    if (!this.api) return;
    const gestures = typeof onlyGesture === 'string' ? [onlyGesture] : [...this.forms.keys()];
    for (const g of gestures) {
      const id = this.settings[this.key(g, 'overlayId')], fb = this.forms.get(g);
      if (!id || !fb?.model) continue;
      try {
        const [remote, slots] = await Promise.all([this.api.getOverlayContent(id), this.api.getSlots(id)]);
        if (version !== this.version || token !== this.settings.token || id !== this.settings[this.key(g, 'overlayId')]) continue;
        this.serverSlots.set(g, slots); this.slots(g);
        const source = this.selectedPreset(g)?.payload || remote;
        const safe = {};
        for (const [key, value] of Object.entries(source)) {
          if (!this.pendingFields.has(`${g}:${key}`) && fb.fieldMap.get(key)?.element !== document.activeElement) safe[key] = value;
        }
        fb.loadValues(safe);
        if (!g && document.activeElement !== el('slotName')) this.presets();
      } catch (error) { this.status(error.message, true); }
    }
  },

  gestureVisibility(g) {
    const action = this.settings[g + 'Action'] || 'none';
    const numeric = ['increment', 'decrement'].includes(action);
    for (const [key, shown] of [['OverlayId', action === 'toggle'], ['SlotNumber', action === 'toggle'],
      ['FieldComposite', numeric], ['Delay', numeric], ['AutoClose', numeric || action === 'toggle']]) {
      el(g + key).closest('.section').classList.toggle('hidden', !shown);
    }
    el(g + 'Tokens-list').closest('fieldset').classList.toggle('hidden', !['showAll', 'hideAll'].includes(action));
    el(g + '-fields').classList.toggle('hidden', action !== 'toggle');
    this.slots(g);
  },

  async model(g, version) {
    const modelVersion = (this.modelVersions.get(g) || 0) + 1;
    this.modelVersions.set(g, modelVersion);
    const id = this.settings[this.key(g, 'overlayId')];
    const fb = this.forms.get(g);
    if (!id || !this.api || !fb) return;
    const [model, remote, slots] = await Promise.all([this.api.getOverlayModel(id), this.api.getOverlayContent(id), this.api.getSlots(id)]);
    if (version !== this.version || modelVersion !== this.modelVersions.get(g) || id !== this.settings[this.key(g, 'overlayId')]) return;
    fb.buildFromModel(model);
    fb.loadValues(remote);
    this.serverSlots.set(g, slots); this.slots(g);
    const selected = this.selectedPreset(g);
    if (selected) {
      this.settings[this.key(g, 'serverSlotId')] = selected.id;
      fb.loadValues(selected.payload || {});
      this.save();
    }
    if (!g) this.presets();
  },

  overlayOptions(root) {
    // Optional behaviour for this overlay; empty values keep the previous behaviour.
    const group = this.group(root, 'toggle', t('Exclusive group (optional)'), 'group');
    const name = this.input(group, 'group', t('Group name: showing this overlay hides the others of the same group'));
    name.setAttribute('list', 'group-names');
    const names = document.createElement('datalist'); names.id = 'group-names';
    names.append(...Object.keys(this.global.groups || {}).map(v => new Option(v))); group.append(names);
    const live = this.group(root, 'dialvalue', t('Edits while on air (optional)'), 'liveEdits');
    this.input(live, 'liveEditDelay', t('Wait after the last change (ms, empty = settings page)'), 'number', '');
    const where = this.group(root, 'link', t('Triggers and chains'), 'triggers');
    where.append(Object.assign(document.createElement('p'), {className: 'hint', textContent: GLOBAL_WHERE()}));
    this.input(where, 'obsOnlyScenes', t('Key shows only while OBS program scene is (comma-separated, optional)'));
  }
});
