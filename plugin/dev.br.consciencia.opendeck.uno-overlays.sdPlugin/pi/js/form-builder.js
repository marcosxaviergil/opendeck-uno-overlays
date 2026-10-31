/* Form generated from an overlay's UNO model (one control per field, JSON types kept).
   Adapted from the FormBuilder of the supplied UNO Overlay Control 5.0.1-fixed6 (SeTIC UFSC, MIT). */
'use strict';

class FormBuilder {
  constructor(container) {
    this.container = container;
    this.fieldMap = new Map();
  }

  buildFromModel(model) {
    this.model = model;
    this.fieldMap.clear();
    if (!Array.isArray(model?.model)) {
      this.container.replaceChildren(Object.assign(document.createElement('p'), {className: 'hint', textContent: t('No fields found')}));
      return;
    }
    const fields = [...model.model].sort((a, b) => (a.index || 0) - (b.index || 0));
    this.container.replaceChildren(...(model.groups || []).map(group => this.createFieldset(group, fields)));
    // Models can contain ungrouped fields alongside groups (all of them when there are no groups).
    this.container.append(...fields.filter(field => !this.fieldMap.has(field.id)).map(field => this.createField(field)));
  }

  createFieldset(group, fields) {
    const fieldset = document.createElement('fieldset');
    fieldset.append(Object.assign(document.createElement('legend'), {textContent: group.title || t('Settings')}));
    for (const id of group.childIds || []) {
      const field = fields.find(f => f.id === id);
      if (field) fieldset.append(this.createField(field));
    }
    return fieldset;
  }

  createField(field) {
    const element = (tag, props = {}) => Object.assign(document.createElement(tag), props);
    const wrapper = element('div', {className: 'field-row'});
    const id = `${this.prefix || ''}field_${field.id}`;
    const title = field.title || field.id;
    if (field.hideTitle !== true) wrapper.append(element('label', {htmlFor: id, textContent: title}));
    let input;
    switch (field.type) {
      case 'text':
        input = element('input', {type: 'text', value: field.defaultValue || '', placeholder: field.title || ''});
        break;
      case 'number':
      case 'counter':
        input = element('input', {type: 'number', value: field.defaultValue || 0, step: field.step ?? 'any'});
        if (field.min !== undefined) input.min = field.min;
        if (field.max !== undefined) input.max = field.max;
        break;
      case 'checkbox':
        input = element('input', {type: 'checkbox', checked: field.defaultValue === true || field.defaultValue === 'true'});
        break;
      case 'image':
        input = element('input', {type: 'url', value: field.defaultValue || '', placeholder: 'https://…'});
        break;
      case 'selection':
        input = element('select');
        for (const opt of Array.isArray(field.selections) ? field.selections : []) input.add(new Option(opt.title ?? opt.id ?? opt, opt.id ?? opt));
        input.value = field.defaultValue || '';
        break;
      default:
        input = element('textarea', {value: JSON.stringify(field.defaultValue ?? '')});
        wrapper.append(element('div', {className: 'hint', textContent: t('{type}: edit the JSON value. Objects and arrays are preserved.', {type: field.type})}));
    }
    input.id = id;
    if (field.hideTitle === true) input.setAttribute('aria-label', title);  // the model hides the title, not its name
    wrapper.append(input);
    this.fieldMap.set(field.id, {element: input, type: field.type, field});
    return wrapper;
  }

  extractValues() {
    const values = {};
    this.fieldMap.forEach((fieldInfo, fieldId) => {
      const element = fieldInfo.element;
      if (fieldInfo.type === 'checkbox') {
        values[fieldId] = element.checked;
      } else if (fieldInfo.type === 'number' || fieldInfo.type === 'counter') {
        const value = element.value.trim() === '' ? 0 : Number(element.value);
        if (!Number.isFinite(value)) throw new Error(t('Invalid number: {field}', {field: fieldId}));
        values[fieldId] = value;
      } else if (['text', 'image', 'selection'].includes(fieldInfo.type)) {
        values[fieldId] = element.value;
      } else {
        try { values[fieldId] = JSON.parse(element.value); }
        catch { throw new Error(t('Invalid JSON: {field}', {field: fieldId})); }
      }
    });
    return values;
  }

  loadValues(values) {
    if (!values) return;
    this.fieldMap.forEach((fieldInfo, fieldId) => {
      if (values[fieldId] !== undefined) {
        const element = fieldInfo.element;
        if (fieldInfo.type === 'checkbox') {
          element.checked = [true, 1, 'true', '1'].includes(values[fieldId]);
        } else if (!['text', 'number', 'counter', 'image', 'selection'].includes(fieldInfo.type)) {
          element.value = JSON.stringify(values[fieldId]);
        } else {
          element.value = values[fieldId];
        }
      }
    });
  }
}
