% UNO Overlays para OpenDeck — Manual
% Sumário

# Introdução {#introduction}

O UNO Overlays controla os overlays do [UNO](https://overlays.uno) (Singular.live) pelo OpenDeck no Linux, com teclas e knobs: mostrar e esconder, slots do servidor, placar, relógios, fontes de dados, enquetes, metas, macros, OBS Studio e diagnóstico.

Foi pensado para a Rise Mode Vision 01 (15 teclas) e a Vision Sound 01 (6 teclas, 3 knobs e 3 botões sem tela) e funciona com qualquer dispositivo que o OpenDeck suporte.

- Toda tecla mostra seu estado: o ícone fica **branco** fora do ar e **vermelho vivo** no ar. O estado vem do UNO em tempo real.
- Toda operação no UNO, de qualquer dispositivo, tecla, knob ou inspetor, passa por **uma fila global**, uma de cada vez e em ordem.
- Gatilhos, grupos exclusivos e a lista de control apps são **globais**: funcionam com qualquer perfil ou dispositivo na tela.

# Instalação {#installation}

## Requisitos

- OpenDeck para Linux 2.6.0 ou mais novo.
- Python 3.10 ou mais novo, com certificados HTTPS (Debian/Ubuntu: `sudo apt install python3 ca-certificates`).
- Acesso à internet para falar com o UNO.
- OBS Studio 28 ou mais novo, só para as ações e os gatilhos do OBS.
- Nada mais: a única dependência (`websockets`) já vem no pacote.

## Instalar ou atualizar

1. Baixe `opendeck-uno-overlays-<versão>-linux.plugin.zip` da release.
2. No OpenDeck, abra **Plugins → Instalar do arquivo** (em inglês, **Install from file**) e escolha o arquivo.
3. A instalação substitui a pasta anterior do plugin. Teclas, knobs e configurações continuam: os identificadores do plugin e das ações não mudaram.
4. Se uma tecla não atualizar, reinicie o OpenDeck.

![OpenDeck: Plugins → Instalar do arquivo](botao_instalar_plugins.jpg)

## Atualizando da versão 1.0

- Os gatilhos das teclas Overlay passam sozinhos para a lista global na primeira vez que cada tecla aparece. Uma tecla que nunca aparece (outro perfil, um dispositivo desconectado) guarda os gatilhos antigos até aparecer uma vez: abra esse perfil uma vez depois de atualizar.
- A opção "Edições no ar (opcional) – Esconder, alterar, mostrar de novo" não existe mais: edições no ar são sempre gravadas diretamente, depois da pausa definida na página de configurações.

# Primeiros passos {#first-steps}

1. No UNO, abra o Control App do overlay, **? → API Description**, e copie o token: o trecho do endereço entre `/controlapps/` e `/api`. Use o token de controle, não a URL de saída usada no OBS.
2. No OpenDeck, arraste uma ação **UNO Overlays** para uma tecla, cole o token em **Token da API** e clique em **Conectar / Recarregar**.
3. Escolha o overlay (a lista tem busca e ★ favoritos) e o que a tecla faz. As edições no formulário vão direto para o UNO; aguarde **Gravado no UNO.**
4. Todo campo tem um **?** ao lado: passe o ponteiro sobre ele, ou chegue a ele com Tab, para ler o que o campo faz. Esc fecha o texto.

![Inspetor de uma tecla Overlay](inspetor_overlay.jpg)

# Página de configurações {#settings-page}

O que todas as teclas compartilham fica na página de configurações do próprio plugin: no OpenDeck, em **Plugins**, no cartão **UNO Overlays**, clique na engrenagem verde (**Configurações**). A página abre no navegador padrão, aceita conexões só deste computador e fecha depois de 10 minutos sem uso.

![OpenDeck: a engrenagem do plugin UNO Overlays](engrenagem_plugins.jpg)

![Página de configurações do plugin](pagina_configuracoes.jpg)

{{settings}}

## Idiomas

O plugin fala português do Brasil, inglês, espanhol, italiano, alemão, japonês, chinês (simplificado), coreano e francês. Com **Automático (idioma do OpenDeck)**, segue o idioma escolhido nas configurações do OpenDeck; um idioma escolhido na página de configurações tem prioridade. O OpenDeck não oferece italiano, então o italiano só é escolhido na página de configurações. Quando o idioma do OpenDeck muda, abra de novo um inspetor ou a página de configurações para o plugin lê-lo.

## Gatilhos

Um gatilho executa uma função quando um evento acontece, como os gatilhos do vMix: mostrar ou esconder um overlay, depois de um atraso de até 30 000 ms. Eventos: uma cena do OBS entra ou sai do programa, a transmissão começa ou termina, a gravação começa ou termina, um overlay do UNO entra ou sai do ar (os encadeamentos "Quando este overlay entra/sai do ar" da versão 1.0). Use **Adicionar gatilho** para criar quantos precisar; cada um pode ser desligado sem ser apagado.

Todo gatilho escreve no log do plugin: o evento recebido, a decisão (disparou ou ignorou, e por quê) e o resultado no UNO, sem tokens.

## Grupos exclusivos

Overlays do mesmo grupo nunca ficam no ar juntos: mostrar um esconde os outros, inclusive os que não têm tecla na tela. As teclas Overlay escolhem o grupo pelo nome; o tempo e os membros ficam na página de configurações.

# Como funciona {#how-it-works}

- **Fila global.** Todas as teclas, knobs e inspetores de todos os dispositivos entram numa só fila: uma operação no UNO de cada vez, em ordem. Giros no mesmo campo se somam numa só gravação.
- **Limites.** A fila espera a próxima janela quando chega aos limites informados pelo UNO. O plano gratuito do uno tem limite diário de 10 000 chamadas à App API; a tecla Status as conta.
- **Gravações.** Uma gravação só é confirmada pelo servidor; nada é repetido sozinho depois de um tempo esgotado.
- **Edições no ar.** Com o overlay no ar, uma edição só é enviada depois de uma pausa sem alterações (1000 ms por padrão), para o público nunca ver uma palavra pela metade. Fechar o inspetor, passar para outro campo, tocar uma tecla ou o Pânico enviam na hora.
- **Teclas fora da tela.** Os timers de Auto Close e os toques já feitos continuam depois de trocar de perfil; só uma mudança real nas configurações da tecla, o Pânico ou um novo toque os cancelam.

# Limitações {#limitations}

- **Visor e knob.** Uma tecla Visor e seu knob só funcionam enquanto os dois estão na tela: o knob guarda o que está escolhendo, e o OpenDeck só informa o plugin sobre knobs do perfil selecionado.
- **Restaurar.** O conjunto de overlays que o Restaurar traz de volta fica na memória: reiniciar o plugin o esquece.
- **Atrasos de gatilho.** Um atraso de gatilho que já está contando sobrevive a edições do gatilho; o Pânico o cancela.
- **Teclas apagadas.** O OpenDeck envia o mesmo evento quando uma tecla é apagada e quando o perfil dela é trocado, então um Auto Close que já está contando termina normalmente (no máximo 120 s).
- **Migração.** Os gatilhos da versão 1.0 só passam para a lista global quando a tecla deles aparece pelo menos uma vez.
- **Quiz.** O Revelar resposta é genérico: escolha o campo e os valores que o seu overlay usa para revelar a resposta.

# Casos de uso {#use-cases}

## Placar

Teclas Campos numéricos para cada time (a tecla mostra +1, +2, +3…), uma tecla Visor de valor para cada placar, Desfazer, Trava, Trocar lados quando os times trocam de lado, Ciclo para o período e Zerar segurado por 2 s no fim.

## Quiz

Um knob Roda de slots com o carrossel ligado: cada giro põe a pergunta seguinte no ar; apertar mostra ou esconde o overlay. Uma tecla Revelar resposta revela a resposta e copia a opção correta para o campo de destaque; a pergunta seguinte a esconde de novo sozinha.

## Relógio

Uma tecla Relógio num campo de texto: contagem regressiva, progressiva, hora do dia ou até um horário de término, com cores de fim. Num knob, girar ajusta o tempo e uma tecla Visor o mostra.

## Ticker e listas

Uma Fonte de dados com lista digitada, arquivo .txt ou .csv, mapeada para os campos do overlay, com Auto Next e Repetir.

## OBS Studio

Uma tecla OBS: cena troca a cena de programa e pode mostrar um overlay. Um gatilho mostra o lower third da câmera quando a cena "Webcam" entra no programa e o esconde quando ela sai. OBS: atualizar navegador recarrega várias fontes de navegador, ou todas as fontes de navegador de uma cena.

# Ações {#actions}

{{actions}}

# Problemas comuns {#troubleshooting}

- **"Coloque o token de controle da API, não a URL de saída."** Cole só o token (letras, números, `_` e `-`).
- **"UNO HTTP 4xx".** O token está errado ou foi revogado: copie de novo em **API Description**.
- **"UNO HTTP 429".** Pedidos demais: aguarde um pouco; evite ferramentas que consultem o UNO com o mesmo token.
- **"O OBS não está conectado…".** Configure na página de configurações e confira se o OBS está aberto.
- **A engrenagem não abre nada.** Não há navegador padrão definido: `xdg-settings get default-web-browser` mostra qual o sistema usa.
- **Uma tecla só mostra um alerta.** A mesa está travada (Trava da mesa vermelha) ou a tecla está fora das cenas do OBS permitidas.
- **Um gatilho não executou.** Veja o log do plugin: cada gatilho escreve se disparou ou foi ignorado, e por quê. Log: `~/.local/share/opendeck/logs/plugins/dev.br.consciencia.opendeck.uno-overlays.sdPlugin.log`

# Privacidade e segurança {#privacy}

Nomes e textos dos overlays são dados pessoais e vão para o UNO. O plugin não envia nada aos autores e não grava tokens em log. Os tokens ficam nas configurações do OpenDeck neste computador; a página de configurações nunca mostra de volta um token nem a senha do OBS. Cenas guardadas e o log podem ser apagados a pedido (Apagar cena guardada, Limpar log). Para exercer os direitos da LGPD, abra uma issue no projeto. Detalhes em PRIVACY.md e SECURITY.md do plugin.
