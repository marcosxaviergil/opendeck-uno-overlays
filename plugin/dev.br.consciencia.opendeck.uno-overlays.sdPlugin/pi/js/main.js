/* Start: one inspector per page; OpenDeck calls connectOpenActionSocket (or the Elgato name). */
'use strict';

const inspector = new Inspector();
window.connectOpenActionSocket = (...args) => inspector.bridge.connect(...args);
window.connectElgatoStreamDeckSocket = window.connectOpenActionSocket;
