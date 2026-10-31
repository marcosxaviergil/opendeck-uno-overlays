/* "?" help next to a field, like OpenDeck's own Tooltip.svelte (phosphor Question icon).
   WCAG 2.2 SC 1.4.13 (Content on Hover or Focus): it shows on hover and on keyboard focus, stays while the
   pointer is over it (hoverable), and Esc dismisses it without moving the focus (dismissible). The control
   gets aria-describedby, so screen readers read the same text. No inline script: the settings page runs
   under CSP script-src 'self'. */
'use strict';

let tipSerial = 0;

// The "?" button and its text. `control`, when given, is described by the text too.
function helpTip(text, name, control) {
  const id = `tip-${++tipSerial}`;
  const box = Object.assign(document.createElement('span'), {className: 'tip'});
  const button = Object.assign(document.createElement('button'), {type: 'button', className: 'tip-button'});
  button.setAttribute('aria-label', t('Help: {name}', {name}));
  button.setAttribute('aria-describedby', id);
  button.append(Object.assign(document.createElement('span'), {className: 'ms', textContent: (window.GLYPHS || {}).help || '?',
    ariaHidden: 'true'}));
  const bubble = Object.assign(document.createElement('span'), {id, className: 'tip-text', textContent: text});
  bubble.setAttribute('role', 'tooltip');
  box.append(button, bubble);
  box.addEventListener('mouseleave', () => box.classList.remove('dismissed'));
  button.addEventListener('blur', () => box.classList.remove('dismissed'));
  if (control) control.setAttribute('aria-describedby', [control.getAttribute('aria-describedby'), id].filter(Boolean).join(' '));
  return box;
}

document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  for (const box of document.querySelectorAll('.tip:hover, .tip:focus-within')) box.classList.add('dismissed');
});
