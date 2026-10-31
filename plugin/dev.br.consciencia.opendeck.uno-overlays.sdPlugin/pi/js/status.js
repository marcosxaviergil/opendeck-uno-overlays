/* Status key: connections, today's App API calls, log, connection test and backup. */
'use strict';

Object.assign(Inspector.prototype, {
  statusPanel(root) {
    const box = this.group(root, 'status', t('Connections'), 'connections');
    const items = document.createElement('div'); items.id = 'status-items';
    const test = document.createElement('button'); test.type = 'button'; test.append(icon('status'), t('Test connection'));
    test.addEventListener('click', async () => {
      this.status(t('Testing…'));
      try { this.status((await this.bridge.request({type: 'status.test'})).join(' | ') || t('Nothing to test.')); this.refreshStatus(); }
      catch (e) { this.status(e.message, true); }
    });
    const actions = document.createElement('div'); actions.className = 'slot-actions'; actions.append(test);
    const testHelp = helpText(this.action, 'test');
    if (testHelp) actions.append(helpTip(testHelp, t('Test connection')));
    box.append(items, actions);
    const cap = Object.assign(document.createElement('input'), {id: 'apiCap', type: 'number', min: 0, placeholder: '10000'});
    cap.value = this.global.apiCap ?? '';
    cap.addEventListener('input', () => this.saveGlobal({apiCap: cap.value}));
    this.labelled(root, 'apiCap', t('Daily App API cap (uno free plan: 10000; yellow from 90%, 0 = no warning)'), cap);
    const logBox = this.group(root, 'history', t('Log (newest first, no tokens)'), 'log');
    const log = Object.assign(document.createElement('pre'), {id: 'log', className: 'log', tabIndex: 0}); // scrollable by keyboard
    log.setAttribute('aria-label', t('Log'));
    const clear = document.createElement('button'); clear.type = 'button'; clear.append(icon('delete'), t('Clear log'));
    clear.addEventListener('click', async () => {
      try { await this.bridge.request({type: 'log.clear'}); this.refreshStatus(); } catch (e) { this.status(e.message, true); }
    });
    const logActions = document.createElement('div'); logActions.className = 'slot-actions'; logActions.append(clear);
    logBox.append(log, logActions);
    const backup = this.group(root, 'download', t('Backup of shared settings'), 'backup');
    const path = Object.assign(document.createElement('input'), {id: 'backupPath', type: 'text', placeholder: '~/uno-overlays-backup.json'});
    path.setAttribute('aria-label', t('Backup file path'));
    const secrets = Object.assign(document.createElement('input'), {type: 'checkbox', id: 'backupSecrets'});
    const secretsRow = document.createElement('label'); secretsRow.className = 'inline'; secretsRow.append(secrets, t('Include API tokens and OBS password'));
    const token = Object.assign(document.createElement('input'), {id: 'backupToken', type: 'password', placeholder: t('API token for items without one (import)')});
    const run = (type, glyph, label) => {
      const b = document.createElement('button'); b.type = 'button'; b.append(icon(glyph), label);
      b.addEventListener('click', async () => {
        try {
          const data = await this.bridge.request({type, path: path.value, secrets: secrets.checked, token: token.value.trim()});
          this.status(type === 'backup.export' ? t('Exported {count} items to {path}.', data) : t('Imported {count} items.', data));
          this.refreshStatus();
        } catch (e) { this.status(e.message, true); }
      });
      return b;
    };
    const buttons = document.createElement('div'); buttons.className = 'slot-actions';
    buttons.append(run('backup.export', 'download', t('Export')), run('backup.import', 'upload', t('Import')));
    const hint = document.createElement('p'); hint.className = 'hint';
    hint.textContent = t('Scenes, data sources, polls, goals, triggers, groups, favorites and the settings page options. Scenes and data sources may hold people\'s names (personal data, LGPD): keep the file private and delete it when no longer needed. Import replaces items with the same name.');
    backup.append(path, secretsRow, token, buttons, hint);
    this.refreshStatus();
    this.statusTimer = setInterval(() => this.refreshStatus(), 2000);
  },

  async refreshStatus() {
    if (!el('status-items')) return;
    try {
      const data = await this.bridge.request({type: 'status.get'});
      const color = {good: '#00C800', warning: '#FFFF00', error: '#C80000'};
      el('status-items').replaceChildren(...(data.items.length ? data.items : [{name: t('Nothing configured'), detail: t('Add an API token to a key or enable OBS.')}])
        .map(item => {
          const row = document.createElement('p');
          const dot = Object.assign(document.createElement('span'), {className: 'dot'}); dot.style.background = color[item.level] || '#404040';
          row.append(dot, `${item.name}: ${item.detail}`);
          return row;
        }),
        Object.assign(document.createElement('p'), {className: 'hint', textContent:
          t('{calls} App API calls today (local day; UNO does not document when its day resets)', data)
          + (data.cap ? ' · ' + t('cap {cap}', data) : '') + (data.locked ? ' · ' + t('desk locked') : '')}));
      el('log').textContent = data.log.join('\n');
    } catch (e) { this.status(e.message, true); }
  }
});
