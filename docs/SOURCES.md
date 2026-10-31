# Fontes e decisões — 28/09/2026

## UNO: documentação, comunidade e fonte fornecida

- [UNO App API com Companion](https://resources.overlays.uno/post/uno-app-api-companion-stream-deck): endpoint por control app, método PUT e comandos de consulta/escrita.
- [Slots via Companion](https://resources.overlays.uno/post/bitfocus-companion-uno-slots): GetOverlays, slots e operações Take.
- [Plugin oficial UNO v2](https://resources.overlays.uno/post/stream-deck-plugin-v2): consultado como referência atual; seu modo de confirmar valores por dial **não** substituiu a operação por tick do plugin fornecido.
- [Fórum oficial OBS, tópico do overlays.uno](https://obsproject.com/forum/threads/animated-browser-overlays-with-dockable-controls.161995/): referência comunitária e respostas do fornecedor sobre imagens via URL. Não foi usado para inventar comandos da API.
- Capturas do Control App anexadas: código de criação, seleção e atualização de slots em `index-tW8XhPhc.js.download`, incluindo `subCompPayloads`, `currentSlotId` e payload por preset.
- 14 fontes do plugin anexadas: `js/api.js`, `js/plugin.js`, manifests, inspetores, utilitários e deltas, documentados em EVOLUTION.md.

Foram feitas **somente leituras** na API de demonstração que a documentação
UNO publica para testes. GetOverlays retornou ids, nomes, visible e slots;
GetOverlayModel retornou model/groups; GetOverlayContent retornou o objeto de
campos. Não foram enviados Show/Hide/Set/Take para esse endpoint.

O artigo oficial contém exemplos com inconsistências editoriais (por exemplo,
o trecho de Hide All repete ShowAllOverlays). Para os corpos implementados,
prevaleceu o cliente funcional fornecido; as consultas foram confirmadas no
endpoint público. Não foi localizado um repositório oficial público do plugin
UNO que permitisse auditar seu backend proprietário. Essa ausência não foi
tratada como confirmação independente de cada comando.

## OpenDeck/OpenAction: contrato e código Git

- [Visão geral OpenAction](https://openaction.amankhanna.me/overview.html): diretório .sdPlugin, instâncias, persistência e inspetor.
- [Manifest OpenAction](https://openaction.amankhanna.me/manifest.html): CodePathLin, ícones e atributos de ações.
- [SDK WebSocket Elgato](https://docs.elgato.com/streamdeck/sdk/references/websocket/plugin/): eventos padrão compatíveis com OpenAction.
- [OpenDeck v2.9.1](https://github.com/nekename/OpenDeck/tree/5290d223ea20bb4cb76ef5c8221aa4eb844325cc) e [main consultado](https://github.com/nekename/OpenDeck/tree/7cc07942ef4a0d4d04d3011fac3f82626a211cfb). HEAD remoto foi conferido; main identifica a versão 2.14.0 no Cargo.toml.

| Decisão no port | Fonte no OpenDeck, commit 7cc07942 |
| --- | --- |
| Processo Python iniciado pelo launch.sh, UUID com sufixo .sdPlugin no registro | [plugins/mod.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/plugins/mod.rs) |
| Entrypoint connectOpenActionSocket e argumentos JSON string | [plugins/webserver.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/plugins/webserver.rs) |
| Save/getSettings e multiplicador em global settings | [inbound/settings.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/events/inbound/settings.rs), [outbound/settings.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/events/outbound/settings.rs) |
| RPC de leitura entre PI e plugin | [inbound/property_inspector.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/events/inbound/property_inspector.rs), outbound/property_inspector.rs |
| Separação Down/Up e ticks | [outbound/keypad.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/events/outbound/keypad.rs), outbound/encoder.rs |
| Display com setImage | [inbound/states.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/events/inbound/states.rs) e [rendererHelper.ts](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src/lib/rendererHelper.ts): SVG/data URI → canvas → JPEG para o driver |
| Keypad, Encoder e Infobar; sem presumir Information do StreamDock | [shared.rs](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/src-tauri/src/shared.rs), store/profiles.rs e components/DeviceView.svelte |
| ZIP com raiz .sdPlugin e restauração da execução de CodePathLin | [frontend/plugins.rs](https://github.com/nekename/OpenDeck/blob/5290d223ea20bb4cb76ef5c8221aa4eb844325cc/src-tauri/src/events/frontend/plugins.rs) e zip_extract.rs |

Não foi copiado código do OpenDeck nem dos drivers para este pacote. O plugin
usa seus contratos existentes. Locks, filas, tratamento de erro e testes são
código da adaptação, não trechos alegadamente publicados pela documentação.

## Build, dependências e Forgejo

- [websockets 15.0.1](https://github.com/python-websockets/websockets/tree/15.0.1): cliente/servidor asyncio; wheel puro, SHA-256 fixado em scripts/build.py, licença incluída.
- [urllib.request](https://docs.python.org/3/library/urllib.request.html), [asyncio](https://docs.python.org/3/library/asyncio.html): HTTPS, timeout, locks, tasks e cancelamento.
- [Forgejo Actions](https://forgejo.org/docs/latest/user/actions/) e [Codeberg Actions](https://docs.codeberg.org/ci/actions/): workflow por push/PR/manual e runner próprio.
- [checkout v4](https://data.forgejo.org/actions/checkout), commit `11d5960a326750d5838078e36cf38b85af677262`.

O padrão de pipeline e de dependência empacotada reutiliza o projeto Knob
Actions anterior. Não exige registry, credencial UNO nem segredos adicionais
para testar/gerar o plugin. Não executa alterações de overlays no CI.

## Correção 1.1.0: conteúdo persistido e eventos

As regras de sincronização da 1.1.0 substituem as decisões locais/sem polling
da primeira adaptação. A solicitação mais recente pede gravação no site e
Display atualizado; não basta preservar os erros da referência fixed6.

### Documentação pública consultada

- [API Description do exemplo oficial](https://app.overlays.uno/apiv2/controlapps/1bccBWBDKFWNSHEo8CdhSQ/api/info): consulta em 28/09/2026; documento UNO Essentials. Lista GetOverlayContent, SetOverlayContent, SetOverlayContentField e os comandos Take; **não lista uma operação de gravar slots**. Foi feita leitura, sem mutações no exemplo.
- [Update a control app's content](https://developer.singular.live/rest-api/api-reference/send-data-to-a-control-app/update-a-control-apps-content): diferença entre payload de uma instância e modelo/template. O port continua usando a UNO App API PUT que já funcionava; não troca arbitrariamente para outro host.
- [Metadados da instância](https://developer.singular.live/rest-api/api-reference/get-control-app-details/get-a-control-apps-metadata): identifica o Control App e sua URL de controle.
- [App SDK, publicação oficial Singular no CodePen](https://codepen.io/Singular/post/singular-app-sdk): API de `storage.set/update/get/on/off`, payload e eventos. Documento histórico de 2018; não é tratado como garantia do protocolo de rede atual.
- [App SDK, portal atual](https://developer.singular.live/software-development-kits/app-sdk): o acesso à documentação completa atual é solicitado ao fornecedor.
- [Boilerplate oficial no Git](https://github.com/singularlive/app-development-boilerplate/tree/6ca416f81d1dcffe93fc16ea5a182ad3bf11bbbd): conferido por clone; expõe `singularAppInit(app)`, mas não o backend de slots. Não foi alegado que esse repositório contém a implementação proprietária.
- [Engine.IO v4](https://socket.io/docs/v4/engine-io-protocol/) e [Socket.IO protocol v5](https://socket.io/docs/v4/socket-io-protocol/): handshake, namespace principal, eventos JSON, ping/pong e erros. O adaptador usa somente esse subconjunto sobre a dependência websockets existente, sem copiar uma biblioteca JS nova.

### Contrato conferido no código do cliente oficial fornecido

| Arquivo capturado | Evidência usada |
| --- | --- |
| `index-tW8XhPhc.js.download` | `storage.on("Slots")`, `storage.set("Slots", subCompSlots)`, lista `{active,currentSlotId,data:[{id,name,payload}]}` e separação entre editar um slot e colocá-lo no ar. |
| `controlapp.2990ba19.js.download` | `singularAppInstance.datastore`; inicialização do datastore com token; SDK storage e caminhos `compExtracts.*.compositions.*.dataSources.composition.controlNode.payload`. |
| `274.e57ec17d.js.download`, módulo 88534 | Host `datastore.singular.live`, Socket.IO WebSocket, `login(datastore, token)`, GET `/v1/{datastore}`, resposta `{data,v}`, eventos `set`/`update`, `userData.sender`, versão e `__group_update__`. |

SHA-256 dos três arquivos, para localizar exatamente a referência:

```text
009fbc4b2595c438bca00665d789b5676eaac3090f98d49776e271f4638122c1  274.e57ec17d.js.download
14a629013e16d50ace0d66136c08472145e05e004a4e1c3e13d785df5ee60b72  controlapp.2990ba19.js.download
f68d4baf3adb6d085797853a38b425c61b6aeadaf99ff40a7d9aefbd1f084bc4  index-tW8XhPhc.js.download
```

As capturas completas não são redistribuídas: podem conter informações privadas.
O adaptador Python é implementação própria desses contratos observados. Ele
não executa scripts baixados, não incorpora tokens e não inventa SetSlot/GetStorage
na API REST. O HTML do Control App é lido apenas para localizar seu datastore;
a conexão usa o token configurado pelo usuário no evento de login do fornecedor.

**Limite de evidência:** a referência de armazenamento é código oficial capturado,
não uma API pública com compromisso de estabilidade. A confirmação em loopback
valida o adaptador e os eventos emulados; não comprova aceitação da escrita pelo
serviço real. O acesso privado com token embutido no anexo foi bloqueado pela
revisão automática. Nenhuma tentativa de contornar esse bloqueio foi feita.

### Decisões específicas da correção

- A entrada do usuário vai ao backend imediatamente; o backend agrupa campos por
  400 ms, mantendo a gravação mesmo quando o inspetor fecha. Take aguarda a fila.
- A gravação de slot ocorre no caminho de seu payload, preservando campos não
  editados e outros slots. Conteúdo ao vivo usa `SetOverlayContent` e só é marcado
  como salvo após confirmação no snapshot/eventos.
- Display recebe eventos do mesmo datastore; não faz uma consulta HTTP periódica
  por botão. Não se confunde WebSocket push com AJAX polling.
- O ciclo Down/Up, transporte OpenAction, identidade de ações, formulários e
  pipeline Forgejo continuam reutilizados. Nenhuma modificação no OpenDeck/driver.
- Sem CAS documentado, não se promete proteção contra edição simultânea externa
  de um mesmo campo ou rearranjo concorrente de arrays de slots.

## Correção 1.1.1: protocolo de gravação do datastore

O site `app.overlays.uno` não pôde ser lido deste ambiente (bloqueado pela
política de rede e por robots.txt); nada foi obtido por arquivo/cópia de
terceiros. As capturas da 1.1.0 não estavam disponíveis. Por isso cada linha
nova segue código **publicado** e conferido localmente:

| Decisão | Fonte (arquivo e linha conferidos) |
| --- | --- |
| `login` com ack; gravação só após o ack; ler `rateLimitInfo.maxBytesPerMin/maxRequestsPerSec` | [singular-datastore 1.0.1](https://www.npmjs.com/package/singular-datastore), cliente oficial publicado pela conta npm `singularlive` (hello@singular.live), `index.js` l. 919–920 |
| `update` = `{data, userData: {sender: socket.id}}` com ack | idem, l. 941 |
| Mensagens de limite "Rate limit exceeded. N requests per second / bytes per minute" e janela de contagem | idem, `createRateLimiter` l. 842 e l. 949 |
| Aplicar `update` com caminhos pontuados; metadados opcionais | idem, `updateJsonObject` l. 821 e `socket.on('update')` l. 887–905 |
| `set` não é aplicado pelo cliente oficial → o plugin relê o snapshot | idem, `socket.on('set')` l. 883 (apenas `console.log`) |
| Snapshot `GET https://datastore.singular.live/v1/{id}` → `.data` | idem, l. 1008–1010 (já usado na 1.1.0) |
| Formato de pacote com id de ack (`42<id>[...]`, `43<id>[...]`) | [socket.io-parser 4.2.7](https://www.npmjs.com/package/socket.io-parser/v/4.2.7) (repositório socketio/socket.io) `encodeAsString`/`decodeString`; decodificação comparada com o JS oficial em Node 22 |
| Servidor só entrega callback quando o pacote tem id | [socket.io 4.8.4](https://www.npmjs.com/package/socket.io/v/4.8.4) `dist/socket.js` l. 453 |
| Cliente numera acks a partir de 0 | socket.io-client 4.8.1 `build/cjs/socket.js` l. 264 |
| `maxPayload` no handshake; mensagem maior fecha o WebSocket | engine.io 6.6.11 `build/server.js` l. 51 e l. 488, `build/socket.js` l. 82 |
| Tipos Engine.IO 0–6 | engine.io-parser 5.2.3 `build/cjs/commons.js` |
| Local do log do plugin | [README do OpenDeck](https://github.com/nekename/OpenDeck/blob/7cc07942ef4a0d4d04d3011fac3f82626a211cfb/README.md) e `src-tauri/src/plugins/mod.rs` l. 320 (stdout/stderr → `logs/plugins/<uuid>.log`) |
| `SetOverlayContent` confirmado por `status: 200` | [UNO App API com Companion](https://resources.overlays.uno/post/uno-app-api-companion-stream-deck) ("All responses include status 200") |

SHA-256 dos pacotes npm conferidos:

```text
fa0dbb8f05b9bd4552f05ea497747f7edab67adba78caecd8cacdb5d240a81be  singular-datastore-1.0.1.tgz
658d1c43c50daa829b1d277a640c91af01f5befd589ff6b88b1f0655069d81e8  singular-datastore-1.0.1/package/index.js
9efbb5f34afcec1430e7e93e16ced958c15377793d37ab69835f8d987a2b1fe9  socket.io-parser-4.2.7.tgz
eac2f8dd36bd1ddc827407c6890cc9fa305e5f94038b9abdba98a4351934c6c2  socket.io-4.8.4.tgz
e39a4baa07488a5cfe10de424bc8646ed897f5dbd318312a852ff74570e47e01  socket.io-client-4.8.1.tgz
963b811ee84cf1539ce4d90ed56c50a8a93d1a34f3e68b684600125588969da7  engine.io-6.6.11.tgz
fc00b90d41fd11b6c0473de006c2f845cc100704f6363c72e24b7d4b79b15566  engine.io-parser-5.2.3.tgz
```

Nenhum desses pacotes é redistribuído; o plugin continua usando apenas
`websockets` 15.0.1. Mantidos da 1.1.0 (evidência das capturas UNO): leitura do
`datastore` na página do Control App, parâmetro `ds`, caminhos `storage.Slots`
e o tratamento de `__group_update__`/`v`.

Decisões próprias, não impostas pelas fontes: quando o limite de requisições
por segundo é atingido o plugin **espera** a janela seguinte (o cliente oficial
rejeitaria); o limite por minuto continua rejeitando com a mensagem oficial.
Após o ack, aguarda o broadcast por 3 s e, sem ele, relê o snapshot.

## Correção 1.1.2

| Decisão | Fonte |
| --- | --- |
| Aplicar todo `update`; sem `v`/`__group_update__`; ordem das chaves | singular-datastore 1.0.1 `index.js` l. 887–905 (`Object.entries(msg)` + `updateJsonObject`) |
| Semântica não estrita (atribuição a primitivo é ignorada; buracos de array) | mesmo arquivo: não contém `"use strict"`; `updateJsonObject` l. 821 |
| Snapshot lido só na conexão | idem l. 1008–1012 (`fetch` antes de `connect`) |
| `set` só registrado | idem l. 883 |
| Ack conclui a gravação | idem l. 941–943 (`resolve(response)`) |
| Erro de listener fecha a conexão no cliente oficial | socket.io-client 4.8.1 `manager.js` l. 230–236 (`onclose("parse error")`); o plugin pula o caminho e registra, sem reconectar |
| Inspetor aberto/fechado | OpenDeck `events/frontend/property_inspector.rs` (`propertyInspectorDidAppear/Disappear`); fila de mensagens sem limpeza em `events/mod.rs` |
| Teto diário REST | [plugin UNO v2](https://resources.overlays.uno/post/stream-deck-plugin-v2): "10,000-call daily cap" |

Decisões próprias: fila global única (pedido do usuário), prioridade de
controles sobre leituras, agrupamento de ticks com barreira por overlay, espera
nos limites, e guardar localmente valores aceitos sem broadcast em 1,5 s.

## 1.2.0 (Fase 1)

| Decisão | Fonte |
| --- | --- |
| Ícones = Material Symbols Outlined, cor por `fill`/CSS | google/material-design-icons, commit bd8cb85b, `variablefont/` (Apache-2.0); geração em `scripts/build_icons.py` |
| SVG como imagem de tecla | OpenDeck `src/lib/rendererHelper.ts`: data URI SVG → `<img>` → canvas 144 px |
| `.svg` nos ícones do manifest | OpenDeck `src-tauri/src/shared.rs` `convert_icon` (prefere `.svg`) |
| Tamanho real das teclas Vision 01 (85–95 px, JPEG) | 4ndv/opendeck-akp153 `src/mappings.rs` `get_image_format_for_key` |
| Badge: "small, filled oval containing a number" | Apple HIG, Notifications → Badges |
| Vermelho do badge R255 G66 B69 | Apple HIG, Color → system colors, Red iOS default (dark) |
| Tally por `compositionStates` = `In` | singular-datastore 1.0.1 `getControl()` e Singular REST "Get a control app's control data" (`state`: In, Out1, Out2) |
| Next/Previous Slot | [uno + Companion Slots](https://resources.overlays.uno/post/bitfocus-companion-uno-slots): TakeOverlayNextSlot/PreviousSlot |
| Dial Value: clicar edita, girar escolhe, clicar envia, segurar 2 s cancela | [plugin uno Stream Deck v2](https://resources.overlays.uno/post/stream-deck-plugin-v2) |
| Slot Wheel: girar escolhe, clicar executa | mesmo artigo: "Action Wheel" |
| dialDown/dialUp separados | OpenDeck `events/outbound/encoder.rs` `dial_press` |
| Timer `{UTC, isRunning, value}`, play/pause/reset/start | singular-datastore 1.0.1 `processPayloadCommand()`; tipo `timecontrol` em `checkDataType()`; ações "Play/Pause/Reset timer" no [artigo do plugin uno](https://resources.overlays.uno/post/using-the-uno-stream-deck-plugin) |
| OBS: Hello/Identify/auth SHA256, Request/Response, eventos, porta 4455, bits Scenes/Outputs | obsproject/obs-websocket commit 1f37e617, `docs/generated/protocol.md` e README |
| Recarregar Browser Source: `PressInputPropertiesButton` + `refreshnocache`; tipo `browser_source` | protocol.md e obsproject/obs-browser commit a1624431 `obs-browser-plugin.cpp` (l. 221, 439) |
| Gatilhos OBS: evento → função (Show/Hide) + atraso até 30 000 ms | [vMix Triggers](https://www.vmix.com/help28/Triggers.html): OnTransitionIn/Out, Function, Delay (máx. 30 s) |
| Revisão de código | DietrichGebert/ponytail commit e3ba2aa6 (MIT): skills `ponytail`, `ponytail-audit`, `ponytail-review` |

Decisões próprias: canal numérico (1–6) liga knob e Visor; o Visor também serve aos
botões sem tela; a opção Play/Pause combina os comandos oficiais `play` e `pause`.

## 1.3.0 (Fase 2)

| Decisão | Fonte |
| --- | --- |
| Macro: passos em ordem, cada um aguarda o anterior; Wait atrasa os seguintes | [Companion 4.2 — Actions](https://companion.free/user-guide/v4.2/config/buttons/creating/actions/) (Sequential, internal: Wait); bitfocus/companion commit 94c24d58 `companion/lib/Internal/BuildingBlocks.ts` (Action Group, `wait`) |
| Panic cancela execuções e atrasos | mesmo commit, `companion/lib/Internal/Controls.ts`: ação `panic` "Actions: Abort all button and trigger runs" |
| Grupo exclusivo: ao entrar um, os outros do grupo saem; tempo custom < 0 atrasa a saída, > 0 atrasa a entrada | singular-datastore 1.0.1 `computeLogicLayerCompositionStates()` e bloco `delayMode` em `putControl()` |
| Gatilhos ao entrar/sair do ar, com Function, alvo e Delay até 30 000 ms | [vMix Triggers](https://www.vmix.com/help28/Triggers.html): OnOverlayIn / OnOverlayOut |
| Estado no ar = `compositionStates` = `In` | já documentado na 1.2.0 |
| Cena: Store (nomear e salvar), Recall (aplicar), Recall safe (não altera itens marcados) | [Yamaha — Using scene memory](https://hub.yamaha.com/proaudio/livesound/using-scene-memory) |
| Restore, Shift e "edições no ar" | decisões próprias, sem software de referência |

Com a fila global, a Macro implementa só o modo *Sequential* do Companion (o
*Concurrent* dispararia chamadas UNO em paralelo). O nome da unidade do tempo do
grupo (segundos) é escolha do plugin; o código oficial não fixa a unidade.

## 1.4.0 (Fase 3)

| Decisão | Fonte |
| --- | --- |
| Funções do Clock | [vMix Shortcut Function Reference](https://www.vmix.com/help28/ShortcutFunctionReference.html): PauseCountdown "Pause or Resume Countdown or if complete, Start from beginning."; SuspendCountdown "Pause Countdown Only"; StopCountdown "Stop and Reset Countdown"; SetCountdown "Set countdown duration according to Value as hh:mm:ss (00:00:00)"; ChangeCountdown "Change countdown time according to Value as hh:mm:ss (00:00:00)"; AdjustCountdown "Seconds to add or subtract from current Countdown time". StartCountdown aparece sem descrição |
| Ao completar: Function + Delay até 30 000 ms | [vMix Triggers](https://www.vmix.com/help28/Triggers.html): OnCountdownCompleted "when a configured countdown clock reaches 0" |
| Aparências Countdown, Count up, Time of Day; Until Finish Time ("The duration is calculated when the timer starts"); wrap-up amarelo/vermelho; overtime "Continue/Stop counting past 0:00", prefixo +0:01/−0:01; Flash 1, 2, 3 ou ∞ "until the timer stops"; formatos 230:59 (mmm:ss), 41:30:59 (hhh:mm:ss), 92 (seconds only) | [stagetimer — Using Timers Correctly](https://stagetimer.io/docs/timers/) |
| Time of day roda sem controle | [stagetimer — Time of Day element](https://stagetimer.io/docs/output-elements/time-of-day/): "You don't need to control anything from the Controller" |
| Cores do wrap-up: normal #22C55D, amarelo #F59E0C, vermelho #EF4444 | [stagetimer — Progress Bar element](https://stagetimer.io/docs/output-elements/progress-bar/) (valores como publicados) |
| min/max do modelo (máximo, depois mínimo; vazio ignorado) e resetValue | singular-datastore 1.0.1 `index.js` `processPayloadCommand()`, l. 426–458 |
| Campos do modelo em `controlNode.model.fields` | mesmo trecho (`Object.entries(model.fields)`) |

Decisões próprias (sem software de referência): Undo (50 últimas, só na memória),
Lock, Swap Sides, Cycle (períodos e posse), Reset segurando 2 s com 0/vazio quando
não há resetValue, passo fixo, limites próprios da tecla, gráfico após ponto, pausar
fora do ar, knob do Clock (girar = AdjustCountdown com passo de 10 s), comportamento do
StartCountdown, piscar também na tecla, formato do Time of day (HH:MM ou HH:MM:SS
pelo relógio local) e gravação do Clock direto no datastore fora da fila de teclas.
Não implementado do stagetimer: formato d:hh:mm:ss, flash nos pontos amarelo/vermelho,
som (chimes).

## 1.5.0 (Fase 4)

| Decisão | Fonte |
| --- | --- |
| Selecionar uma linha atualiza os campos; Auto Next com "number of seconds between each row"; Loop "jump to the start of the list after the last row"; DataSourceNextRow, DataSourcePreviousRow, DataSourceSelectRow; "all Data Sources automatically update" | [vMix — Controlling Data Sources](https://www.vmix.com/help28/DataSourcesControl.html) |
| Tipos Text ("Select any text file") e Excel/CSV, "Use first row as column names" | [vMix — Types of Data Sources](https://www.vmix.com/help24/DataSourcesTypes.html) |
| Column *Auto*: coluna com o mesmo nome do campo, senão o índice do campo; *Row* "Selected"; *Format* "'Name: {0}' will output the data as 'Name: Gary'" | [vMix — Mapping a Data Source to a Title](https://www.vmix.com/help28/DataSourcesTitleMapping.html) |
| Meta: Title, Goal Amount, Starting Amount, End After; "An existing goal cannot be edited"; a barra "fill up and show the current total" | [Streamlabs — How to Set up the Streamlabs Tip Goal Widget](https://support.streamlabs.com/hc/en-us/articles/360052472373-How-to-Set-up-the-Streamlabs-Tip-Goal-Widget) |
| Inspetor grava configurações globais → plugin recebe; plugin grava → todos os inspetores recebem | OpenDeck commit 7cc0794, `src-tauri/src/events/inbound/settings.rs` (`set_global_settings`) e `outbound/settings.rs` |
| Leitura de CSV | Python `csv.reader` (biblioteca padrão), arquivo UTF-8 com ou sem BOM |

Decisões próprias: opção "tocar de novo soma o Auto Close" (pedido do Marcos); lista
digitada como tipo de fonte; em .txt/lista, cada linha não vazia é uma linha da fonte
(sem espaços nas pontas); escolha do separador do CSV; *Auto* compara com o id e com
o título do campo UNO; `{Coluna}` no Format e a tecla Text Template com
`{Overlay::Campo}` (modelos pedidos pelo Marcos); Next sem seleção = linha 1; Auto Next
grava a linha 1 se nada estiver selecionado e para na última linha sem Loop; Loop só
de frente (Previous não dá a volta); linha selecionada só na memória; checagem do
arquivo a cada 1 s; enquete inteira (percentual inteiro arredondando .5 para cima, 0
sem votos); *End After* com data e hora; percentual da meta sem teto; gatilho de meta
atingida; Panic desliga o Auto Next; votos e somas passam por Lock/Undo.

## 1.6.0 (Fase 5)

| Decisão | Fonte |
| --- | --- |
| Travar após N s sem uso ("Pin Timeout (seconds, 0 to turn off)"), travar todos juntos ("Link Lockouts"), travar por ação | Companion commit 94c24d58, `docs/user-guide/3_config/settings.md` (PIN lockout) |
| Status "All": erro se alguma conexão tem erro, senão aviso, senão OK; cores padrão OK #FFFFFF/#00C800, aviso #000000/#FFFF00, erro #FFFFFF/#C80000, desligado #999999/#404040 | Companion `companion/lib/Internal/Instance.ts` (`instance_status`, `executeFeedback`) |
| *connecting* e *disconnected* contam como erro | Companion `companion/lib/Instance/Status.ts` (`updateInstanceStatus`) |
| Limite diário de 10 000 chamadas no plano gratuito | [uno — Stream Deck plugin v2](https://resources.overlays.uno/post/stream-deck-plugin-v2): "free users who have a 10,000-call daily cap" |
| OBS GetVersion: obsVersion, obsWebSocketVersion | obs-websocket `docs/generated/protocol.md` |
| Copiar/colar teclas já existe | OpenDeck commit 7cc0794, `src/components/Key.svelte` (Copy/Paste, Ctrl+C/Ctrl+V) e `DeviceView.svelte` (`move_instance` com `retain`) |

Decisões próprias: confirmação com 2º toque (opções 2/3/5/10 s, tecla piscando);
destravar segurando 2 s no lugar do PIN (pedido do Marcos); travamento só na
memória; aviso a partir de 90% do limite; dia local no contador (o UNO não documenta a
virada) e contagem de toda requisição enviada, mesmo as que falham; nome da control
app pelo SHA-256 do token; log de 200 linhas; busca, favoritos e backup (JSON com
permissão 600, segredos opcionais, tokens completados na importação).

## 1.0.0 (versão profissional)

| Decisão | Fonte |
| --- | --- |
| Versão `MAJOR.MINOR.PATCH`: o OpenDeck compara versões de plugins com `semver::Version::parse` | OpenDeck commit 7cc07942, `src-tauri/src/plugins/mod.rs` |
| Instalar por arquivo substitui a pasta do plugin e reinicia o processo; teclas e configurações ficam | OpenDeck, `src-tauri/src/events/frontend/plugins.rs` (`install_plugin`: `deactivate_plugin`, extração, `initialise_plugin`) |
| Menus citados: **Plugins → Install from file**, **Settings → Contribute statistics** | OpenDeck `translations/en.json` e `pt_BR.json` |
| O OpenDeck coleta estatísticas mínimas por padrão | OpenDeck `src-tauri/src/main.rs` ("minimal statistics (such as operating system and plugins installed)") e `store/mod.rs` (`statistics: true`) |
| Portas 57116/57118 em `0.0.0.0`, sem autenticação no registro, arquivos da pasta de configuração com `Access-Control-Allow-Origin: *` | OpenDeck `src-tauri/src/plugins/mod.rs`, `plugins/webserver.rs`, `events/mod.rs` |
| Eventos dos testes: `GenericInstancePayload`, `DialRotatePayload`, `DialPressPayload` | OpenDeck `src-tauri/src/events/outbound/mod.rs`, `encoder.rs`, `will_appear.rs`, `keypad.rs` |
| `websockets` vendorizado = wheel oficial 15.0.1 (SHA-256 `f7a866fb…`) | PyPI; comparação byte a byte em `scripts/build.py` |
| CI: `runs-on`, `container`, URLs completas de actions | [Forgejo Actions reference](https://forgejo.org/docs/latest/user/actions/reference/) |
| `within` em vez de `asyncio.wait_for`: no 3.10/3.11 o `wait_for` pode engolir o cancelamento quando o resultado chega junto; corrigido no 3.12 | [CPython gh-86296](https://github.com/python/cpython/issues/86296) ("fixed in 3.12 by gh-96764", sem backport para 3.11); código de `asyncio/tasks.py` do 3.11 e do 3.12; travamento reproduzido aqui no 3.11 e no CI (Debian 12, Python 3.11.2) |
| Build reprodutível com `SOURCE_DATE_EPOCH` | [reproducible-builds.org](https://reproducible-builds.org/specs/source-date-epoch/) |
| LGPD: Art. 4º, 5º, 6º, 16, 18, 33, 46, 48; Res. CD/ANPD 15/2024 (três dias úteis) | Lei 13.709/2018 (texto do Planalto conferido pela cópia em manfredjr/legal-br @ `583853a8`) |
| Skills de estrutura, segurança, LGPD, usabilidade, testes e documentação | [SKILLS.md](SKILLS.md) |
| Plugins não criam menus: o menu nativo é só o da bandeja, com itens fixos (Show, Hide, Restart, Quit) | OpenDeck `src-tauri/src/main.rs` (`MenuBuilder`, `TrayIconBuilder`) |
| `HasSettingsInterface`: "Whether the plugin has its own GUI that the user can request to be shown through the OpenAction server" | [OpenAction manifest](https://openaction.amankhanna.me/manifest.html); OpenDeck `plugins/manifest.rs` |
| A engrenagem (aria-label "Settings"/"Configurações") envia `{"event": "showSettingsInterface"}` ao plugin | OpenDeck `src/components/PluginManager.svelte`, `events/frontend/plugins.rs`, `events/outbound/settings.rs`; traduções `plugin_manager.plugin_settings` |
| Disponível desde o OpenDeck 2.6.0 | commit `c945d19` (2025-08-18, "feat: display settings interfaces for supported plugins"), primeira tag que o contém: v2.6.0 |
| `setGlobalSettings` do plugin grava e avisa todos os inspetores (não o próprio plugin) | OpenDeck `events/inbound/settings.rs`, `events/outbound/settings.rs` |
| Abrir no navegador padrão: `webbrowser.open` (usa `xdg-open` quando existe) | código do Python 3.10, `Lib/webbrowser.py` (`register_X_browsers`) |
| Servidor da página: `http.server.ThreadingHTTPServer` (threads daemon), `handle_request` com `timeout` | código do Python 3.10, `Lib/http/server.py`, `Lib/socketserver.py` |
| Workflow: `on: push` com tags, `startsWith`, `github.ref`, variáveis `GITHUB_SERVER_URL`, `GITHUB_REPOSITORY`, `GITHUB_REF_NAME`, `FORGEJO_TOKEN`/`GITHUB_TOKEN` | [Forgejo Actions reference](https://forgejo.org/docs/latest/user/actions/reference/) |
| Token automático: escrita no próprio repositório (não em forks); pacotes exigiriam token pessoal | Forgejo Actions reference ("the automatic token has write permission to the repository"); [Codeberg Community #1735](https://codeberg.org/Codeberg/Community/issues/1735); [forgejo #3571](https://codeberg.org/forgejo/forgejo/issues/3571); Gitea 1.21 `routers/api/v1/api.go` (`repoAssignment`: token de Actions = escrita em todas as unidades, leitura em PR de fork) |
| Releases: `/repos/{owner}/{repo}/releases` e `/releases/{id}/assets` | [Forgejo: Tags and Releases](https://forgejo.org/docs/latest/user/releases/) |
| `DELETE /releases/tags/{tag}` (204/404, mantém a tag git), anexo no campo `attachment` com `?name=`, `DELETE /repos/{owner}/{repo}`, `POST /user/repos` / `/orgs/{org}/repos`, `PATCH` com `has_actions`/`has_releases` | especificação da API do Gitea 1.21 (base do fork do Forgejo): `templates/swagger/v1_json.tmpl`, `routers/api/v1/repo/release_tags.go`, `release_attachment.go`. A especificação do próprio Forgejo (`/api/swagger`) não pôde ser lida deste ambiente (robots.txt) |
| Apagar o repositório remove releases e anexos, execuções/tarefas/logs/artefatos do Actions, runners e segredos do repositório | Gitea 1.21 `services/repository/delete.go` |
| Escopos do token: `write:repository` e `write:user` para criar/apagar | [Forgejo: token scopes](https://forgejo.org/docs/latest/user/token-scope/); Gitea 1.21 `api.go` (`/user` exige categoria user; `/user/repos` também repository) |
| Token lido e salvo pelo credential helper (`git credential fill`/`approve`); helper `store` grava em texto puro | [git-credential](https://git-scm.com/docs/git-credential), [git-credential-store](https://git-scm.com/docs/git-credential-store) |
| User-Agent próprio: o Cloudflare na frente de forgejo.consciencia.dev.br respondeu 403, erro 1010, ao User-Agent padrão do Python e aceitou outro | resposta do próprio servidor (teste do Marcos em 30/09/2026); [Cloudflare error 1010](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/) |
| Git por HTTPS com o token como senha Basic; header `Authorization: token` na API | Gitea 1.21 `services/auth/basic.go`; [Forgejo: API usage](https://forgejo.org/docs/latest/user/api-usage/) |

## 2.0.0 (automações globais, idiomas, manual)

| Decisão | Fonte |
| --- | --- |
| O OpenDeck só envia `willAppear` das teclas do perfil selecionado de cada dispositivo conectado; trocar de perfil manda `willDisappear` | OpenDeck 2.14.0, commit `7cc0794`: `src-tauri/src/events/inbound/devices.rs`, `events/frontend/profiles.rs` |
| Apagar uma tecla também manda `willDisappear` (o plugin não distingue de "saiu da tela") | `src-tauri/src/events/frontend/instances.rs` |
| `getSettings` exige o contexto da tecla, que só chega no `willAppear`: por isso as regras vão para as configurações globais (`didReceiveGlobalSettings` ao iniciar) | `store/profiles.rs` (`get_slot`), `events/inbound/settings.rs` |
| Nomes das ações por idioma: `<idioma>.json` na pasta do plugin, `Name` e `Tooltip` por UUID, `Name` do plugin | `src-tauri/src/events/frontend/mod.rs` (`get_localisations`), `src/components/ActionList.svelte`, `PluginManager.svelte` |
| Idiomas do OpenDeck: `de`, `en`, `es`, `fr`, `pt_BR`, `sv`, `uk`, `zh_CN`, `ja`, `ko` (sem italiano) | `src/components/SettingsView.svelte` |
| Idioma escolhido fica em `language` do `settings.json` da pasta de configuração (padrão `"en"`) | `src-tauri/src/store/mod.rs` (`Settings.language`, `config_dir().join("settings.json")`) |
| O registro só repassa `en`, `es`, `zh_CN`, `fr`, `de`, `ja`, `ko`; os outros chegam como `en`: o plugin lê o `settings.json` primeiro | `src-tauri/src/plugins/info_param.rs` |
| Mudar o idioma no OpenDeck não avisa o plugin: ele relê ao abrir inspetor ou página | `src-tauri/src/events/frontend/settings.rs` (`set_settings`) |
| Ajuda **?** como a do OpenDeck (ícone `Question` com balão) | `src/components/Tooltip.svelte` |
| Balão que abre no hover e no foco, fica sob o ponteiro e fecha com Esc | [WCAG 2.2, 1.4.13 Content on Hover or Focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html); skill addyosmani `accessibility` |
| Refresh de várias fontes: `PressInputPropertiesButton` com `refreshnocache`; `GetInputList` com `inputKind: browser_source`; cena inteira com `GetSceneItemList` e `GetGroupSceneItemList` (`sourceName`, `inputKind`, `isGroup`) | obs-websocket 5, `docs/generated/protocol.md` (o protocolo só diz `Array<Object>`); campos de cada item no código do obs-websocket, `src/utils/Obs_ArrayHelper.cpp` (iguais desde a 5.0.0). **Não conferido num OBS real** |
| Ícone do Numeric Fields desenhado como texto: o Material Symbols só tem `exposure_plus_1/2` e `exposure_neg_1/2` | arquivo de codepoints do Material Symbols (fonte mestre) |
| Carrossel: giros somados num `TakeOverlaySlotNumber` (já usado pela Macro) com intervalo mínimo de 0,3 s, por causa do HTTP 429 visto em 01/10/2026 | App API do UNO (comandos já usados desde a 1.0.0); erro 429 registrado em `uno-overlays-erros.md` |
| Gatilhos globais continuam no modelo do vMix (evento → função, atraso até 30 000 ms, `OnOverlayIn/Out`) | [vMix Triggers](https://www.vmix.com/help28/Triggers.html), as mesmas linhas acima |
| Versão 2.0.0: opção removida e configurações movidas da tecla para o global | [SemVer 2.0.0](https://semver.org/lang/pt-BR/), item 8 (mudança incompatível → MAJOR) |
| Manual: WeasyPrint 57.2, `fonts-noto-cjk`, `fonts-dejavu-core` e `fontconfig` do Debian 12; CVEs abertos da 57.2 | Debian Package Tracker e Debian Security Tracker (`weasyprint`), consultados em 01/10/2026 |
| Sumário com número de página (`target-counter`), marcadores (`bookmark-level`), links internos | [WeasyPrint 57 docs](https://doc.courtbouillon.org/weasyprint/v57.2/) |
| A imagem do CI (`node:22-bookworm-slim`) não tem `make`: entra no `apt-get install` | [nodejs/docker-node `22/bookworm-slim/Dockerfile`](https://github.com/nodejs/docker-node/blob/main/22/bookworm-slim/Dockerfile) (só `ca-certificates curl wget gnupg dirmngr xz-utils libatomic1`, removidos depois) |
| Publicação por cima do histórico, tag movida só com `--force-with-lease` | [git-push `--force-with-lease`](https://git-scm.com/docs/git-push); `GET /repos/{owner}/{repo}/releases/tags/{tag}` e `GET .../tags/{tag}` da API do Gitea 1.21 |

## GitHub Actions (31/10/2026)

| Decisão | Fonte |
| --- | --- |
| O Forgejo só lê `.github/workflows` quando não existe `.forgejo/workflows`: os dois workflows convivem e cada forja roda o seu | [Forgejo Actions: overview](https://forgejo.org/docs/latest/user/actions/overview/) ("In the absence of a .forgejo/workflows directory, workflows will be looked up in the .github/workflows directory") |
| Sintaxe: `on.push.tags`, `permissions`, `concurrency`, `container`, `timeout-minutes` | [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| `GITHUB_TOKEN` não vai para o ambiente sozinho: passado por `${{ secrets.GITHUB_TOKEN }}` só no passo da release; `permissions` no job eleva um padrão restrito; sem o que não foi listado, só `metadata: read` | [About the GITHUB_TOKEN](https://docs.github.com/actions/security-guides/automatic-token-authentication) |
| `actions/checkout` v6.1.0 = commit `d23441a48e516b6c34aea4fa41551a30e30af803`, `runs.using: node24` | `git ls-remote --tags https://github.com/actions/checkout` e `action.yml` desse commit, conferidos em 31/10/2026 |
| Releases: `POST /repos/{owner}/{repo}/releases` (201, `draft`), `GET .../releases` (rascunhos só para quem tem push), `PATCH`/`DELETE .../releases/{id}`; permissão `contents: write` | [REST API: releases](https://docs.github.com/en/rest/releases/releases) |
| Anexo: `upload_url` (hipermídia, `{?name,label}`) com `?name=`, corpo binário e `Content-Type` do arquivo | [REST API: release assets](https://docs.github.com/en/rest/releases/assets) |
| Commit da tag: `GET /repos/{owner}/{repo}/git/ref/tags/{tag}`; tag anotada (`object.type = "tag"`) seguida por `GET .../git/tags/{sha}` | [REST API: git references](https://docs.github.com/en/rest/git/refs), [git tags](https://docs.github.com/en/rest/git/tags) |
| Rascunho → anexos → publicar: com releases imutáveis, anexos são recusados depois de publicar; tag e anexos ficam travados | [Immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases); `gh release create` ("create the release as a draft, upload the assets, and then publish") |
| Push de `.github/workflows` exige token com permissão de workflow (`workflow` no clássico; *Workflows: Read and write* no fine-grained) | mensagem do GitHub "refusing to allow a Personal Access Token to create or update workflow ... without `workflow` scope" (relatos públicos em armbian/ci #45 e archlinux-docker #50) |
| Auditoria do workflow: `actionlint` 1.7.12 sem achados; `zizmor` 1.31.1 só aponta a imagem sem digest (a mesma do Forgejo, mantida de propósito) | execução local em 31/10/2026 |
