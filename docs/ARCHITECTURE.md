# Arquitetura

## Visão geral

```text
 dispositivo ──► OpenDeck ──WebSocket 57116──► main.py ──► Runtime (uno/runtime)
                   │                                          │
                   └─ inspetor (pi/, HTTP 57118) ─sendToPlugin┘
                                                              ├─► UnoAPI      HTTPS PUT app.overlays.uno/apiv2 (comandos)
                                                              ├─► Datastore   WSS datastore.singular.live (Socket.IO: ler, gravar slots, eventos)
                                                              ├─► Obs         WS local (obs-websocket 5)
                                                              └─► LocalPage   HTTP 127.0.0.1 (página de configurações)
 Plugins → UNO Overlays → engrenagem ──showSettingsInterface──► Runtime ──► navegador padrão (webbrowser)
```

- O OpenDeck inicia `launch.sh`, que confere o Python 3.10+ e executa `main.py`
  com os argumentos `-port -pluginUUID -registerEvent -info`.
- `main.py` só transporta: conecta ao OpenDeck, registra o plugin e entrega cada
  evento a `Runtime.handle`.
- O inspetor nunca fala com o UNO direto: pede ao plugin (`sendToPlugin` com
  `requestId`) e recebe a resposta (`sendToPropertyInspector`). Assim há uma só
  fila, um só lugar com o token e nenhum problema de CORS.
- O OpenDeck não deixa plugins criarem menus. Com `HasSettingsInterface` no
  manifest, ele mostra uma engrenagem no cartão do plugin em **Plugins** e manda
  `showSettingsInterface`; o plugin abre a própria página (`uno/localpage.py`) no
  navegador. É lá que fica o que vale para todas as teclas: idioma, conexão com o
  OBS, atraso das edições no ar, control apps registrados, gatilhos e grupos.

## Automações globais (2.0.0)

O OpenDeck só envia `willAppear` das teclas do **perfil selecionado** de cada
dispositivo **conectado** (`events/inbound/devices.rs`, `events/frontend/profiles.rs`).
Regras guardadas numa tecla paravam quando ela saía da tela. Por isso o que precisa
funcionar sempre fica nas **configurações globais**, que o plugin recebe ao iniciar
(`didReceiveGlobalSettings`):

| Chave global | Conteúdo | Quem escreve |
| --- | --- | --- |
| `controlApps` | `app_id → {token, name}`; `app_id` = 6 primeiros hex do SHA-256 do token | tecla que conecta, migração, página |
| `triggers` | lista de gatilhos (evento, cena, origem, função, `app`, overlay, atraso, ligado) | página, migração |
| `groups` | `nome → {delay, members: [{app, overlay}]}` | página; a tecla Overlay só entra ou sai |
| `clockConfigs`, `revealConfigs` | configuração da última tecla Clock/Reveal por `app::campo` | tecla ao aparecer |
| `language`, `liveEditDelay` | idioma escolhido, atraso das edições no ar | página |

- O token aparece uma vez, no registro; gatilhos, grupos e log usam só o `app_id`.
- `uno/automations.py` (puro) limpa, compara e migra; `runtime/automation.py` avalia
  eventos do OBS e do UNO, agenda com `run_later` (dono `automation`, que o Panic
  cancela) e registra cada decisão no log.
- Chaves em `OWNED` (`core.py`) só mudam pelo plugin: uma cópia antiga das configurações
  globais vinda de um inspetor não as desfaz.
- Migração da 1.0.0 (`adopt_key`): ao aparecer, uma tecla Overlay com campos antigos
  passa os gatilhos para a lista global (sem duplicar), entra no grupo e recebe
  `setSettings` sem esses campos.

## Idiomas

Catálogos `i18n/<código>.json`, estilo gettext: o texto em inglês é a chave; chaves
com `?` são as ajudas dos campos, e só elas ficam em `en.json`. `scripts/build_i18n.py`
acha todo texto marcado (`t()` e `data-t` no inspetor, `tr()` no Python, nomes do
manifest), falha se faltar ou sobrar chave e gera `pi/js/i18n.js` e os arquivos
`<idioma>.json` que o OpenDeck lê para a lista de ações. Ordem do idioma (`uno/i18n.py`):
escolha na página → `language` do `settings.json` do OpenDeck (`<pasta do plugin>/../../`,
pasta vinda de `UNO_PLUGIN_DIR`, que o `launch.sh` exporta) → o idioma do registro →
inglês. O manual em PDF usa as mesmas ajudas (`scripts/build_manual.py`).

## Camadas

Cada camada só importa as de baixo (imports absolutos, `from uno.x import …`).

| Camada | Módulos | Regra |
| --- | --- | --- |
| Regras puras | `values`, `jsonpath`, `clock`, `sources`, `files`, `backup`, `images`, `glyphs`, `automations`, `i18n`, `timeouts` (espera com prazo que não perde cancelamento) | sem rede e sem estado global; testáveis sozinhas (`tests/test_units.py`) |
| Adaptadores | `api` (App API), `datastore` (Socket.IO), `obs` (obs-websocket), `localpage` (página de configurações) | cada protocolo num arquivo, com a fonte do contrato no docstring |
| Funcionalidades | `runtime/*.py` (17 mixins) | uma razão para mudar por arquivo |
| Composição | `runtime/core.py` | recebe eventos, roteia, guarda o estado comum |
| Entrada | `main.py`, `launch.sh` | processo e transporte |

## Runtime

`Runtime` (em `core.py`) herda 17 mixins. Todos compartilham um objeto e um event
loop; cada mixin cria o próprio estado em `_init_<nome>()`, chamado no `__init__`.

| Módulo | Responsabilidade |
| --- | --- |
| `queue.py` | fila global: um job UNO por vez, prioridade para controle sobre leitura, agrupamento de giros |
| `automation.py` | registro de control apps, gatilhos globais (OBS e UNO), grupos globais, migração da 1.0.0, configurações guardadas de Clock e Reveal |
| `content.py` | cópia em tempo real do datastore por token, leituras, gravações e edições do inspetor (espera sem alterações quando no ar) |
| `rpc.py` | pedidos do inspetor (leituras, slots, prévias, status, backup, apagar log e cena) |
| `overlays.py` | mostrar/esconder, grupos, slots, Auto Close e badge |
| `numeric.py` | incrementos agrupados, atraso, limites, Undo, gráfico do ponto |
| `dials.py` | knobs: Slot Wheel (com carrossel), Dial Value, Shift |
| `reveal.py` | Reveal Answer: alternar, copiar a resposta, esconder ao trocar de slot |
| `keys.py` | imagens das teclas: glifo, tally, badge, Visor |
| `triggers.py` | OBS: conexão, cenas, Refresh Browser (lista ou cena inteira), `run_later` (função + alvo + atraso) |
| `settingspage.py` | página de configurações do plugin: idioma, OBS, atraso das edições, control apps, gatilhos e grupos |
| `scoreboard.py` | Lock, limites do modelo, histórico do Undo, Cycle, Swap, Reset |
| `clocks.py` | escreve um `Clock` (regras em `uno/clock.py`) por campo, a cada segundo |
| `datasources.py` | fontes de dados do vMix: mapeamento, Auto Next, Loop, observar arquivo |
| `derived.py` | campos calculados: Text Template, enquete, meta |
| `safety.py` | Lock Desk, 2º toque, Status, contador da App API, log |
| `showcontrol.py` | Macro, Panic, Restore, Scene |

Por que mixins e não objetos separados: as funcionalidades se cruzam no mesmo
estado (a Macro usa overlays, OBS, Scene e Timer; Panic cancela timers, macros e
Auto Next). Um objeto só evita repassar dependências entre 17 serviços; a
separação fica no arquivo, que é onde muda. As regras com lógica própria
ficaram em **módulos profundos** com interface pequena e testes diretos:
`Clock`, `Datastore`, a fila e `values`.

## Fila global

- Todo comando UNO, de qualquer dispositivo, tecla, knob ou inspetor, vira um
  `Job` numa de duas filas (`CONTROL` antes de `READ`), executado um por vez.
- Giros do mesmo campo somam-se no job que ainda espera, a menos que outro job do
  mesmo overlay tenha entrado depois (barreira por token + overlay): a ordem por
  overlay é preservada.
- O `Datastore` espera a próxima janela do `rateLimitInfo` recebido no login em
  vez de descartar gravações. Gravações não são repetidas depois de timeout.
- Só uma mudança real das configurações de uma tecla descarta os jobs dela ainda na
  fila. Sair da tela (`willDisappear`, troca de perfil) não descarta: o toque já feito
  executa, e o Auto Close segue até o fim.

## Inspetor (pi/)

Scripts clássicos, na ordem de `index.html`: `glyphs`, `i18n` (catálogos, gerado),
`lang` (`t()`, `helpText()`, idioma), `tips` (balões de ajuda **?**), `texts` (rótulos e
listas), `bridge` (WebSocket do OpenDeck e RPC), `data`,
`form-builder` (formulário do modelo UNO), `inspector` (núcleo e ajudantes de
formulário), depois um arquivo por área que estende `Inspector.prototype`
(`builders`, `overlay`, `obs`, `editors`, `definitions`, `status`, `pickers`) e
`main` (inicia). Sem framework e sem build: o OpenDeck serve os arquivos como estão.

`settings.html` + `js/settings.js` são a página de configurações do plugin, servida pelo
próprio plugin (`uno/localpage.py`), não pelo OpenDeck: nenhum script inline, porque a
página roda sob CSP `script-src 'self'`.

Regras: nada de `innerHTML`; todo controle com nome acessível (`label` ou
`aria-label`, conferido no teste do navegador) e com ajuda **?** ligada por
`aria-describedby` (WCAG 1.4.13: abre no hover e no foco, Esc fecha); todo texto
visível passa por `t()`; tema escuro com `color-scheme`.

## Convenções dentro de cada arquivo

1. Docstring do módulo: o que ele faz e a fonte (documentação ou código) que o define.
2. Imports: stdlib, terceiros, `uno` (isort via ruff).
3. `__all__` com a interface pública; o resto é interno.
4. Constantes, depois classes e funções públicas; quem chama fica acima de quem é chamado.
5. Comentários dizem **por quê** e citam a fonte; não repetem o código.
6. Erros para o usuário são `UnoError` com o próximo passo; `except Exception` só
   nas bordas (tarefas, conexões), anotado com o motivo.
7. Logs sem token, URL ou conteúdo de campo.

## Adicionar uma ação

1. `manifest.json`: nova entrada em `Actions` (UUID `dev.br.consciencia.opendeck.uno-overlays.<nome>`).
2. Ícone: nome do glifo em `scripts/build_icons.py` e rode o script.
3. Runtime: a regra no mixin da área (ou um novo `runtime/<área>.py` com `_init_<área>`), roteada em `core.py`.
4. Inspetor: `build<Nome>` no arquivo da área e a entrada em `BUILDERS` (`inspector.js`).
5. Textos: `t('…')` / `tr("…")` em todo texto novo, a ajuda `?<ação>` e `?<ação>.<campo>`
   em `i18n/en.json` e a tradução nos outros 8 catálogos; `scripts/build_i18n.py` aponta
   o que falta. O manual pega a ajuda sozinho.
6. Teste: um cenário em `tests/` com os emuladores de `tests/support.py`; o teste do
   navegador cobre o inspetor novo sozinho (lê as ações do manifest).
