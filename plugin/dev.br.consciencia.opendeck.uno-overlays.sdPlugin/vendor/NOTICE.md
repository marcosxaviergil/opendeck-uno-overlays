# Third-party code

- Material Symbols (Outlined), Google, **Apache-2.0**. Full license: `material-symbols-LICENSE`.
  Source: github.com/google/material-design-icons at commit bd8cb85bd4bad964fe6918f79665bb40c3a8efef,
  `variablefont/MaterialSymbolsOutlined[FILL,GRAD,opsz,wght].ttf` (SHA-256
  0128da5981791d2fe09918c337ea6657b0ef2e4e5f8f4af3e1dc5f31889b2311) and `.codepoints`
  (225bd09137103cb7746bc93dc08d08764c9f0c3bd04f4b958d4a3c3c19432dd6). Modified: instanced at
  FILL 1, GRAD 0, opsz 48, wght 400 and subset to the glyphs listed in `scripts/build_icons.py` of the source project
  (`uno/glyphs.py`, `pi/css/symbols.css`, `images/*.svg`).

- `websockets` **15.0.1**, copyright Aymeric Augustin and contributors,
  BSD-3-Clause. Full license: `websockets-LICENSE`.
- Official source: https://github.com/python-websockets/websockets/tree/15.0.1
- Pure-Python wheel from PyPI: `websockets-15.0.1-py3-none-any.whl`.
- SHA-256: `f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f`.
- The wheel is kept in the source project (`third_party/`); before every
  build, `scripts/build.py` checks its SHA-256 and that the `websockets/` files
  here are byte-identical to the ones in the wheel (extracted unchanged).
  No architecture-specific extension, optional proxy package, pip invocation,
  dependency download or Internet access is needed when running the plugin.

The original UNO Overlay Control plugin was supplied by Marcos Xavier in
fourteen versions (3.1.1 through 5.0.1-fixed6). Its README declares MIT and
attributes authorship to SeTIC UFSC. The supplied images, dynamic form builder,
numeric discovery and UI utilities are reused and adapted with attribution.
The Python action logic ports the supplied JavaScript behavior. The OpenDeck
bridge, inspector orchestration and tests are new MIT-licensed adaptations.
OpenDeck and its hardware drivers remain separate installed applications;
their source or binaries are not redistributed in this package.

This project was prepared with AI assistance; it is not an official OpenDeck,
OpenAction, Elgato, Rise Mode, Singular.live or overlays.uno release.
