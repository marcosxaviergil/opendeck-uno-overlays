/* Languages of the inspector and the settings page. Catalogs (js/i18n.js, generated from i18n/*.json by
   scripts/build_i18n.py) use the English text as the key, like gettext: a missing translation shows English.
   Keys that are not English text start with "?" (help of a field) and live in the English catalog too. */
'use strict';

const LANG = {code: 'en'};
const LANGUAGE_NAMES = {'pt-BR': 'Português (Brasil)', en: 'English', es: 'Español', it: 'Italiano', de: 'Deutsch',
  ja: '日本語', 'zh-CN': '简体中文', ko: '한국어', fr: 'Français'};

function setLanguage(code) {
  LANG.code = (window.I18N || {})[code] || code === 'en' ? code : 'en';
  document.documentElement.lang = LANG.code;
  for (const node of document.querySelectorAll('[data-t]')) node.textContent = t(node.dataset.t);
  for (const node of document.querySelectorAll('[data-t-placeholder]')) node.placeholder = t(node.dataset.tPlaceholder);
}

// t(text, values) → the text in the current language, {name} filled after translating.
function t(text, values) {
  const catalogs = window.I18N || {};
  let out = (catalogs[LANG.code] || {})[text] || (text[0] === '?' ? (catalogs.en || {})[text] : '') || text;
  if (values) out = out.replace(/\{(\w+)\}/g, (match, key) => key in values ? String(values[key]) : match);
  return out;
}

// Help text when there is one: "?<action>" for the action, "?<action>.<key>" for a field, else the shared "?<key>".
function helpText(action, key) {
  const english = (window.I18N || {}).en || {};
  const found = (key ? [`?${action}.${key}`, `?${key}`] : [`?${action}`]).find(id => id in english);
  return found ? t(found) : '';
}
