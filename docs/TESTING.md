# Testes

```sh
make check        # tools + lint + testes Python + teste do inspetor + manual
make test         # só Python (unittest), ~4 min
make test-pi      # só o inspetor no Chromium
UNO_TEST_LOG=1 make test   # mostra os avisos do plugin durante os testes
```

Requisitos: Python 3.10+ (suíte conferida em 3.10, 3.11, 3.12 e 3.13), `pyflakes` (Debian: `python3-pyflakes`), Node.js (testado no 22)
e, para o manual, `weasyprint`, `fontconfig`, `fonts-dejavu-core` e `fonts-noto-cjk` (apt). Sem o WeasyPrint, os testes
do PDF são pulados com aviso e `make tools` diz o que falta.
Opcionais: `ruff` (regras em `pyproject.toml`) e Playwright com Chromium para o
teste do inspetor, que é pulado com aviso quando o Playwright não está instalado
(`npm install -g playwright` e `npx playwright install chromium`, ou
`CHROMIUM_PATH=/caminho/do/chrome`).

Nenhum teste usa a conta UNO, tokens reais, o OBS real ou dados de pessoas: tudo
roda contra emuladores locais com nomes fictícios.

## O que cada arquivo cobre

| Arquivo | Tipo | Cobre |
| --- | --- | --- |
| `tests/test_units.py` | puro | decodificação Socket.IO, `updateJsonObject`, timecontrol, autenticação do OBS, validação do token, valores e formatos, regras do `Clock`, mapeamento e linhas das fontes, arquivos (caminho, tamanho, UTF-8, 600, link simbólico), backup, `within` não perde um cancelamento que chega junto com o resultado (gh-86296) |
| `tests/test_datastore.py` | loopback | login e update com ack, slots (add, rename, remove), `set` só registrado, `maxPayload`, limite de taxa, login sem `rateLimitInfo`, queda antes do ack, ack sem broadcast, ping/pong, formatos de update e snapshot atrasado |
| `tests/test_queue.py` | loopback | 5 controles em 2 dispositivos, giros agrupados, 3 gravações/s, ordem com toggle no meio, Delay; reconfigurar a tecla descarta, sair da tela não |
| `tests/test_keys.py` | loopback | ícone, tally, badge e Auto Close, Next/Previous Slot, Slot Wheel + Visor, Dial Value, Timer |
| `tests/test_obs.py` | loopback | autenticação, listas, tecla de cena, proteção por cena, Refresh Browser |
| `tests/test_global.py` | loopback | gatilhos globais sem nenhuma tecla na tela e o log de cada passo; migração da 1.0.0 uma vez só, com `setSettings` sem os campos antigos; encadeamento e grupo globais com a tecla em outro dispositivo e fora da tela; Auto Close e toque na fila sobrevivem à troca de perfil; registro de control apps em Status, Panic e Restore; Cycle zera um Clock fora da tela; Shift no dispositivo A e knob no B |
| `tests/test_multi.py` | loopback | Show/Hide All com vários tokens (tecla, gesto do knob, passo da Macro; falha de um não para os outros); ícone do Numeric Fields (`+3`, `−1`, multiplicador); Refresh Browser em lista e cena inteira (grupos, cena aninhada, sem laço); carrossel do Slot Wheel; Reveal Answer |
| `tests/test_show_control.py` | loopback | grupo exclusivo, Macro, Panic/Restore (Panic envia a edição pendente), Scene (store, recall, safe, delete), Shift, edição no ar só depois de parar de digitar, edição fora do ar na janela de 0,4 s |
| `tests/test_clock_scoreboard.py` | loopback | countdown com cores, fim e flash, knob do Clock, count up, time of day, until, pausar fora do ar, placar, Swap, Cycle, Reset |
| `tests/test_text_data.py` | loopback | Auto Close "soma tempo", fontes (lista, CSV, Format, arquivo salvo, Auto Next, knob), Text Template, enquete, meta |
| `tests/test_safety.py` | loopback | 2º toque, Lock Desk e trava automática, Status (cores, contador, log sem token, Clear log), backup (600, sem segredos, import, recusas) |
| `tests/test_settings_page.py` | loopback | engrenagem (`showSettingsInterface`) abre a página no navegador; só `127.0.0.1`; token exigido; `Host` e `Origin` de outro site recusados; CSP e cabeçalhos; salvar conecta ao OBS e vale para todas as teclas; senha nunca volta; cópia antiga de um inspetor não desfaz; host/porta inválidos, corpo grande e não-JSON recusados; fecha com o plugin; backup com host inválido não conecta; idioma, atraso das edições, control apps (token nunca volta), gatilhos e grupos salvos e limpos |
| `tests/test_i18n.py` | puro + loopback | catálogos completos e sem sobras, marcadores `{nome}` iguais, arquivos do OpenDeck gerados; ordem do idioma (página → `settings.json` do OpenDeck → registro → inglês); mensagens traduzidas; o inspetor pede o idioma ao abrir |
| `tests/test_manual.py` | puro + WeasyPrint | toda ação e todo campo do manifest têm ajuda; fontes dos 9 idiomas com a mesma estrutura; placeholder quando a imagem falta e imagem quando existe; carregador recusa arquivos fora de `docs/manual`; PDF com capa de idiomas, marcadores de cada idioma e todo link interno com destino |
| `tests/test_ci.py` | puro | todo comando dos passos dos workflows do Forgejo e do GitHub e de `make tools` existe na imagem `node:22-bookworm-slim` ou na lista do `apt-get install`; o workflow do GitHub tem os mesmos passos do Forgejo, só a release muda; só tag `v*`; actions fixadas por SHA, sem credencial persistida; no GitHub, `permissions: {}` e escrita só em `contents` |
| `tests/test_forgejo.py` | processo + loopback | release da tag: apaga a da mesma versão, cria com notas do CHANGELOG e anexa o ZIP e o manual (campo `attachment`), SHA-256 dos dois nas notas, não publica se a tag mudou de commit (`BUILD_COMMIT`), recusa tag diferente da versão; publish: commit novo por cima do histórico, tag enviada, nada apagado; reset: nada muda sem digitar o nome, espelho local do histórico antigo, apaga e recria com a mesma visibilidade, Actions ligado, um commit e a tag enviados por HTTP com o token como senha Basic, token fora da saída; senha antiga no credential helper é trocada pelo token, e a execução seguinte não pede token; User-Agent padrão do Python recusado (como o Cloudflare) |
| `tests/test_github.py` | processo + loopback | release da tag no GitHub: apaga a release e o rascunho da mesma versão (as de outras versões ficam), cria rascunho com notas do CHANGELOG e SHA-256, anexa o ZIP e o manual com o tipo de mídia, publica por último (o emulador recusa anexo em release publicada, como com releases imutáveis); segue tag anotada até o commit e recusa tag de tag; não publica se a tag mudou de commit (`BUILD_COMMIT`); recusa tag diferente da versão, arquivo faltando, token ausente e URL sem TLS (`http` só em loopback), sem nenhum pedido; `Authorization: Bearer` em todo pedido, token fora da saída |
| `tests/test_launch.py` | processo | `launch.sh` iniciado com os argumentos do OpenDeck: registro, global settings, idioma do `-info`, encerramento limpo |
| `tests/pi/inspector.test.cjs` | navegador | as 33 ações do manifest montam sem erro nem aviso no console, com todo controle nomeado e com **?** em todo campo e grupo; inspetor em pt-BR quando o plugin responde pt-BR; definições compartilhadas; busca e favoritos; página de configurações sob a mesma CSP (sem script inline), token só no cabeçalho, OBS, listas de gatilhos/grupos/control apps e ajuda |

## Emuladores (`tests/support.py`)

- **Datastore**: Engine.IO 4 + Socket.IO 5 como o `socket.io` 4.8.4 (ack só com id),
  contrato do `singular-datastore` 1.0.1 (login/update com callback,
  `rateLimitInfo`, broadcast com `userData`). Opções: formato do update, snapshot
  atrasado, sem eco, login sem `rateLimitInfo`, queda antes do ack, ack sem gravar.
- **App API**: os comandos que o plugin usa, aplicados aos dados do emulador.
- **OpenDeck**: eventos com o `GenericInstancePayload` do código do OpenDeck
  (`settings`, `coordinates`, `controller`, `state`, `isInMultiAction`) e os
  payloads de encoder (`ticks`, `pressed`).
- **OBS**: Hello/Identify com desafio SHA-256, requisições, troca de cena, eventos de
  transmissão e gravação e listas de itens de cena com grupos e cenas aninhadas
  (campos como no `Obs_ArrayHelper.cpp` do obs-websocket).

Os emuladores seguem contratos publicados; não são o UNO nem o OBS. Os testes
provam que o plugin cumpre esses contratos, não como os serviços reais reagem.

## Conferir que um teste pega o erro

Antes de confiar num teste novo, quebre de propósito o código que ele protege e
veja o teste falhar (checagem por mutação). Exemplos feitos na 1.0.0: backup com
permissão 644 → `test_units` falha; rótulo removido de um campo → teste do
inspetor falha. Na página de configurações: sem a checagem de `Host`, sem as chaves
do OBS em `OWNED`, com `bool()` no lugar de `is True`, sem `check_address` no
`configure_obs` e com um `style` inline no HTML, cada um desses testes falha.

Na 2.0.0, os testes novos foram rodados contra o código da 1.0.0 (commit `5f5ba8c`)
e falharam nos comportamentos novos (`test_global`: 18 falhas; `test_multi`: 13;
`test_show_control`: 3; `test_queue`: 1); só "Shift no A, knob no B" já passava, como
esperado (já funcionava entre dispositivos). Mutações conferidas: sem a deduplicação da
migração, Panic só com os apps abertos, sem reiniciar a espera da edição a cada tecla,
inspetor que ignora o idioma do plugin, `make` fora da imagem do CI, âncora de capítulo
trocada num manual traduzido: cada uma faz um teste falhar. Os erros achados no fim (idioma
do registro ignorado, seção da página perdida, mensagens sem `tr()`, app esquecido que voltava
ao registro) ganharam primeiro um teste que falhava (`test_launch`, teste do navegador,
`test_i18n`, `test_global`).

No workflow do GitHub (31/10/2026), `test_github` falhou antes de existir o
`scripts/github_release.py`. Mutações conferidas no script: publicar sem rascunho, apagar só
releases publicadas (sobra o rascunho), não seguir tag anotada, `Authorization: token` no
lugar de `Bearer`, ignorar `BUILD_COMMIT`, aceitar tag de tag, aceitar `http` fora de loopback; no workflow: passo diferente do Forgejo, action
por tag em vez de SHA, permissão de escrita a mais, sem `permissions: {}`, pacote a menos no
`apt-get`. Cada uma faz um teste falhar.

O teste de limite de 3 gravações/s (`test_queue`) falhou 1 vez em 12 com quatro processos
em paralelo: o emulador conta na chegada, e um atraso juntava gravações de duas janelas.
O limitador passou a começar a janela seguinte 0,1 s depois; depois disso, 16 em 16.

## Validação depois de instalar (manual)

1. Edite um campo na ação Overlay e aguarde **Saved to UNO.**; confira no Control
   App aberto, sem recarregar.
2. Tecla Overlay: mostre e esconda; o ícone fica vermelho no ar e branco fora.
3. Display e Numeric Fields no mesmo campo: some, subtraia e mude o número no
   site; o Display acompanha.
4. Tecla Status: verde e com o número de chamadas; toque para testar.
5. **Plugins → UNO Overlays → engrenagem**: a página abre no navegador; salve o OBS
   e veja **Connected to OBS.**; uma tecla OBS Scene troca a cena sem configurar nada nela.
6. Gatilho global: crie "cena Webcam entra → mostrar OV" com atraso; troque para um
   perfil sem essa tecla e coloque a cena no programa: o overlay entra, e o log mostra
   o evento, a decisão e o resultado.
7. Teclas da 1.0.0 com gatilhos: abra cada perfil uma vez e confira a lista de gatilhos
   na engrenagem.
8. Digite num campo com o overlay no ar: nada vai ao ar até parar de digitar
   (**Waiting to send (on air)…**), depois a palavra inteira.
9. Idioma: troque o idioma na engrenagem e reabra um inspetor; troque o do OpenDeck,
   deixe *Automático* e reabra.
10. OBS Refresh Browser com "todas as fontes da cena" numa cena com grupo e cena
    aninhada (o emulador segue o código do obs-websocket, mas não foi conferido num OBS real).
11. Quiz: confira, no modelo do overlay de quiz, qual campo revela a resposta e configure
    o Reveal Answer com ele.
12. Se algo falhar, anote só a mensagem do inspetor e a versão do plugin. Não
   publique token, perfil, backup ou captura que mostre o token.
