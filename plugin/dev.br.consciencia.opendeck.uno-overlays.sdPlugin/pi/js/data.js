/* Loaders and dropdown builders for overlays, slots and numeric fields.
   Adapted from PIData of the supplied UNO Overlay Control 5.0.1-fixed6 (SeTIC UFSC, MIT). */
'use strict';

const PIData = {

  // ── Overlay loading ──────────────────────────────────────────────────────

  /** Populate a <select> with overlay options. */
  populateOverlaySelect(el, overlays, selectedId) {
    el.replaceChildren(new Option(t('Select an overlay…'), ''), ...overlays.map(ov => new Option(ov.name || ov.id, ov.id)));
    if (selectedId) el.value = selectedId;
  },

  /** Populate a <select> with slot options from a specific overlay. */
  populateSlotSelect(el, overlay, selectedSlot) {
    const slots = overlay?.slots || [];
    el.replaceChildren(new Option(slots.length ? t('Default slot') : t('No server slots'), '0'),
      ...slots.map((slot, i) => new Option(slot.name || t('Slot {n}', {n: i + 1}), i + 1)));
    if (slots.length && selectedSlot) el.value = selectedSlot;
    el.closest('.section')?.classList.toggle('hidden', !slots.length);
  },

  // ── Numeric field discovery ────────────────────────────────────────────

  /**
   * Scan all overlays for incrementable fields.
   * Returns array of { composite, label, overlayId, fieldId, idx }.
   */
  async loadNumericFields(api, overlays) {
    const entries = [];

    // Sequential overlays, two reads each: avoid flooding the control app.
    for (const ov of overlays) {
        const [model, content] = await Promise.all([
          api.getOverlayModel(ov.id),
          api.getOverlayContent(ov.id)
        ]);
        const fields = (model && model.model) ? model.model : [];
        const data   = content || {};
        const name   = ov.name || ov.id;

        // Phase 1: titles where at least one sibling has a numeric value
        const numTitles = new Set();
        for (const f of fields) {
          if (f.type === 'text' && PIData.isNumeric(data[f.id])) {
            numTitles.add(f.title);
          }
        }

        // Phase 2: include incrementable fields
        for (const f of fields) {
          if (PIData.includeField(f, data, numTitles)) {
            entries.push({
              composite: ov.id + '::' + f.id,
              label:     name + '  ›  ' + f.id,
              overlayId: ov.id,
              fieldId:   f.id,
              idx:       f.index || 0
            });
          }
        }
    }

    return entries.sort((a, b) => a.label.localeCompare(b.label) || a.idx - b.idx);
  },

  /** Model fields matching test(field), e.g. type "timecontrol" (singular-datastore checkDataType). */
  async loadFields(api, overlays, test) {
    const entries = [];
    for (const ov of overlays) {
      const model = await api.getOverlayModel(ov.id);
      for (const f of (model && model.model) || []) {
        if (test(f)) entries.push({composite: ov.id + '::' + f.id, type: f.type, label: (ov.name || ov.id) + '  ›  ' + (f.title || f.id)});
      }
    }
    return entries;
  },

  /** Populate a <select> with numeric field options. */
  populateFieldSelect(el, entries, selectedComposite) {
    el.replaceChildren(new Option(entries.length ? t('Select a numeric field…') : t('No matching fields found'), ''),
      ...entries.map(e => new Option(e.label, e.composite)));
    if (entries.length && selectedComposite) el.value = selectedComposite;
  },

  // ── Detection helpers ─────────────────────────────────────────────────

  includeField(field, data, numTitles) {
    if (field.type === 'number' || field.type === 'counter') return true;
    if (field.type !== 'text') return false;
    const v = data[field.id];
    if (PIData.isNumeric(v)) return true;
    return PIData.isEmpty(v) && numTitles.has(field.title);
  },

  isNumeric(v) {
    if (typeof v === 'number') return Number.isFinite(v);
    if (v == null) return false;
    const s = String(v).trim().replace(',', '.');
    return s !== '' && !isNaN(s) && !isNaN(parseFloat(s));
  },

  isEmpty(v) {
    return v == null || String(v).trim() === '';
  }
};
