% UNO Overlays for OpenDeck — Manual
% Contents

# Introduction {#introduction}

UNO Overlays controls the overlays of [UNO](https://overlays.uno) (Singular.live) from OpenDeck on Linux, with keys and knobs: show and hide, server slots, scoreboard, clocks, data sources, polls, goals, macros, OBS Studio and diagnostics.

It is designed for the Rise Mode Vision 01 (15 keys) and Vision Sound 01 (6 keys, 3 knobs and 3 buttons without a screen), and works with every device OpenDeck supports.

- Every key shows its state: the icon is **white** off air and **bright red** on air. The state comes from UNO in real time.
- Every UNO operation, from every device, key, knob and inspector, goes through **one global queue**, one at a time and in order.
- Triggers, exclusive groups and the list of control apps are **global**: they work whatever profile or device is on screen.

# Installation {#installation}

## Requirements

- OpenDeck for Linux 2.6.0 or newer.
- Python 3.10 or newer with HTTPS certificates (Debian/Ubuntu: `sudo apt install python3 ca-certificates`).
- Internet access to talk to UNO.
- OBS Studio 28 or newer, only for the OBS actions and triggers.
- Nothing else: the only dependency (`websockets`) comes inside the package.

## Install or update

1. Download `opendeck-uno-overlays-<version>-linux.plugin.zip` from the release.
2. In OpenDeck, open **Plugins → Install from file** and choose the file.
3. The installation replaces the previous folder of the plugin. Keys, knobs and settings stay: the identifiers of the plugin and of its actions did not change.
4. If a key does not update, restart OpenDeck.

![OpenDeck: Plugins → Install from file](botao_instalar_plugins.jpg)

## Updating from version 1.0

- Triggers of Overlay keys move to the global list by themselves the first time each key appears. A key that is never shown (another profile, a device that is not connected) keeps its old triggers until it appears once: open that profile once after updating.
- The option "Edits while on air (optional) – Hide, change, show again" no longer exists: edits on air are always written directly, after the pause set on the settings page.

# First steps {#first-steps}

1. In UNO, open the Control App of the overlay, **? → API Description**, and copy the token: the part of the address between `/controlapps/` and `/api`. Use the control token, not the output URL used in OBS.
2. In OpenDeck, drag a **UNO Overlays** action to a key, paste the token in **API Token** and click **Connect / Reload**.
3. Choose the overlay (the list has search and ★ favorites) and what the key does. Edits in the form go straight to UNO; wait for **Saved to UNO.**
4. Every field has a **?** next to it: move the pointer over it, or reach it with Tab, to read what the field does. Esc closes the text.

![Inspector of an Overlay key](inspetor_overlay.jpg)

# Settings page {#settings-page}

What every key shares is on the plugin's own settings page: in OpenDeck, **Plugins**, on the **UNO Overlays** card, click the green gear (**Settings**). The page opens in the default web browser, accepts connections only from this computer and closes after 10 minutes without use.

![OpenDeck: the gear of the UNO Overlays plugin](engrenagem_plugins.jpg)

![Settings page of the plugin](pagina_configuracoes.jpg)

{{settings}}

## Languages

The plugin speaks Portuguese (Brazil), English, Spanish, Italian, German, Japanese, Chinese (simplified), Korean and French. With **Automatic**, it follows the language chosen in OpenDeck's settings; a language chosen on the settings page wins. OpenDeck does not offer Italian, so Italian is chosen only on the settings page. When the language of OpenDeck changes, open an inspector or the settings page again so the plugin reads it.

## Triggers

A trigger runs a function when an event happens, like the triggers of vMix: show or hide an overlay, after a delay of up to 30 000 ms. Events: an OBS scene goes to or leaves program, streaming starts or stops, recording starts or stops, a UNO overlay goes on or off air (the "When this overlay goes on air / off air" chains of version 1.0). Use **Add trigger** to add as many as you need; each one can be switched off without being removed.

Every trigger writes to the plugin log: the event received, the decision (fired or ignored, and why) and the result in UNO, without tokens.

## Exclusive groups

Overlays of the same group are never on air together: showing one hides the others, also those whose keys are not on screen. Overlay keys choose their group by name; the time and the members are on the settings page.

# How it works {#how-it-works}

- **Global queue.** All keys, knobs and inspectors of every device enter one queue: one UNO operation at a time, in order. Turns of the same field add up into one write.
- **Limits.** The queue waits for the next window when it reaches the limits announced by UNO. The free uno plan has a daily cap of 10 000 App API calls; the Status key counts them.
- **Saves.** A write is confirmed only by the server; nothing is repeated by itself after a timeout.
- **Edits on air.** While an overlay is on air, an edit is sent only after a pause without changes (1000 ms by default), so the audience never sees a word half typed. Closing the inspector, moving to another field, pressing a key or Panic send it at once.
- **Keys not on screen.** Auto Close timers and presses already made keep running after a profile switch; only a real change of the key's settings, Panic or a new press cancel them.

# Limitations {#limitations}

- **Visor and knob.** A Visor key and its knob work only while both are on screen: the knob keeps what it is choosing, and OpenDeck only tells the plugin about knobs of the selected profile.
- **Restore.** The set of overlays that Restore brings back lives in memory: a plugin restart forgets it.
- **Trigger delays.** A trigger delay already counting survives edits of the trigger; Panic cancels it.
- **Deleted keys.** OpenDeck sends the same event when a key is deleted and when its profile is switched, so an Auto Close already counting finishes normally (at most 120 s).
- **Migration.** Triggers of version 1.0 move to the global list only when their key appears at least once.
- **Quiz.** Reveal Answer is generic: choose the field and the values that your overlay uses to reveal the answer.

# Use cases {#use-cases}

## Scoreboard

Numeric Fields keys for each team (the key shows +1, +2, +3…), a Display key for each score, Undo, Lock, Swap Sides when the teams change sides, Cycle for the period and Reset held for 2 s at the end.

## Quiz

A Slot Wheel knob with the carousel on: each turn puts the next question on air; pressing shows or hides the overlay. A Reveal Answer key reveals the answer and copies the correct option into the highlight field; the next question hides it again by itself.

## Clock

A Clock key in a text field: countdown, count up, time of day or until a finish time, with wrap-up colors. On a knob, turning adjusts the time and a Visor key shows it.

## Ticker and lists

A Data Source with a typed list, a .txt or a .csv file, mapped to the fields of the overlay, with Auto Next and Loop.

## OBS Studio

An OBS Scene key switches the program scene and can show an overlay. A trigger shows the camera lower third when the scene "Webcam" goes to program and hides it when it leaves. OBS Refresh Browser reloads several browser sources, or every browser source of a scene.

# Actions {#actions}

{{actions}}

# Troubleshooting {#troubleshooting}

- **"Enter the control API token, not the output URL."** Paste only the token (letters, numbers, `_` and `-`).
- **"UNO HTTP 4xx".** The token is wrong or was revoked: copy it again in **API Description**.
- **"UNO HTTP 429".** Too many requests: wait a moment; avoid tools that query UNO with the same token.
- **"OBS is not connected…".** Set it up on the settings page and check that OBS is open.
- **The gear opens nothing.** No default web browser is set: `xdg-settings get default-web-browser` shows which one the system uses.
- **A key only shows an alert.** The desk is locked (Lock Desk red) or the key is outside the allowed OBS scenes.
- **A trigger did not run.** Look at the plugin log: each trigger writes whether it fired or was ignored and why. Log: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Privacy and security {#privacy}

Names and texts of the overlays are personal data and go to UNO. The plugin sends nothing to its authors and writes no tokens in logs. Tokens are kept in OpenDeck's settings on this computer; the settings page never shows a token or the OBS password back. Stored scenes and the log can be deleted on request (Delete stored scene, Clear log). To exercise your rights under Brazil's LGPD, open an issue in the project. Details in PRIVACY.md and SECURITY.md of the plugin.
