# UNO Overlays para OpenDeck — código-fonte

[Português (Brasil)](#português-brasil) · [English](#english) · [Español](#español) ·
[Italiano](#italiano) · [Deutsch](#deutsch) · [日本語](#日本語) · [简体中文](#简体中文) ·
[한국어](#한국어) · [Français](#français)

## Português (Brasil)

Plugin Linux do [OpenDeck](https://github.com/nekename/OpenDeck) que controla overlays
do [UNO](https://overlays.uno) (Singular.live) por teclas e knobs. Este repositório
tem o plugin, os testes e o build. Para **usar** o plugin, leia o
[README do plugin](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md)
ou o manual em PDF anexado a cada release.

### Estrutura

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   o que vai no ZIP instalável
  manifest.json, launch.sh, main.py                         entrada (OpenDeck → Python)
  uno/                                                       regras puras e adaptadores (UNO, datastore, OBS)
  uno/runtime/                                               funcionalidades, uma por arquivo
  pi/                                                        inspetor e página de configurações (HTML, CSS, JS sem build)
  i18n/<idioma>.json                                         catálogos dos 9 idiomas (o texto em inglês é a chave)
  <idioma OpenDeck>.json, pi/js/i18n.js                      gerados por scripts/build_i18n.py
  images/, vendor/                                           ícones gerados; websockets e licenças
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD e segurança, para quem usa
tests/                                                       unittest + emuladores; tests/pi: navegador
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (enviar versão), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      o mesmo CI no Forgejo e no GitHub, só em tag de versão (v*)
third_party/                                                 wheel oficial do websockets (conferido no build)
docs/                                                        arquitetura, testes, fontes, skills, Forgejo, GitHub
docs/manual/<idioma>/manual.md, docs/manual/imagens/         fonte do manual em PDF e capturas de tela
```

### Comandos

```sh
make tools   # lista o que falta instalar (o mesmo que a imagem do CI tem)
make check   # tools, lint (pyflakes, ruff se houver, node --check, catálogos), testes Python e do inspetor, manual
make build   # dist/opendeck-uno-overlays-<versão>-linux.plugin.zip + SHA256SUMS do plugin
make manual  # dist/UNO-Overlays-<versão>-Manual.pdf, os 9 idiomas num arquivo
```

Requisitos de desenvolvimento: Python 3.10+, `python3-pyflakes`, Node.js, `make` e, para o
manual, `weasyprint`, `fontconfig`, `fonts-dejavu-core` e `fonts-noto-cjk` (apt).
Opcionais: `ruff`; Playwright com Chromium para o teste do inspetor. Detalhes em
[docs/TESTING.md](docs/TESTING.md).

### Documentação

- [Arquitetura](docs/ARCHITECTURE.md): camadas, runtime, fila global, inspetor, convenções.
- [Testes](docs/TESTING.md): o que cada teste cobre e como os emuladores funcionam.
- [Fontes](docs/SOURCES.md): documentação oficial e código que embasam cada decisão.
- [Skills](docs/SKILLS.md): skills do GitHub aplicadas em cada área.
- [Privacidade (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  e [Segurança](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Manual](docs/manual/): fonte do PDF por idioma; imagens em [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, envio de versão, releases por tag e como zerar o remoto. [Histórico](CHANGELOG.md). [Origem](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): o mesmo CI no GitHub Actions, release por tag e envio por HTTPS.

### Licença

MIT ([LICENSE](LICENSE)). Terceiros: `websockets` (BSD-3-Clause) e Material Symbols
(Apache-2.0), em [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).

## English

Linux plugin for [OpenDeck](https://github.com/nekename/OpenDeck) that controls
[UNO](https://overlays.uno) (Singular.live) overlays with keys and knobs. This repository
holds the plugin, its tests and its build. To **use** the plugin, read the
[plugin README](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md) (in Portuguese)
or the PDF manual attached to every release.

### Structure

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   what goes into the installable ZIP
  manifest.json, launch.sh, main.py                         entry point (OpenDeck → Python)
  uno/                                                       pure rules and adapters (UNO, datastore, OBS)
  uno/runtime/                                               features, one per file
  pi/                                                        inspector and settings page (HTML, CSS, JS without a build)
  i18n/<language>.json                                       catalogs of the 9 languages (the English text is the key)
  <OpenDeck language>.json, pi/js/i18n.js                    generated by scripts/build_i18n.py
  images/, vendor/                                           generated icons; websockets and licenses
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD (privacy) and security, for users
tests/                                                       unittest + emulators; tests/pi: browser
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (send a version), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      the same CI on Forgejo and GitHub, only on a version tag (v*)
third_party/                                                 official websockets wheel (checked during the build)
docs/                                                        architecture, tests, sources, skills, Forgejo, GitHub
docs/manual/<language>/manual.md, docs/manual/imagens/       source of the PDF manual and screenshots
```

### Commands

```sh
make tools   # lists what is missing (the same tools the CI image has)
make check   # tools, lint (pyflakes, ruff if present, node --check, catalogs), Python and inspector tests, manual
make build   # dist/opendeck-uno-overlays-<version>-linux.plugin.zip + SHA256SUMS of the plugin
make manual  # dist/UNO-Overlays-<version>-Manual.pdf, the 9 languages in one file
```

Development requirements: Python 3.10+, `python3-pyflakes`, Node.js, `make` and, for the
manual, `weasyprint`, `fontconfig`, `fonts-dejavu-core` and `fonts-noto-cjk` (apt).
Optional: `ruff`; Playwright with Chromium for the inspector test. Details in
[docs/TESTING.md](docs/TESTING.md).

### Documentation

The documents below are in Portuguese; the PDF manual has all 9 languages.

- [Architecture](docs/ARCHITECTURE.md): layers, runtime, global queue, inspector, conventions.
- [Tests](docs/TESTING.md): what each test covers and how the emulators work.
- [Sources](docs/SOURCES.md): official documentation and code behind each decision.
- [Skills](docs/SKILLS.md): GitHub skills applied in each area.
- [Privacy (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  and [Security](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Manual](docs/manual/): PDF source per language; images in [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, sending a version, releases by tag and how to reset the remote. [Changelog](CHANGELOG.md). [Origin](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): the same CI on GitHub Actions, release by tag and pushing over HTTPS.

### License

MIT ([LICENSE](LICENSE)). Third parties: `websockets` (BSD-3-Clause) and Material Symbols
(Apache-2.0), in [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).

## Español

Plugin para Linux de [OpenDeck](https://github.com/nekename/OpenDeck) que controla overlays
de [UNO](https://overlays.uno) (Singular.live) con teclas y knobs. Este repositorio
contiene el plugin, las pruebas y el build. Para **usar** el plugin, lea el
[README del plugin](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md) (en portugués)
o el manual en PDF adjunto a cada release.

### Estructura

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   lo que va en el ZIP instalable
  manifest.json, launch.sh, main.py                         entrada (OpenDeck → Python)
  uno/                                                       reglas puras y adaptadores (UNO, datastore, OBS)
  uno/runtime/                                               funcionalidades, una por archivo
  pi/                                                        inspector y página de configuración (HTML, CSS, JS sin build)
  i18n/<idioma>.json                                         catálogos de los 9 idiomas (el texto en inglés es la clave)
  <idioma OpenDeck>.json, pi/js/i18n.js                      generados por scripts/build_i18n.py
  images/, vendor/                                           iconos generados; websockets y licencias
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD (privacidad) y seguridad, para quien lo usa
tests/                                                       unittest + emuladores; tests/pi: navegador
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (enviar versión), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      el mismo CI en Forgejo y en GitHub, solo con etiqueta de versión (v*)
third_party/                                                 wheel oficial de websockets (verificado en el build)
docs/                                                        arquitectura, pruebas, fuentes, skills, Forgejo, GitHub
docs/manual/<idioma>/manual.md, docs/manual/imagens/         fuente del manual en PDF y capturas de pantalla
```

### Comandos

```sh
make tools   # lista lo que falta instalar (lo mismo que tiene la imagen del CI)
make check   # tools, lint (pyflakes, ruff si existe, node --check, catálogos), pruebas Python y del inspector, manual
make build   # dist/opendeck-uno-overlays-<versión>-linux.plugin.zip + SHA256SUMS del plugin
make manual  # dist/UNO-Overlays-<versión>-Manual.pdf, los 9 idiomas en un archivo
```

Requisitos de desarrollo: Python 3.10+, `python3-pyflakes`, Node.js, `make` y, para el
manual, `weasyprint`, `fontconfig`, `fonts-dejavu-core` y `fonts-noto-cjk` (apt).
Opcionales: `ruff`; Playwright con Chromium para la prueba del inspector. Detalles en
[docs/TESTING.md](docs/TESTING.md).

### Documentación

Los documentos siguientes están en portugués; el manual en PDF tiene los 9 idiomas.

- [Arquitectura](docs/ARCHITECTURE.md): capas, runtime, cola global, inspector, convenciones.
- [Pruebas](docs/TESTING.md): qué cubre cada prueba y cómo funcionan los emuladores.
- [Fuentes](docs/SOURCES.md): documentación oficial y código que respaldan cada decisión.
- [Skills](docs/SKILLS.md): skills de GitHub aplicadas en cada área.
- [Privacidad (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  y [Seguridad](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Manual](docs/manual/): fuente del PDF por idioma; imágenes en [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, envío de versión, releases por etiqueta y cómo vaciar el remoto. [Historial](CHANGELOG.md). [Origen](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): el mismo CI en GitHub Actions, release por etiqueta y envío por HTTPS.

### Licencia

MIT ([LICENSE](LICENSE)). Terceros: `websockets` (BSD-3-Clause) y Material Symbols
(Apache-2.0), en [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).

## Italiano

Plugin Linux per [OpenDeck](https://github.com/nekename/OpenDeck) che controlla gli overlay
di [UNO](https://overlays.uno) (Singular.live) con tasti e knob. Questo repository
contiene il plugin, i test e il build. Per **usare** il plugin, leggi il
[README del plugin](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md) (in portoghese)
o il manuale PDF allegato a ogni release.

### Struttura

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   ciò che va nello ZIP installabile
  manifest.json, launch.sh, main.py                         punto di ingresso (OpenDeck → Python)
  uno/                                                       regole pure e adattatori (UNO, datastore, OBS)
  uno/runtime/                                               funzionalità, una per file
  pi/                                                        inspector e pagina delle impostazioni (HTML, CSS, JS senza build)
  i18n/<lingua>.json                                         cataloghi delle 9 lingue (il testo inglese è la chiave)
  <lingua OpenDeck>.json, pi/js/i18n.js                      generati da scripts/build_i18n.py
  images/, vendor/                                           icone generate; websockets e licenze
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD (privacy) e sicurezza, per chi lo usa
tests/                                                       unittest + emulatori; tests/pi: browser
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (inviare una versione), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      la stessa CI su Forgejo e su GitHub, solo con tag di versione (v*)
third_party/                                                 wheel ufficiale di websockets (verificata nel build)
docs/                                                        architettura, test, fonti, skill, Forgejo, GitHub
docs/manual/<lingua>/manual.md, docs/manual/imagens/         sorgente del manuale PDF e screenshot
```

### Comandi

```sh
make tools   # elenca ciò che manca (gli stessi strumenti dell'immagine della CI)
make check   # tools, lint (pyflakes, ruff se presente, node --check, cataloghi), test Python e dell'inspector, manuale
make build   # dist/opendeck-uno-overlays-<versione>-linux.plugin.zip + SHA256SUMS del plugin
make manual  # dist/UNO-Overlays-<versione>-Manual.pdf, le 9 lingue in un file
```

Requisiti di sviluppo: Python 3.10+, `python3-pyflakes`, Node.js, `make` e, per il
manuale, `weasyprint`, `fontconfig`, `fonts-dejavu-core` e `fonts-noto-cjk` (apt).
Opzionali: `ruff`; Playwright con Chromium per il test dell'inspector. Dettagli in
[docs/TESTING.md](docs/TESTING.md).

### Documentazione

I documenti seguenti sono in portoghese; il manuale PDF contiene tutte le 9 lingue.

- [Architettura](docs/ARCHITECTURE.md): livelli, runtime, coda globale, inspector, convenzioni.
- [Test](docs/TESTING.md): cosa copre ogni test e come funzionano gli emulatori.
- [Fonti](docs/SOURCES.md): documentazione ufficiale e codice alla base di ogni decisione.
- [Skill](docs/SKILLS.md): skill di GitHub applicate in ogni area.
- [Privacy (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  e [Sicurezza](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Manuale](docs/manual/): sorgente del PDF per lingua; immagini in [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, invio di una versione, release per tag e come azzerare il remoto. [Cronologia](CHANGELOG.md). [Origine](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): la stessa CI su GitHub Actions, release per tag e invio via HTTPS.

### Licenza

MIT ([LICENSE](LICENSE)). Terze parti: `websockets` (BSD-3-Clause) e Material Symbols
(Apache-2.0), in [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).

## Deutsch

Linux-Plugin für [OpenDeck](https://github.com/nekename/OpenDeck), das Overlays von
[UNO](https://overlays.uno) (Singular.live) mit Tasten und Knobs steuert. Dieses Repository
enthält das Plugin, die Tests und den Build. Um das Plugin zu **benutzen**, lies das
[README des Plugins](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md) (auf Portugiesisch)
oder das PDF-Handbuch, das jedem Release beiliegt.

### Struktur

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   was in das installierbare ZIP kommt
  manifest.json, launch.sh, main.py                         Einstieg (OpenDeck → Python)
  uno/                                                       reine Regeln und Adapter (UNO, Datastore, OBS)
  uno/runtime/                                               Funktionen, eine pro Datei
  pi/                                                        Inspektor und Einstellungsseite (HTML, CSS, JS ohne Build)
  i18n/<Sprache>.json                                        Kataloge der 9 Sprachen (der englische Text ist der Schlüssel)
  <OpenDeck-Sprache>.json, pi/js/i18n.js                     erzeugt von scripts/build_i18n.py
  images/, vendor/                                           erzeugte Symbole; websockets und Lizenzen
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD (Datenschutz) und Sicherheit, für Anwender
tests/                                                       unittest + Emulatoren; tests/pi: Browser
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (Version senden), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      dieselbe CI auf Forgejo und GitHub, nur bei einem Versions-Tag (v*)
third_party/                                                 offizielles websockets-Wheel (im Build geprüft)
docs/                                                        Architektur, Tests, Quellen, Skills, Forgejo, GitHub
docs/manual/<Sprache>/manual.md, docs/manual/imagens/        Quelle des PDF-Handbuchs und Screenshots
```

### Befehle

```sh
make tools   # listet auf, was fehlt (dieselben Werkzeuge wie im CI-Image)
make check   # tools, Lint (pyflakes, ruff falls vorhanden, node --check, Kataloge), Python- und Inspektor-Tests, Handbuch
make build   # dist/opendeck-uno-overlays-<Version>-linux.plugin.zip + SHA256SUMS des Plugins
make manual  # dist/UNO-Overlays-<Version>-Manual.pdf, die 9 Sprachen in einer Datei
```

Entwicklungsvoraussetzungen: Python 3.10+, `python3-pyflakes`, Node.js, `make` und, für das
Handbuch, `weasyprint`, `fontconfig`, `fonts-dejavu-core` und `fonts-noto-cjk` (apt).
Optional: `ruff`; Playwright mit Chromium für den Inspektor-Test. Details in
[docs/TESTING.md](docs/TESTING.md).

### Dokumentation

Die folgenden Dokumente sind auf Portugiesisch; das PDF-Handbuch enthält alle 9 Sprachen.

- [Architektur](docs/ARCHITECTURE.md): Schichten, Runtime, globale Warteschlange, Inspektor, Konventionen.
- [Tests](docs/TESTING.md): was jeder Test abdeckt und wie die Emulatoren funktionieren.
- [Quellen](docs/SOURCES.md): offizielle Dokumentation und Code hinter jeder Entscheidung.
- [Skills](docs/SKILLS.md): in jedem Bereich angewandte GitHub-Skills.
- [Datenschutz (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  und [Sicherheit](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Handbuch](docs/manual/): PDF-Quelle pro Sprache; Bilder in [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, Version senden, Releases per Tag und Zurücksetzen des Remotes. [Änderungen](CHANGELOG.md). [Herkunft](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): dieselbe CI auf GitHub Actions, Release per Tag und Senden über HTTPS.

### Lizenz

MIT ([LICENSE](LICENSE)). Dritte: `websockets` (BSD-3-Clause) und Material Symbols
(Apache-2.0), in [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).

## 日本語

[UNO](https://overlays.uno)（Singular.live）のオーバーレイをキーとノブで操作する、
[OpenDeck](https://github.com/nekename/OpenDeck) 用の Linux プラグインです。このリポジトリには
プラグイン、テスト、ビルドが含まれます。プラグインを**使う**には、
[プラグインの README](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md)（ポルトガル語）
または各リリースに添付された PDF マニュアルをお読みください。

### 構成

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   インストール用 ZIP に入るもの
  manifest.json, launch.sh, main.py                         エントリーポイント（OpenDeck → Python）
  uno/                                                       純粋なルールとアダプター（UNO、datastore、OBS）
  uno/runtime/                                               機能。1 ファイルに 1 つ
  pi/                                                        インスペクターと設定ページ（HTML、CSS、ビルド不要の JS）
  i18n/<言語>.json                                           9 言語のカタログ（英語のテキストがキー）
  <OpenDeck の言語>.json, pi/js/i18n.js                      scripts/build_i18n.py が生成
  images/, vendor/                                           生成されたアイコン、websockets とライセンス
  docs/PRIVACY.md, docs/SECURITY.md                          利用者向けの LGPD（プライバシー）とセキュリティ
tests/                                                       unittest + エミュレーター、tests/pi: ブラウザー
scripts/                                                     build.py（ZIP）、build_manual.py（PDF）、build_i18n.py、build_icons.py、
                                                             forgejo_publish.py（バージョンの送信）、forgejo_release.py、forgejo_reset.py、
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      Forgejo と GitHub で同じ CI。バージョンタグ（v*）のときだけ実行
third_party/                                                 websockets の公式 wheel（ビルド時に照合）
docs/                                                        アーキテクチャ、テスト、出典、スキル、Forgejo、GitHub
docs/manual/<言語>/manual.md, docs/manual/imagens/           PDF マニュアルのソースとスクリーンショット
```

### コマンド

```sh
make tools   # 足りないものを一覧表示（CI イメージと同じツール）
make check   # tools、lint（pyflakes、あれば ruff、node --check、カタログ）、Python とインスペクターのテスト、マニュアル
make build   # dist/opendeck-uno-overlays-<バージョン>-linux.plugin.zip + プラグインの SHA256SUMS
make manual  # dist/UNO-Overlays-<バージョン>-Manual.pdf、9 言語を 1 ファイルに
```

開発に必要なもの: Python 3.10 以上、`python3-pyflakes`、Node.js、`make`。マニュアルには
`weasyprint`、`fontconfig`、`fonts-dejavu-core`、`fonts-noto-cjk`（apt）。
任意: `ruff`、インスペクターのテスト用に Chromium 付きの Playwright。詳細は
[docs/TESTING.md](docs/TESTING.md) にあります。

### ドキュメント

以下の文書はポルトガル語です。PDF マニュアルには 9 言語すべてが含まれます。

- [アーキテクチャ](docs/ARCHITECTURE.md): レイヤー、runtime、グローバルキュー、インスペクター、規約。
- [テスト](docs/TESTING.md): 各テストの対象とエミュレーターの仕組み。
- [出典](docs/SOURCES.md): 各判断の根拠となる公式ドキュメントとコード。
- [スキル](docs/SKILLS.md): 各分野で適用した GitHub のスキル。
- [プライバシー（LGPD）](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  と[セキュリティ](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md)。
- [マニュアル](docs/manual/): 言語ごとの PDF ソース。画像は [docs/manual/imagens](docs/manual/imagens/README.md)。
- [Forgejo](docs/FORGEJO.md): CI、バージョンの送信、タグによるリリース、リモートの初期化。[変更履歴](CHANGELOG.md)。[経緯](docs/EVOLUTION.md)。
- [GitHub](docs/GITHUB.md): GitHub Actions での同じ CI、タグによるリリース、HTTPS での送信。

### ライセンス

MIT（[LICENSE](LICENSE)）。サードパーティ: `websockets`（BSD-3-Clause）と Material Symbols
（Apache-2.0）。詳細は [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md)。

## 简体中文

用于 [OpenDeck](https://github.com/nekename/OpenDeck) 的 Linux 插件，可通过按键和旋钮控制
[UNO](https://overlays.uno)（Singular.live）的叠加层。本仓库包含插件、测试和构建。
如需**使用**插件，请阅读
[插件 README](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md)（葡萄牙语）
或每个 release 附带的 PDF 手册。

### 结构

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   放入可安装 ZIP 的内容
  manifest.json, launch.sh, main.py                         入口（OpenDeck → Python）
  uno/                                                       纯规则与适配器（UNO、datastore、OBS）
  uno/runtime/                                               功能，每个文件一个
  pi/                                                        检查器和设置页面（HTML、CSS、无需构建的 JS）
  i18n/<语言>.json                                           9 种语言的目录（英文文本作为键）
  <OpenDeck 语言>.json, pi/js/i18n.js                        由 scripts/build_i18n.py 生成
  images/, vendor/                                           生成的图标；websockets 及许可证
  docs/PRIVACY.md, docs/SECURITY.md                          面向用户的 LGPD（隐私）与安全说明
tests/                                                       unittest + 模拟器；tests/pi：浏览器
scripts/                                                     build.py（ZIP）、build_manual.py（PDF）、build_i18n.py、build_icons.py、
                                                             forgejo_publish.py（发送版本）、forgejo_release.py、forgejo_reset.py、
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      Forgejo 与 GitHub 上相同的 CI，仅在版本标签（v*）时运行
third_party/                                                 websockets 官方 wheel（构建时校验）
docs/                                                        架构、测试、来源、技能、Forgejo、GitHub
docs/manual/<语言>/manual.md, docs/manual/imagens/           PDF 手册的源文件和截图
```

### 命令

```sh
make tools   # 列出缺少的工具（与 CI 镜像相同）
make check   # tools、lint（pyflakes、如有 ruff、node --check、目录）、Python 与检查器测试、手册
make build   # dist/opendeck-uno-overlays-<版本>-linux.plugin.zip + 插件的 SHA256SUMS
make manual  # dist/UNO-Overlays-<版本>-Manual.pdf，9 种语言合为一个文件
```

开发要求：Python 3.10+、`python3-pyflakes`、Node.js、`make`；生成手册还需要
`weasyprint`、`fontconfig`、`fonts-dejavu-core` 和 `fonts-noto-cjk`（apt）。
可选：`ruff`；检查器测试需要带 Chromium 的 Playwright。详见
[docs/TESTING.md](docs/TESTING.md)。

### 文档

以下文档为葡萄牙语；PDF 手册包含全部 9 种语言。

- [架构](docs/ARCHITECTURE.md)：分层、runtime、全局队列、检查器、约定。
- [测试](docs/TESTING.md)：每个测试覆盖的内容以及模拟器的工作方式。
- [来源](docs/SOURCES.md)：每项决策所依据的官方文档和代码。
- [技能](docs/SKILLS.md)：各领域所采用的 GitHub 技能。
- [隐私（LGPD）](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  和[安全](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md)。
- [手册](docs/manual/)：各语言的 PDF 源文件；图片位于 [docs/manual/imagens](docs/manual/imagens/README.md)。
- [Forgejo](docs/FORGEJO.md)：CI、发送版本、按标签发布以及如何重置远程仓库。[更新日志](CHANGELOG.md)。[由来](docs/EVOLUTION.md)。
- [GitHub](docs/GITHUB.md)：GitHub Actions 上相同的 CI、按标签发布以及通过 HTTPS 推送。

### 许可证

MIT（[LICENSE](LICENSE)）。第三方：`websockets`（BSD-3-Clause）和 Material Symbols
（Apache-2.0），见 [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md)。

## 한국어

키와 노브로 [UNO](https://overlays.uno)(Singular.live)의 오버레이를 제어하는
[OpenDeck](https://github.com/nekename/OpenDeck)용 Linux 플러그인입니다. 이 저장소에는
플러그인, 테스트, 빌드가 들어 있습니다. 플러그인을 **사용**하려면
[플러그인 README](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md)(포르투갈어)
또는 각 릴리스에 첨부된 PDF 매뉴얼을 읽어 주세요.

### 구조

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   설치용 ZIP에 들어가는 내용
  manifest.json, launch.sh, main.py                         진입점(OpenDeck → Python)
  uno/                                                       순수 규칙과 어댑터(UNO, datastore, OBS)
  uno/runtime/                                               기능, 파일 하나에 하나씩
  pi/                                                        인스펙터와 설정 페이지(HTML, CSS, 빌드 없는 JS)
  i18n/<언어>.json                                           9개 언어 카탈로그(영어 텍스트가 키)
  <OpenDeck 언어>.json, pi/js/i18n.js                        scripts/build_i18n.py가 생성
  images/, vendor/                                           생성된 아이콘, websockets와 라이선스
  docs/PRIVACY.md, docs/SECURITY.md                          사용자를 위한 LGPD(개인정보)와 보안
tests/                                                       unittest + 에뮬레이터, tests/pi: 브라우저
scripts/                                                     build.py(ZIP), build_manual.py(PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py(버전 보내기), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      Forgejo와 GitHub에서 같은 CI, 버전 태그(v*)일 때만 실행
third_party/                                                 websockets 공식 wheel(빌드에서 확인)
docs/                                                        아키텍처, 테스트, 출처, 스킬, Forgejo, GitHub
docs/manual/<언어>/manual.md, docs/manual/imagens/           PDF 매뉴얼 소스와 스크린샷
```

### 명령

```sh
make tools   # 없는 것을 나열(CI 이미지와 같은 도구)
make check   # tools, lint(pyflakes, 있으면 ruff, node --check, 카탈로그), Python과 인스펙터 테스트, 매뉴얼
make build   # dist/opendeck-uno-overlays-<버전>-linux.plugin.zip + 플러그인 SHA256SUMS
make manual  # dist/UNO-Overlays-<버전>-Manual.pdf, 9개 언어를 한 파일로
```

개발 요구 사항: Python 3.10+, `python3-pyflakes`, Node.js, `make`, 그리고 매뉴얼에는
`weasyprint`, `fontconfig`, `fonts-dejavu-core`, `fonts-noto-cjk`(apt).
선택 사항: `ruff`, 인스펙터 테스트용 Chromium이 포함된 Playwright. 자세한 내용은
[docs/TESTING.md](docs/TESTING.md)에 있습니다.

### 문서

아래 문서는 포르투갈어입니다. PDF 매뉴얼에는 9개 언어가 모두 들어 있습니다.

- [아키텍처](docs/ARCHITECTURE.md): 계층, runtime, 전역 대기열, 인스펙터, 규칙.
- [테스트](docs/TESTING.md): 각 테스트가 다루는 내용과 에뮬레이터의 동작 방식.
- [출처](docs/SOURCES.md): 각 결정의 근거가 되는 공식 문서와 코드.
- [스킬](docs/SKILLS.md): 분야별로 적용한 GitHub 스킬.
- [개인정보(LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  및 [보안](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [매뉴얼](docs/manual/): 언어별 PDF 소스, 이미지는 [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md): CI, 버전 보내기, 태그별 릴리스, 원격 저장소 초기화 방법. [변경 기록](CHANGELOG.md). [유래](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md): GitHub Actions의 같은 CI, 태그별 릴리스, HTTPS로 보내기.

### 라이선스

MIT([LICENSE](LICENSE)). 서드파티: `websockets`(BSD-3-Clause)와 Material Symbols
(Apache-2.0), [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md) 참고.

## Français

Plugin Linux pour [OpenDeck](https://github.com/nekename/OpenDeck) qui pilote les overlays
d'[UNO](https://overlays.uno) (Singular.live) avec des touches et des knobs. Ce dépôt
contient le plugin, ses tests et son build. Pour **utiliser** le plugin, lisez le
[README du plugin](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/README.md) (en portugais)
ou le manuel PDF joint à chaque release.

### Structure

```text
plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/   ce qui va dans le ZIP installable
  manifest.json, launch.sh, main.py                         point d'entrée (OpenDeck → Python)
  uno/                                                       règles pures et adaptateurs (UNO, datastore, OBS)
  uno/runtime/                                               fonctionnalités, une par fichier
  pi/                                                        inspecteur et page de réglages (HTML, CSS, JS sans build)
  i18n/<langue>.json                                         catalogues des 9 langues (le texte anglais est la clé)
  <langue OpenDeck>.json, pi/js/i18n.js                      générés par scripts/build_i18n.py
  images/, vendor/                                           icônes générées ; websockets et licences
  docs/PRIVACY.md, docs/SECURITY.md                          LGPD (confidentialité) et sécurité, pour les utilisateurs
tests/                                                       unittest + émulateurs ; tests/pi : navigateur
scripts/                                                     build.py (ZIP), build_manual.py (PDF), build_i18n.py, build_icons.py,
                                                             forgejo_publish.py (envoyer une version), forgejo_release.py, forgejo_reset.py,
                                                             github_release.py
.forgejo/workflows/, .github/workflows/                      la même CI sur Forgejo et GitHub, uniquement sur un tag de version (v*)
third_party/                                                 wheel officiel de websockets (vérifié au build)
docs/                                                        architecture, tests, sources, skills, Forgejo, GitHub
docs/manual/<langue>/manual.md, docs/manual/imagens/         source du manuel PDF et captures d'écran
```

### Commandes

```sh
make tools   # liste ce qui manque (les mêmes outils que l'image de la CI)
make check   # tools, lint (pyflakes, ruff s'il est là, node --check, catalogues), tests Python et de l'inspecteur, manuel
make build   # dist/opendeck-uno-overlays-<version>-linux.plugin.zip + SHA256SUMS du plugin
make manual  # dist/UNO-Overlays-<version>-Manual.pdf, les 9 langues dans un fichier
```

Prérequis de développement : Python 3.10+, `python3-pyflakes`, Node.js, `make` et, pour le
manuel, `weasyprint`, `fontconfig`, `fonts-dejavu-core` et `fonts-noto-cjk` (apt).
Optionnels : `ruff` ; Playwright avec Chromium pour le test de l'inspecteur. Détails dans
[docs/TESTING.md](docs/TESTING.md).

### Documentation

Les documents ci-dessous sont en portugais ; le manuel PDF contient les 9 langues.

- [Architecture](docs/ARCHITECTURE.md) : couches, runtime, file globale, inspecteur, conventions.
- [Tests](docs/TESTING.md) : ce que couvre chaque test et comment fonctionnent les émulateurs.
- [Sources](docs/SOURCES.md) : documentation officielle et code à l'appui de chaque décision.
- [Skills](docs/SKILLS.md) : skills GitHub appliquées dans chaque domaine.
- [Confidentialité (LGPD)](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md)
  et [Sécurité](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).
- [Manuel](docs/manual/) : source du PDF par langue ; images dans [docs/manual/imagens](docs/manual/imagens/README.md).
- [Forgejo](docs/FORGEJO.md) : CI, envoi d'une version, releases par tag et remise à zéro du dépôt distant. [Historique](CHANGELOG.md). [Origine](docs/EVOLUTION.md).
- [GitHub](docs/GITHUB.md) : la même CI sur GitHub Actions, release par tag et envoi en HTTPS.

### Licence

MIT ([LICENSE](LICENSE)). Tiers : `websockets` (BSD-3-Clause) et Material Symbols
(Apache-2.0), dans [vendor/NOTICE.md](plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/vendor/NOTICE.md).
