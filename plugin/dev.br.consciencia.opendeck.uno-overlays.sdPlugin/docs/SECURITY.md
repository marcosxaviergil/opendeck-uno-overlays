# Segurança

Escopo: o plugin roda no seu computador, iniciado pelo OpenDeck. Ele fala com
o OpenDeck (WebSocket local), com o UNO (`https://app.overlays.uno` e
`wss://datastore.singular.live`) e, se você ligar, com o OBS (obs-websocket 5).
Tratamos como **não confiáveis**: respostas do UNO e do OBS, mensagens do
datastore, arquivos indicados no inspetor e qualquer mensagem que chegue pelo
OpenDeck (ver "Riscos do OpenDeck").

## O que o plugin faz

| Área | Medida |
| --- | --- |
| Token da API | validado (`[A-Za-z0-9_-]`, até 256) antes de entrar na URL; nunca aparece em logs, erros, Status ou backup padrão |
| Rede | só os hosts fixos do UNO; HTTPS e WSS com certificado verificado (padrão do Python e do `websockets`); redirecionamentos HTTP recusados; tempo limite em toda conexão |
| Tamanho | respostas da API até 4 MB; mensagens WebSocket até 16 MB (UNO, OBS) e 4 MB (OpenDeck); gravação maior que o `maxPayload` do datastore é recusada antes do envio |
| Limites do UNO | fila única respeita o `rateLimitInfo` do login (requisições/s e bytes/min); gravações não são repetidas sozinhas após timeout |
| Arquivos | caminho absoluto, extensão esperada (.txt/.csv/.tsv; .json no backup), arquivo regular, até 10 MB, UTF-8 |
| Backup | permissão 600; nunca sobrescreve arquivo que não seja backup do plugin nem segue link simbólico; tokens, registro de control apps e senha do OBS só se você marcar |
| OBS | a senha não trafega: autenticação por desafio SHA-256 do obs-websocket 5; host e porta validados antes de virar URL, venham da página de configurações ou de um backup |
| Página de configurações | aberta pela engrenagem em **Plugins**; servida só em `127.0.0.1`, porta aleatória, fecha após 10 min parada ou com o plugin; token aleatório no fragmento da URL (o navegador não o envia) e exigido no cabeçalho `X-UNO-Token`; `Host` e `Origin` precisam ser a própria página; só JSON até 64 KiB, no máximo 200 gatilhos, 50 grupos e nomes de 60 caracteres; CSP estrita, sem cache e sem referrer; nenhuma requisição registrada; a senha salva e os tokens registrados nunca voltam para a página (ela vê só `app_id` e nome); um token novo só entra no registro depois de responder a `GetOverlays` |
| Automações globais | gatilhos e grupos validados campo a campo (evento e função de listas fixas, atraso 0–30 000 ms, tempo −30 a 30 s); chaves globais do plugin (`OWNED`) não são desfeitas por uma cópia antiga vinda de um inspetor; o log de cada gatilho não leva token |
| Idioma | o `settings.json` do OpenDeck é só lido, até 1 MB, e só o campo `language` é usado; valor desconhecido vira inglês |
| Manual (pipeline) | gerado pelo WeasyPrint 57.2 do Debian 12 só a partir de arquivos do repositório; o carregador de recursos recusa tudo fora de `docs/manual` (sem rede); veja "Riscos aceitos" |
| Inspetor | sem `innerHTML`, `eval` ou `localStorage`; textos vindos do UNO entram como texto |
| Erros | mensagens previstas dizem o que fazer; erro inesperado aparece genérico, com o tipo só no log |
| Código | sem `shell=True`, `pickle`, `yaml` ou `eval`; exceção genérica só nas bordas (conexões, tarefas), anotada; nenhuma telemetria |
| Dependência | `websockets` 15.0.1 vendorizado, idêntico byte a byte ao wheel oficial (SHA-256 fixado; o build confere) |

## Riscos aceitos

- **Token no caminho da URL.** A App API do UNO usa
  `/apiv2/controlapps/{token}/api`; o OWASP ASVS 5.0 (14.2.1) recomenda não ter
  dados sensíveis em URLs. Mitigação: só HTTPS, sem redirecionamento, token fora
  de logs e mensagens.
- **Segredos em texto no disco.** Token e senha do OBS ficam nas configurações do
  OpenDeck (JSON em `~/.config/opendeck/`), como todo plugin OpenDeck. Proteja a
  conta do computador e os backups.
- **websockets 15.0.1.** A 16.1 passou a remover o cabeçalho `Authorization` em
  redirecionamentos entre origens; este plugin não envia esse cabeçalho. A 17
  exige Python 3.11+, e o plugin suporta 3.10. A consulta a bases de
  vulnerabilidades (OSV) não pôde ser feita deste ambiente; confira antes de
  atualizar.

- **Token da página de configurações na linha de comando.** O plugin abre a
  página com o navegador padrão (`xdg-open`), e a URL com o token fica visível
  para outros usuários do mesmo computador na lista de processos enquanto o
  navegador abre. Mitigação: o token vale só enquanto a página está aberta (até
  10 min parada), a página só aceita conexões locais e nunca mostra a senha.

- **WeasyPrint 57.2 do Debian 12 no pipeline.** O Debian Security Tracker lista
  CVE-2025-68616, CVE-2026-49452 e CVE-2026-55073 abertos para essa versão. O
  manual não é instalado com o plugin: só o pipeline usa o WeasyPrint, com HTML
  montado de arquivos do próprio repositório, CSS inline (sem
  `write_pdf(stylesheets=…)`), sem `xmp_metadata` e com carregador que só aceita
  arquivos de `docs/manual`. Quem altera esses arquivos já tem escrita no repositório.
- **Traduções sem revisão humana** (ja, zh-CN, ko). Um texto mal traduzido pode
  confundir; as chaves e os marcadores `{nome}` são conferidos por
  `scripts/build_i18n.py`.

## Riscos do OpenDeck (fora do alcance do plugin)

Conferidos no código do OpenDeck (commit `7cc07942`):

- O WebSocket dos plugins (porta **57116**) e o servidor HTTP dos inspetores
  (porta **57118**) escutam em **todas as interfaces** (`0.0.0.0`)
  (`src-tauri/src/plugins/mod.rs`, `webserver.rs`).
- O WebSocket não autentica quem se registra como plugin ou inspetor
  (`src-tauri/src/events/mod.rs`). Um computador da rede que alcance a porta pode
  mandar mensagens ao plugin como se fosse o inspetor: por exemplo, pedir a
  prévia de um arquivo .txt/.csv que você consiga ler.
- O servidor HTTP entrega qualquer arquivo da pasta de configuração do OpenDeck,
  onde ficam as configurações com tokens, com `Access-Control-Allow-Origin: *`;
  no modo desenvolvedor, qualquer arquivo do disco (`webserver.rs`).
- O OpenDeck injeta um `<script>` inline no HTML de cada inspetor, o que impede
  uma CSP com `script-src 'self'` no inspetor.

Para ver em quais endereços as portas estão abertas no seu computador:

```sh
ss -ltn '( sport = :57116 or sport = :57118 )'
```

`0.0.0.0` ou `*` na coluna *Local Address* significa que outros computadores da
rede alcançam essas portas se o firewall permitir.

## Relatar um problema

Abra uma issue no repositório do projeto **sem** colar tokens, senhas, backups ou
logs com nomes de pessoas. Descreva a versão, o passo a passo e o efeito.
