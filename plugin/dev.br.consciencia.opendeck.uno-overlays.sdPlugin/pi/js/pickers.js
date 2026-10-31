/* Search and favorite overlays in every overlay or field list. */
'use strict';

Object.assign(Inspector.prototype, {
  enhanceSelects() {
    const ids = new Set(this.overlays.map(o => String(o.id)));
    const overlayOf = value => ids.has(value) ? value : value.includes('::') && ids.has(value.split('::')[0]) ? value.split('::')[0] : '';
    const plain = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();  // ignore accents
    const favorites = new Set(this.global.favorites || []);
    for (const select of document.querySelectorAll('#controls select')) {
      if (select.multiple) continue;
      const current = [...select.options].map(o => o.value).join('\n');
      if (select.pickStamp !== current) select.pickAll = [...select.options].map(o => [o.value, o.text.replace(/^★ /, '')]);
      const all = select.pickAll;
      if (all.filter(([v]) => overlayOf(v)).length < 2) continue;
      let pick = select.previousElementSibling;
      if (!pick?.classList.contains('pick')) {
        pick = document.createElement('div'); pick.className = 'pick';
        const search = Object.assign(document.createElement('input'), {type: 'search', placeholder: t('Search…'), autocomplete: 'off'});
        const star = document.createElement('button'); star.type = 'button'; star.title = t('Favorite overlay'); star.append(icon('star'));
        search.addEventListener('input', () => this.enhanceSelects());
        star.addEventListener('click', () => {
          const overlay = overlayOf(select.value);
          if (!overlay) return;
          const list = new Set(this.global.favorites || []);
          list.has(overlay) ? list.delete(overlay) : list.add(overlay);
          this.saveGlobal({favorites: [...list]});
          this.enhanceSelects();
        });
        pick.append(search, star); select.before(pick);
      }
      const query = plain(pick.querySelector('input').value.trim());
      const value = select.value;
      const rank = ([v]) => !overlayOf(v) ? 0 : favorites.has(overlayOf(v)) ? 1 : 2;
      const shown = all.filter(([v, t]) => !overlayOf(v) || v === value || !query || plain(t).includes(query))
        .sort((a, b) => rank(a) - rank(b));
      select.replaceChildren(...shown.map(([v, t]) => new Option((rank([v]) === 1 ? '★ ' : '') + t, v)));
      select.value = value;
      select.pickStamp = [...select.options].map(o => o.value).join('\n');
      const star = pick.querySelector('button');
      star.classList.toggle('on', favorites.has(overlayOf(value)));
      star.setAttribute('aria-pressed', String(favorites.has(overlayOf(value))));
    }
  }
});
