/* Every user-facing list of the inspector in one place: action names and option lists. Functions, not
   constants: they run after the language is known (js/lang.js), and each text is a literal call of t() that
   scripts/build_i18n.py finds. Help texts are "?<action>" and "?<action>.<field>" keys of the catalogs. */
'use strict';

const NAMES = () => ({showall: t('Show All'), hideall: t('Hide All'), toggle: t('Overlay'),
  numericfields: t('Numeric Fields'), multiplier: t('Multiplier'), knob: t('Knob Control'), display: t('Display'),
  nextslot: t('Next Slot'), prevslot: t('Previous Slot'), slotwheel: t('Slot Wheel'), reveal: t('Reveal Answer'),
  dialvalue: t('Dial Value'), visor: t('Visor'), timer: t('Timer'), obsscene: t('OBS Scene'),
  obsrefresh: t('OBS Refresh Browser'), macro: t('Macro'), panic: t('Panic'), restore: t('Restore'),
  snapshot: t('Scene'), shift: t('Shift'), clock: t('Clock'), undo: t('Undo'), lock: t('Lock'), swap: t('Swap Sides'),
  cycle: t('Cycle'), reset: t('Reset'), datasource: t('Data Source'), template: t('Text Template'), vote: t('Poll Vote'),
  goal: t('Goal'), status: t('Status'), lockdesk: t('Lock Desk')});

const FUNCTIONS = () => [['', t('Do nothing')], ['show', t('Show')], ['hide', t('Hide')]];
const STEPS = () => [['show', t('Show overlay')], ['hide', t('Hide overlay')], ['toggle', t('Toggle overlay')],
  ['takeslot', t('Take slot number')], ['nextslot', t('Next slot')], ['prevslot', t('Previous slot')],
  ['showall', t('Show all')], ['hideall', t('Hide all')], ['setfield', t('Set field value')], ['timer', t('Timer')],
  ['obsscene', t('OBS scene')], ['snapshot', t('Recall scene')], ['wait', t('Wait (ms)')]];
const CHANNELS = () => [['', t('None')], ...[1, 2, 3, 4, 5, 6].map(n => [String(n), t('Channel {n}', {n})])];
const TIMER_OPERATIONS = () => [['toggle', t('Play / Pause')], ['play', t('Play')], ['pause', t('Pause')],
  ['reset', t('Reset')], ['start', t('Start (from zero)')]];
const OBS_WHERE = () => t('OBS connection, shared by every key: in OpenDeck, Plugins → UNO Overlays → Settings (gear).');
const GLOBAL_WHERE = () => t('Triggers, exclusive group times and control apps are shared by every key: in OpenDeck, Plugins → UNO Overlays → Settings (gear).');
