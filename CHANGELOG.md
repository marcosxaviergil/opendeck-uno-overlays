# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões: [SemVer](https://semver.org/lang/pt-BR/).
Cada seção traz só as diferenças para a versão publicada anterior.

## [2.0.0] - 2026-10-01

Versão maior: os gatilhos e os grupos exclusivos saem das teclas e passam a valer para o plugin inteiro, e a edição no ar com "esconder, alterar e mostrar de novo" foi removida. As teclas da 1.0.0 são migradas automaticamente (veja **Atualizando da 1.0.0**).

### Adicionado

- **Gatilhos globais** na página de configurações (**Plugins → UNO Overlays →** engrenagem), com o botão **Add trigger**. Cada gatilho tem evento, cena do OBS, função (mostrar ou esconder), control app e overlay de destino, atraso de 0 a 30 000 ms e um interruptor para desligar sem apagar. Eventos:
  - cena entra ou sai do programa do OBS;
  - transmissão ou gravação começa ou termina;
  - um overlay do UNO entra ou sai do ar (encadeamento no estilo *OnOverlayIn/Out* do vMix).
- Os gatilhos funcionam com qualquer perfil e dispositivo, mesmo sem nenhuma tecla do overlay na tela.
- O log registra, em INFO e sem token, cada evento recebido do OBS, cada gatilho avaliado (disparou ou ignorou, e por quê) e o resultado no UNO.
- **Grupos exclusivos globais** na página de configurações: nome, tempo e overlays de qualquer control app. A tecla Overlay só escolhe o grupo.
- **Control apps registrados** na página de configurações: todo token que conecta numa tecla (ou cujos gatilhos foram migrados) entra no registro e pode ser renomeado ou removido. Status, teste de conexão, Panic e Restore sem token passam a alcançar todos os registrados.
- **Show All / Hide All para vários tokens:** lista **Control apps** com **Add token** na tecla, nos gestos do Knob Control e nos passos da Macro. Um token com falha não impede os outros; a falha aparece no alerta e no log, sem o token.
- **OBS Refresh Browser com várias fontes:** lista de fontes com **Add source**, ou a opção de atualizar todas as fontes de navegador de uma cena (inclusive as de grupos e cenas aninhadas).
- **Slot Wheel em carrossel** (opcional): girar chama o slot seguinte ou anterior no ar; apertar mostra ou esconde. Giros rápidos são somados num só pedido ao UNO, com intervalo mínimo de 0,3 s.
- **Reveal Answer:** ação nova que alterna revelar e esconder um campo do overlay no ar (por exemplo, a resposta de um quiz), com valores configuráveis, cópia opcional de um campo para outro e volta ao estado oculto quando outro slot entra. Tally vermelho quando revelada.
- **Atraso das edições no ar:** com o overlay no ar, o formulário só envia ao UNO depois de um tempo sem alterações (padrão 1000 ms, de 0 a 10 000; 0 = como antes). O valor fica na página de configurações, com valor opcional por tecla. A edição pendente é enviada ao fechar o inspetor, ao sair do campo, ao tocar a tecla e no Panic. O inspetor mostra **Waiting to send (on air)…** enquanto espera.
- **Ajuda (?) em todos os campos** do inspetor e da página de configurações: aparece ao passar o mouse ou ao focar pelo teclado e some com Esc (WCAG 1.4.13).
- **Idiomas:** português do Brasil, inglês, espanhol, italiano, alemão, japonês, chinês simplificado, coreano e francês, no inspetor, na página de configurações, nas mensagens e na lista de ações do OpenDeck. O idioma segue o do OpenDeck e pode ser escolhido na página de configurações. Traduções para japonês, chinês e coreano sem revisão humana.
- **Manual em PDF** nos 9 idiomas, anexado à release (`UNO-Overlays-2.0.0-Manual.pdf`), com sumário por idioma, links internos e marcadores.
- **Numeric Fields:** o ícone mostra o sinal e o passo (`+3`, `−1`); sem passo fixo, mostra o multiplicador atual.

### Alterado

- **Atualizando da 1.0.0:** quando uma tecla Overlay da 1.0.0 aparece pela primeira vez, os gatilhos do OBS, os encadeamentos "When it goes on air / off air" e o tempo do grupo exclusivo dela são copiados para as configurações globais, sem duplicar, e removidos da tecla. **Teclas que nunca aparecerem** (perfil não usado) não são migradas: abra cada perfil uma vez depois de atualizar.
- O inspetor da tecla Overlay não tem mais as seções de gatilhos do OBS e de encadeamento; uma linha indica onde configurá-los. "Key shows only while OBS program scene is" continua na tecla.
- O Auto Close e os toques já feitos não são mais cancelados ao trocar de perfil; só uma mudança real das configurações da tecla, um novo toque ou o Panic os cancelam.
- O Cycle com "reset clock" e o Visor de um Clock parado usam a configuração do Clock guardada, mesmo com a tecla fora da tela.
- O backup inclui gatilhos, grupos, idioma, atraso das edições e configurações de Clock e Reveal; os tokens registrados só entram com **Include API tokens and OBS password**.
- A fila espera 0,1 s a mais antes de abrir uma nova janela de gravações no datastore, para que atrasos de rede não façam o UNO contar mais gravações por segundo que o limite.

### Removido

- Escolha **Live edits: Hide, change, show again** e campo **Wait after hiding**, do grupo *Edits while on air (optional)* da tecla Overlay. Edições no ar são sempre aplicadas diretamente, agora depois do atraso descrito acima (o grupo passou a ter só esse atraso). O valor salvo nas teclas é ignorado e apagado.

### Corrigido

- Gatilhos do OBS deixavam de funcionar quando a tecla estava num perfil não selecionado ou num dispositivo desconectado.
- O grupo exclusivo não escondia overlays cuja tecla não estava na tela.
- Digitar no formulário com o overlay no ar mostrava o texto pela metade ("Al", depois "Aline").

### Segurança

- A página de configurações passou a aceitar pedidos de até 64 KiB (antes 4 KB), para caber as listas, com no máximo 200 gatilhos e 50 grupos; nunca devolve tokens, só o identificador curto e o nome de cada control app.
- Um token adicionado pela página só entra no registro depois de responder ao UNO.
- Os tokens ficam uma só vez no registro de control apps; gatilhos, grupos e log usam só um identificador curto (início do SHA-256 do token).
- O manual é gerado no pipeline pelo WeasyPrint do Debian, apenas a partir de arquivos do próprio repositório (sem acesso à rede). Detalhes em [SECURITY.md](docs/SECURITY.md).

### Instalação

No OpenDeck, acesse **Plugins → Install from file** e selecione `opendeck-uno-overlays-2.0.0-linux.plugin.zip`.

## [1.0.0] — 2026-09-30

Primeira versão do UNO Overlays para OpenDeck: controle de overlays do [UNO](https://overlays.uno) (Singular.live) por teclas e knobs no Linux.

### Requisitos

- OpenDeck para Linux 2.6.0 ou superior.
- Python 3.10 ou superior, com certificados HTTPS (`sudo apt install python3 ca-certificates`).
- Acesso à internet para comunicação com o UNO.
- OBS Studio 28 ou superior, apenas para as ações de OBS.
- Arquiteturas x86-64 e ARM64. Nenhuma dependência externa: `websockets` já vem no pacote.

### Funcionalidades

**Overlays e slots**

- **Overlay:** mostra, esconde ou alterna um overlay, ou chama um slot salvo. O formulário do modelo UNO grava as alterações imediatamente, e os slots do servidor podem ser adicionados, renomeados e removidos.
- **Show All / Hide All:** mostra ou esconde todos os overlays do token.
- **Next Slot / Previous Slot:** chama o slot seguinte ou o anterior e mostra o overlay.
- **Numeric Fields:** incrementa ou decrementa um campo numérico, com multiplicador global ou passo fixo, limites mínimo e máximo e alerta ao atingir o limite.
- **Multiplier:** define o multiplicador global, de 1 a 50.
- **Display:** exibe em tempo real o valor de um campo numérico.

**Knobs**

- **Knob Control:** uma ação independente para cada movimento: girar à esquerda, apertar e girar à direita.
- **Slot Wheel:** girar escolhe o slot, apertar chama o slot e mostra o overlay.
- **Dial Value:** apertar inicia a edição, girar escolhe o valor, apertar envia; segurar por 2 s cancela.
- **Visor:** exibe a seleção do knob do mesmo canal; apertar equivale a apertar o knob.
- **Shift:** enquanto pressionada, Slot Wheel e Dial Value usam um alvo alternativo.

**Tempo**

- **Clock:** relógio em campo de texto nos modos Countdown, Count up, Time of day e Until finish time.
  - Funções no estilo vMix: pausar, retomar, parar, definir e ajustar o tempo.
  - Cores de fim, overtime e piscar ao terminar.
  - Mostrar ou esconder um overlay ao completar.
  - No knob, girar ajusta o tempo.
- **Timer:** Play, Pause, Reset e Start em campos *timecontrol*.

**Placar**

- **Undo:** desfaz as últimas 50 alterações de placar.
- **Lock:** bloqueia e desbloqueia as alterações de placar.
- **Swap Sides:** troca os valores de pares de campos.
- **Cycle:** avança um campo por uma lista de valores (períodos, posse); pode zerar um Clock.
- **Reset:** segurar por 2 s restaura os campos ao valor inicial do modelo, ou a 0 ou vazio.

**Texto e dados**

- **Data Source:** lista, `.txt` ou `.csv` mapeados para campos do overlay.
  - Next, Previous, Select e Auto Next com Loop.
  - Atualização automática ao salvar o arquivo.
- **Text Template:** grava um texto montado a partir de vários campos (`{Overlay::Campo}`).
- **Poll Vote:** votos por tecla ou knob, com total e percentual atualizados.
- **Goal:** meta com título, valor e término; somar, iniciar e encerrar; ação ao atingir a meta.

**Controle do show**

- **Macro:** passos em sequência com espera (**Wait**), incluindo overlays, slots, campos, Timer, cena do OBS e cenas armazenadas.
- **Panic:** cancela macros, atrasos e Auto Close e esconde todos os overlays.
- **Restore:** mostra novamente o que o último Panic retirou do ar.
- **Scene:** armazena, aplica e apaga a visibilidade, o slot e o conteúdo de todos os overlays.

**OBS Studio**

- **OBS Scene:** troca a cena de programa e pode mostrar um overlay junto.
- **OBS Refresh Browser:** recarrega uma Browser Source sem cache.
- **Conexão única:** configurada na página de configurações do plugin (**Plugins → UNO Overlays →** engrenagem) e usada por todas as teclas.

**Operação e diagnóstico**

- **Lock Desk:** bloqueia todas as teclas e knobs do plugin; segurar por 2 s desbloqueia. O bloqueio automático por inatividade é opcional.
- **Status:** estado das conexões e chamadas do dia à App API; tocar testa as conexões.
- **Log:** log de diagnóstico sem tokens e ação **Clear log** para limpá-lo.
- **Backup:** exportação e importação das configurações.

**Recursos gerais**

- Tally em tempo real: ícone branco fora do ar e vermelho no ar.
- Fila única de gravação para todos os dispositivos, respeitando o limite de requisições informado pelo UNO.
- Busca e favoritos nas listas de overlays e campos.
- Opcionais, desligados por padrão:
  - confirmação por segundo toque;
  - Auto Close com contagem na tecla;
  - grupo exclusivo de overlays;
  - encadeamento ao entrar e ao sair do ar;
  - edição no ar;
  - gatilhos do OBS.

### Privacidade e segurança

- Nenhum dado é enviado aos autores; tokens não são registrados em log.
- Dados pessoais podem ser apagados sob demanda com **Delete stored scene** e **Clear log** (LGPD, Art. 16 e 18). Detalhes em [PRIVACY.md](docs/PRIVACY.md).
- A página de configurações aceita apenas conexões do próprio computador, exige um token por sessão e fecha após 10 minutos sem uso. A senha do OBS nunca é exibida de volta.
- Caminhos de arquivo são validados (absolutos, extensão esperada, até 10 MB); o backup não sobrescreve arquivos nem segue links simbólicos.
- Medidas e riscos conhecidos do OpenDeck estão em [SECURITY.md](docs/SECURITY.md).

### Instalação

No OpenDeck, acesse **Plugins → Install from file** e selecione `opendeck-uno-overlays-1.0.0-linux.plugin.zip`.

### Checksums

| Arquivo | SHA-256 |
| --- | --- |
| `opendeck-uno-overlays-1.0.0-linux.plugin.zip` | `a047296e053cf580c69ccd6656a9b4bd12a4bb25eb08d0234c666057e9f24226` |