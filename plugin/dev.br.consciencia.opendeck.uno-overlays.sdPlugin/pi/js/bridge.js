/* OpenAction property inspector transport. Settings stay in OpenDeck profiles. */
'use strict';

// The original fixed release compared recursively sorted settings. Rust may
// serialize object keys in a different order from the JavaScript editor.
function stableStringify(value) {
  const sort = v => {
    if (Array.isArray(v)) return v.map(sort);
    if (v && typeof v === 'object') {
      const out = {};
      Object.keys(v).sort().forEach(k => { out[k] = sort(v[k]); });
      return out;
    }
    return v;
  };
  return JSON.stringify(sort(value));
}

class OpenDeckBridge {
  constructor(onSettings, onError) {
    this.onSettings = onSettings;
    this.onError = onError;
    this.pending = new Map();
    this.echoes = new Set();
    this.serial = 0;
  }

  connect(port, uuid, registerEvent, info, actionInfo) {
    const ai = typeof actionInfo === 'string' ? JSON.parse(actionInfo) : actionInfo;
    this.context = ai.context || uuid;
    this.action = ai.action;
    this.ws = new WebSocket(`ws://127.0.0.1:${port}`);
    this.ws.onopen = async () => {
      this.ws.send(JSON.stringify({event: registerEvent, uuid}));
      // The plugin knows the language (settings page, else OpenDeck's settings.json): ask before drawing.
      try {
        const answer = await Promise.race([this.request({type: 'i18n.get'}),
          new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 3000))]);
        setLanguage(answer?.language || 'en');
      } catch { setLanguage(LANG.code); }  // an old or busy plugin: draw in the current language
      const initial = ai.payload?.settings || {};
      this.echoes.add(stableStringify(initial));
      this.onSettings(initial, this.action);
      this.send('getSettings');
      this.send('getGlobalSettings');
    };
    this.ws.onmessage = e => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { return; }
      // didReceiveGlobalSettings carries no context (OpenDeck outbound/settings.rs).
      if (msg.event === 'didReceiveGlobalSettings') { this.onGlobal?.(msg.payload?.settings || {}); return; }
      if (msg.context !== this.context) return;
      if (msg.event === 'didReceiveSettings') {
        const s = msg.payload?.settings || {};
        if (this.echoes.has(stableStringify(s))) return;
        this.onSettings(s, this.action);
      }
      if (msg.event === 'sendToPropertyInspector') {
        const p = msg.payload || {};
        if (p.type === 'uno.changed') this.onChange?.();
        if (p.type === 'uno.waiting') this.onWaiting?.(p.requestId);
        if (p.type === 'error') this.onError(p.error);
        const pending = this.pending.get(p.requestId);
        if (p.type !== 'uno.result' || !pending) return;
        clearTimeout(pending.timer);
        this.pending.delete(p.requestId);
        if (p.error) pending.reject(new Error(p.error));
        else pending.resolve(p.data);
      }
    };
    this.ws.onclose = () => {
      for (const p of this.pending.values()) {
        clearTimeout(p.timer);
        p.reject(new Error(t('OpenDeck disconnected. Reopen this inspector.')));
      }
      this.pending.clear();
      this.onError(t('OpenDeck disconnected. Reopen this inspector.'));
    };
    this.ws.onerror = () => this.onError(t('Unable to connect to OpenDeck.'));
  }

  send(event, payload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error(t('OpenDeck is not connected.'));
    const msg = {event, context: this.context};
    if (payload !== undefined) msg.payload = payload;
    this.ws.send(JSON.stringify(msg));
  }

  save(settings) {
    // Retain recent snapshots: older echoes must not replace newer typing.
    this.echoes.add(stableStringify(settings));
    if (this.echoes.size > 100) this.echoes.delete(this.echoes.values().next().value);
    this.send('setSettings', settings);
  }

  read(token, command, id) {
    return this.request({type: 'uno.read', token, command, id});
  }

  request(payload) {
    const requestId = `uno-${++this.serial}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(requestId);
        reject(new Error(t('UNO request timed out. Click Reload to try again.')));
      }, 90000);
      this.pending.set(requestId, {resolve, reject, timer});
      try { this.send('sendToPlugin', {...payload, requestId}); }
      catch (error) { clearTimeout(timer); this.pending.delete(requestId); reject(error); }
    });
  }
}

class UnoApi {
  constructor(token, bridge) { this.token = token; this.bridge = bridge; }
  getOverlays() { return this.bridge.read(this.token, 'GetOverlays'); }
  getOverlayModel(id) { return this.bridge.read(this.token, 'GetOverlayModel', id); }
  getOverlayContent(id) { return this.bridge.read(this.token, 'GetOverlayContent', id); }
  getSlots(id) { return this.bridge.read(this.token, 'GetSlots', id); }
}
