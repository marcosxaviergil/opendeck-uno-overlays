# UNO Overlays para OpenDeck 2.0.0

Controle os overlays do [UNO](https://overlays.uno) (Singular.live) pelo OpenDeck no
Linux: mostrar e esconder, slots, placar, relógios, fontes de dados, macros, OBS e
diagnóstico, com teclas e knobs. Interface em português do Brasil, inglês, espanhol,
italiano, alemão, japonês, chinês, coreano e francês. Pensado para a
Rise Mode Vision 01 (15 teclas) e Vision Sound 01 (6 teclas, 3 knobs sem tela e 3
botões sem tela), mas funciona em qualquer dispositivo que o OpenDeck suporte.

## Requisitos

- OpenDeck para Linux **2.6.0 ou mais novo** e Python **3.10 ou mais novo**, com certificados HTTPS.
  Debian/Ubuntu: `sudo apt install python3 ca-certificates`
- Internet para falar com o UNO. OBS Studio 28+ só se for usar as ações de OBS.
- Nada de pip ou npm: a única dependência (`websockets`) já vem no pacote.
  Independente de arquitetura (x86-64 e ARM64); testado em Linux x86-64.

## Instalar ou atualizar

1. No OpenDeck: **Plugins → Install from file** (em português: **Plugins →
   Instalar do arquivo**) e escolha `opendeck-uno-overlays-2.0.0-linux.plugin.zip`.
2. A instalação substitui a pasta anterior do plugin. Teclas, knobs e
   configurações continuam: os identificadores do plugin e das ações não mudaram.
3. Se uma tecla não atualizar, reinicie o OpenDeck.

**Vindo da 1.0.0:** gatilhos do OBS, encadeamentos "When it goes on air / off air"
e o tempo do grupo exclusivo saem das teclas Overlay e vão para a página de
configurações sozinhos, na primeira vez que cada tecla aparece. Uma tecla que nunca
aparece (perfil não usado, dispositivo desligado) não é migrada: abra cada perfil
uma vez depois de atualizar. A escolha "Hide, change, show again" de "Edits while on air"
deixou de existir: edições no ar vão direto, depois do atraso configurado.

O manual completo, nos 9 idiomas, vem na release como
`UNO-Overlays-2.0.0-Manual.pdf`.

## Primeiros passos

1. No UNO, abra o Control App do overlay, **? → API Description**, e copie o
   token: o trecho da URL entre `/controlapps/` e `/api`. Use o token de
   controle, não a URL de saída do OBS.
2. No OpenDeck, arraste uma ação **UNO Overlays** para uma tecla, cole o token em
   **API Token** e clique **Connect / Reload**.
3. Escolha o overlay (a lista tem busca e ★ favoritos) e o que a tecla faz.
   Edições no formulário vão direto ao UNO; aguarde **Saved to UNO.**
4. Todo campo tem um **?** ao lado: passe o mouse ou chegue com Tab para ler o que
   ele faz; Esc fecha.

## Ações

Tally: toda tecla que mostra estado fica com o ícone **branco** fora do ar e
**vermelho vivo** no ar, sem texto. O estado vem do UNO em tempo real.

### Overlays e slots

| Ação | O que faz |
| --- | --- |
| **Overlay** | Mostra/esconde (ou chama um slot salvo e mostra). Formulário do modelo UNO com gravação imediata; slots do servidor: adicionar, renomear, remover |
| **Show All / Hide All** | Todos os overlays de um ou vários tokens (**Add token**); um token com falha não para os outros |
| **Next Slot / Previous Slot** | Chama o próximo/anterior slot e mostra |
| **Numeric Fields** | Soma/subtrai num campo numérico (multiplicador global ou passo fixo); o ícone mostra o passo (`+3`, `−1`) |
| **Multiplier** | Define o multiplicador global (1–50); no knob, girar muda |
| **Display** | Mostra o valor de um campo numérico ao vivo, inclusive mudanças feitas no site |
| **Reveal Answer** | Alterna revelar/esconder um campo do overlay no ar (resposta de quiz), com cópia opcional da resposta certa para um campo de destaque; volta a esconder quando outro slot entra |

### Knobs e Visor (Vision Sound 01)

| Ação | O que faz |
| --- | --- |
| **Knob Control** | Ação independente para girar à esquerda, à direita e apertar |
| **Slot Wheel** | Girar escolhe o slot (dá a volta); apertar chama e mostra. Opcional, **carrossel**: cada giro chama o slot seguinte/anterior no ar e apertar mostra/esconde |
| **Dial Value** | Apertar entra em edição, girar escolhe, apertar envia uma vez; segurar 2 s cancela |
| **Visor** | Mostra o que o knob do mesmo canal está escolhendo; apertar = apertar o knob. Use também nos 3 botões sem tela |

Sugestão para a Sound 01: coluna 1 = Slot Wheel + Visor (canal 1); coluna 2 =
Dial Value + Visor (canal 2); coluna 3 = Clock no knob + Visor (canal 3).

### Tempo

| Ação | O que faz |
| --- | --- |
| **Clock** | Relógio num campo de **texto**, atualizado a cada segundo: *Countdown*, *Count up*, *Time of day* (começa sozinho) e *Until finish time*. Funções do vMix: Pause/Resume, Start, Pause only, Stop and reset, Set, Change, Adjust. No knob: girar soma/subtrai o passo |
| **Timer** | Play, Pause, Reset, Start ou Play/Pause num campo *timecontrol* (o overlay anima) |

Opções do Clock: cores de fim (verde → amarelo → vermelho), parar ou continuar em
0:00 (overtime −0:01 ou +0:01), piscar 1, 2, 3 vezes ou até parar, Show/Hide de um
overlay ao completar, pausar enquanto o overlay está fora do ar. Formatos 230:59,
41:30:59 e 92. Os relógios rodam no plugin: continuam ao trocar de página e param
se o OpenDeck fechar.

### Placar

| Ação | O que faz |
| --- | --- |
| **Undo** | Desfaz a última mudança de placar (até 50, só na memória) |
| **Lock** | Trava as mudanças de placar do token até tocar de novo |
| **Swap Sides** | Troca os valores de cada par de campos de uma vez |
| **Cycle** | Grava o próximo valor de uma lista (1º tempo, 2º tempo…); pode parar e zerar um Clock |
| **Reset** | Segure 2 s: volta os campos ao *resetValue* do modelo, ou 0 / vazio |

No Numeric Fields: passo fixo, mínimo e máximo, min/max do modelo UNO, alerta no
limite e "mostrar um overlay por N segundos depois de um ponto".

### Texto e dados

| Ação | O que faz |
| --- | --- |
| **Data Source** | Linhas de uma lista digitada, .txt ou .csv, mapeadas para campos como no vMix (coluna *Auto*, linha selecionada ou fixa, *Format* `Nome: {0}` ou `{Nome} – {Cargo}`). Next, Previous, Select row, Auto Next (com Loop). No knob: girar escolhe, apertar seleciona. Arquivo salvo = campos atualizados |
| **Text Template** | Grava um texto com `{Overlay::Campo}` trocado pelo valor atual |
| **Poll Vote** | +1 voto por tecla (±1 no knob); total e % acompanham |
| **Goal** | Meta como a *Tip Goal* do Streamlabs: título, valor da meta, valor inicial, término; somar, iniciar, encerrar; ao bater a meta, Show/Hide de um overlay |

Fontes de dados, enquetes e metas são compartilhadas por todas as teclas
(menu **Create / Delete** no inspetor). Arquivos: caminho completo, em UTF-8.

### Controle do show

| Ação | O que faz |
| --- | --- |
| **Macro** | Passos em ordem: Show, Hide, Toggle, slots, Show/Hide All (um ou vários tokens), valor de campo, Timer, cena do OBS, Recall scene e **Wait**, que atrasa os passos seguintes |
| **Panic** | Cancela macros, atrasos e Auto Close, envia edições pendentes e esconde tudo; sem token, em todos os control apps registrados |
| **Restore** | Mostra de novo o que o último Panic tirou do ar (guardado só na memória) |
| **Scene** | *Store* guarda visibilidade, slot e conteúdo de todos os overlays; *Recall* aplica, menos os *recall safe*; **Delete stored scene** apaga |
| **Shift** | Enquanto segurada, Slot Wheel e Dial Value usam o alvo "While Shift is held" |

### OBS Studio

| Ação | O que faz |
| --- | --- |
| **OBS Scene** | Troca a cena de programa e, se quiser, mostra um overlay; vermelha com a cena no ar |
| **OBS Refresh Browser** | Recarrega sem cache uma lista de Browser Sources (**Add source**) ou todas as de uma cena, inclusive em grupos e cenas aninhadas |

## Página de configurações (engrenagem)

No OpenDeck: **Plugins**, no cartão **UNO Overlays** clique na engrenagem verde
(**Settings**; em português, **Configurações**). A página abre no navegador padrão e
guarda o que vale para todas as teclas, em qualquer perfil e dispositivo:

| Seção | O que faz |
| --- | --- |
| **Language** | Idioma das teclas, do inspetor e da página; *Automático* segue o idioma do OpenDeck. Italiano só por aqui (o OpenDeck não tem) |
| **OBS Studio** | Conexão única com o OBS (abaixo) |
| **Edits while on air** | Com o overlay no ar, o formulário espera N ms sem alterações antes de enviar (padrão 1000, 0 a 10 000; 0 = envia enquanto digita). Cada tecla Overlay pode ter o seu valor |
| **Control apps** | Tokens registrados (entram quando uma tecla conecta); nome opcional, remover. Status, Panic, Restore, gatilhos e grupos usam esta lista |
| **Triggers** | **Add trigger**: evento (cena do OBS entra/sai do programa, live ou gravação começa/termina, overlay do UNO entra/sai do ar), função Show/Hide, control app e overlay, atraso até 30 000 ms, liga/desliga. Cada gatilho escreve no log o que recebeu, se disparou e o resultado |
| **Exclusive groups** | Nome, tempo (+ espera antes de entrar, − deixa os antigos saírem depois) e membros. A tecla Overlay só escolhe o grupo |

**Conexão com o OBS, uma vez para todas as teclas:**

1. No OBS: **Ferramentas → Configurações do servidor WebSocket**, ative o servidor
   e copie a porta e a senha.
2. No OpenDeck: **Plugins**, no cartão **UNO Overlays** clique na engrenagem verde
   (**Settings**; em português, **Configurações**). A página de configurações do
   plugin abre no navegador padrão.
3. Marque **Connect to OBS**, preencha host (127.0.0.1 se o OBS estiver no mesmo
   computador), porta (4455) e senha e clique **Save and connect**. A página mostra
   **Connected to OBS.** quando a conexão funcionar.

Todas as teclas usam essa conexão; o inspetor de cada tecla só lembra onde ela fica.
O OpenDeck não permite que plugins criem menus na janela nem na bandeja: a
engrenagem em **Plugins** é o lugar que ele oferece para configurações do plugin.
A página só existe enquanto é usada (fecha após 10 minutos parada) e só aceita
conexões do próprio computador. A senha salva nunca é mostrada de volta: deixe o
campo vazio para mantê-la ou marque **Remove the saved password**.

### Segurança e diagnóstico

| Ação | O que faz |
| --- | --- |
| **Lock Desk** | Trava todas as teclas e knobs do plugin (só mostram alerta); segurar 2 s destrava. Opcional: travar sozinha após N s sem uso |
| **Status** | Verde, amarelo ou vermelho com as chamadas à App API do dia; tocar testa as conexões. Inspetor: log (sem tokens), **Clear log**, backup (*Export* / *Import*) |

## Opções (todas desligadas por padrão)

| Opção | Onde | Padrão |
| --- | --- | --- |
| Confirmar com 2º toque (2, 3, 5 ou 10 s; a tecla pisca armada) | seção *Safety (optional)* de quase toda tecla | um toque executa |
| Auto Close com badge vermelho de segundos | Overlay, Next/Previous Slot, Slot Wheel, Numeric Fields, OBS Scene | desligado |
| Tocar de novo durante o Auto Close soma o tempo | Overlay | esconder na hora |
| Grupo exclusivo (mostrar um tira os outros) | Overlay escolhe; tempo e membros na engrenagem | sem grupo |
| Atraso próprio das edições no ar | Overlay | o da engrenagem |
| "Só nestas cenas do OBS" | Overlay | qualquer cena |
| Carrossel de slots | Slot Wheel | escolher e apertar |
| Gatilhos e encadeamentos (entra/sai do ar) | engrenagem | nada |

## Como as gravações funcionam

- Todas as teclas, knobs e inspetores, de todos os dispositivos, entram numa
  **fila única**: uma operação por vez, na ordem. Giros seguidos do mesmo campo
  somam-se num só envio, sem pular a ordem de outro comando do mesmo overlay.
- A fila espera a janela seguinte quando atinge o limite informado pelo UNO
  (requisições/s e bytes/min). O plano gratuito tem "a 10,000-call daily cap"
  (artigo do plugin UNO v2); a tecla Status conta as chamadas do dia.
- Uma gravação só é confirmada pelo servidor; nada é repetido sozinho depois de
  um timeout. Sem transação atômica no UNO, duas pessoas editando o mesmo campo
  ao mesmo tempo podem se sobrepor.
- Com o overlay no ar, o formulário só envia depois da pausa definida na
  engrenagem (padrão 1000 ms), para o público não ver a palavra pela metade.
  Fechar o inspetor, mudar de campo, tocar a tecla ou o Panic enviam na hora.
- Auto Close e toques já feitos continuam depois de trocar de perfil; só mudança
  real da tecla, novo toque ou Panic os cancelam.

## Limitações

- **Visor e knob** só funcionam com os dois na tela: o OpenDeck só informa os
  knobs do perfil selecionado, e o estado da escolha vive no knob.
- **Restore** guarda o conjunto só na memória: reiniciar o plugin o esquece.
- **Atraso de gatilho** que já está contando sobrevive a edições do gatilho; o
  Panic o cancela.
- O OpenDeck envia o mesmo evento ao **apagar** uma tecla e ao trocar de perfil:
  um Auto Close em contagem termina normalmente (no máximo 120 s).
- A **migração** da 1.0.0 só alcança teclas que aparecerem pelo menos uma vez.
- Traduções para japonês, chinês e coreano ainda sem revisão humana.

## Privacidade e segurança

Nomes e textos dos overlays são dados pessoais e vão para o UNO. O plugin não
envia nada aos autores e não registra tokens. Veja o que é tratado, onde fica e
como apagar em [docs/PRIVACY.md](docs/PRIVACY.md) (LGPD), e as medidas e os
riscos do OpenDeck em [docs/SECURITY.md](docs/SECURITY.md).

## Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| "Enter the control API token, not the output URL." | Cole só o token (letras, números, `_` e `-`) |
| "UNO HTTP 4xx" | Token errado ou revogado: copie de novo em **API Description** |
| "OBS is not connected…" | Configure em **Plugins → UNO Overlays → Settings** e confira se o OBS está aberto |
| A engrenagem não abre nada | Sem navegador padrão configurado: `xdg-settings get default-web-browser` mostra qual o sistema usa |
| Tecla só mostra alerta | A mesa está travada (Lock Desk vermelha) ou a tecla está fora das cenas permitidas do OBS |
| Um gatilho não disparou | Veja o log: cada gatilho registra o evento, se disparou ou foi ignorado (e por quê) e o resultado |
| Display mostra — | Sem conexão em tempo real: o plugin tenta de novo com intervalo crescente até 30 s |

Log do plugin: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

## Créditos e licença

MIT. Baseado no UNO Overlay Control (SeTIC UFSC), versões 3.1.1 a 5.0.1-fixed6,
adaptado por Marcos Xavier. Terceiros em [vendor/NOTICE.md](vendor/NOTICE.md):
`websockets` (BSD-3-Clause) e Material Symbols (Apache-2.0). Projeto independente
de UNO, Singular.live, OpenDeck, OBS e Rise Mode.
