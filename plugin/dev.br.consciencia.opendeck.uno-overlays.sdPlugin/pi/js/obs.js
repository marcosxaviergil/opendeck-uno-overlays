/* OBS Studio (obs-websocket 5): scene and browser source lists. The connection and the triggers are shared by
   every key and set on the plugin's settings page (OpenDeck: Plugins → UNO Overlays → Settings). */
'use strict';

Object.assign(Inspector.prototype, {
  buildObsScene(root) {
    this.select(root, 'sceneName', t('OBS scene'), [['', t('Connect to OBS…')]]);
    const overlay = this.select(root, 'overlayId', t('Then show overlay (optional)'), [['', t('None')]]);
    const slot = this.select(root, 'slotNumber', t('Server Slot'), [[0, t('Live / current slot')]]);

    overlay.addEventListener('change', () => {
      this.settings.slotNumber = 0;
      delete this.settings.serverSlotId;
      this.serverSlots.delete('');
      this.save();
      this.loadObsSceneSlots();
    });

    slot.addEventListener('change', () => {
      const number = Number(slot.value);
      const item = this.serverSlots.get('')?.data?.[number - 1];
      this.settings.serverSlotId = item?.id || '';
      this.save();
    });

    this.timer(root, 'autoClose', t('Auto Close'));
    this.obsNote(root);
    this.loadObsSceneSlots();
  },

  async loadObsSceneSlots() {
    const id = this.settings.overlayId;
    const token = this.settings.token;
    const select = el('slotNumber');

    if (!select) return;

    if (!id || !token) {
      this.serverSlots.delete('');
      select.replaceChildren(new Option(t('Live / current slot'), '0'));
      select.value = '0';
      return;
    }

    try {
      const slots = await new UnoApi(token, this.bridge).getSlots(id);

      if (id !== this.settings.overlayId || token !== this.settings.token) return;

      this.serverSlots.set('', slots);
      this.slots('');
    } catch (e) {
      if (id === this.settings.overlayId && token === this.settings.token) {
        this.status(e.message, true);
      }
    }
  },

  buildObsRefresh(root) {
    this.select(root, 'refreshMode', t('Refresh'), [['', t('The browser sources listed below')],
      ['scene', t('Every browser source of a scene')]]).addEventListener('change', () => this.refreshVisibility());
    this.select(root, 'refreshScene', t('Scene'), [['', t('Connect to OBS…')]]);
    this.select(root, 'inputName', t('Browser source'), [['', t('Connect to OBS…')]]);
    const box = this.group(root, 'obsrefresh', t('More browser sources'), 'inputNames');
    const list = document.createElement('div'); list.id = 'sources';
    const add = document.createElement('button'); add.type = 'button'; add.append(icon('add'), t('Add source'));
    add.addEventListener('click', () => { (this.settings.inputNames ||= []).push(''); this.save(); this.renderSources(); });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(add);
    box.append(list, actions);
    this.renderSources();
    this.refreshVisibility();
    this.obsNote(root);
  },

  refreshVisibility() {
    const scene = this.settings.refreshMode === 'scene';
    el('refreshScene').closest('.section').classList.toggle('hidden', !scene);
    el('inputName').closest('.section').classList.toggle('hidden', scene);
    el('sources').closest('fieldset').classList.toggle('hidden', scene);
  },

  renderSources() {
    const list = el('sources');
    if (!list) return;
    const names = this.settings.inputNames ||= [];
    const browsers = (this.obsLists?.browsers || []).map(name => [name, name]);
    list.replaceChildren(...names.map((value, i) => {
      const row = document.createElement('div'); row.className = 'field-row inline-row';
      const select = choose(value && !browsers.some(([v]) => v === value) ? [[value, value], ...browsers] : browsers, t('Browser source…'));
      select.value = value;
      select.addEventListener('change', () => { names[i] = select.value; this.save(); });
      const remove = document.createElement('button'); remove.type = 'button'; remove.append(icon('close'));
      remove.addEventListener('click', () => { names.splice(i, 1); this.save(); this.renderSources(); });
      row.append(select, remove);
      return row;
    }));
  },

  obsNote(parent) {
    parent.append(Object.assign(document.createElement('p'), {className: 'hint', textContent: OBS_WHERE()}));
  },

  async loadObs() {
    if (!OBS_ACTIONS.includes(this.action) || (this.action === 'macro' && !this.global.obsEnabled)) return;
    try {
      const lists = await this.bridge.request({type: 'obs.list'});
      this.obsLists = lists; this.obsScenes = lists.scenes; this.renderSteps(); this.renderSources();
      for (const [id, items] of [['sceneName', lists.scenes], ['refreshScene', lists.scenes], ['inputName', lists.browsers]]) {
        const select = el(id);
        if (!select) continue;
        select.replaceChildren(new Option(t('Select…'), ''), ...items.map(name => new Option(name, name)));
        select.value = this.settings[id] || '';
      }
      this.status(t('OBS connected.'));
    } catch (e) { this.status(e.message, true); }
  }
});