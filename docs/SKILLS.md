# Skills usadas nas versões 1.0.0 e 2.0.0

Skills de agentes publicadas no GitHub, escolhidas por área em 29/09/2026. Cada
uma foi lida no commit indicado (clones rasos); nenhum script delas foi
executado. Aplicamos as **regras**, não os pipelines: várias supõem web SaaS,
pytest ou TypeScript, e este projeto é um plugin desktop em Python 3.10 com
`unittest`. O ponytail veio por último, como pedido.

## Estrutura do código

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [wshobson/agents](https://github.com/wshobson/agents) `python-development` (python-project-structure, python-design-patterns) @ `156b7a5e`, MIT | "Group related code that changes together"; dividir quando um arquivo "Handles multiple unrelated responsibilities"; `__all__` ("Unlisted members are internal"); imports absolutos; camadas que só dependem das de baixo | `uno/runtime/` (14 módulos), `__all__` em todo módulo, [ARCHITECTURE.md](ARCHITECTURE.md) |
| [mattpocock/skills](https://github.com/mattpocock/skills) `codebase-design` @ `d81f3a18`, MIT | "Design **deep modules**"; teste da exclusão (nada de repassadores); "Accept dependencies, don't create them" | `uno/clock.py` (regras puras do relógio), `Datastore`, fila; `Runtime(send, uuid, api_factory, store_factory)` recebe dependências, o que permite os emuladores dos testes |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) `code-simplification`, `code-review-and-quality` @ `2686b620`, MIT | "Make one simplification at a time. Run tests after each change."; "The Rule of 500" (divisões grandes por automação); nomes sem abreviações genéricas | divisão do runtime e do inspetor feita por scripts e testada a cada passo |
| [wondelai/skills](https://github.com/wondelai/skills) `clean-code` @ `c1729964`, MIT | "The caller should be above the callee"; constantes no topo; "One word per concept" | ordem dentro dos arquivos ([ARCHITECTURE.md](ARCHITECTURE.md), "Convenções") |

## Segurança

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [trailofbits/skills](https://github.com/trailofbits/skills) `sharp-edges`, `insecure-defaults` (referências), `supply-chain-risk-auditor` @ `82fe8226`, CC-BY-SA-4.0 | valores vazios que passam em checagens; falhas silenciosas; permissões de arquivo; o vendorizado não é visto por auditores de manifesto: conferir à mão | `uno/files.py` (caminho, tamanho, 600), `except` estreitos; `scripts/build.py` confere o `websockets` contra o wheel oficial |
| [getsentry/skills](https://github.com/getsentry/skills) `security-review` @ `8ca68795`, CC-BY-SA-4.0 (pasta da skill) | só achados de alta confiança; mensagens WebSocket e respostas de API são entrada não confiável; caminho vindo do usuário | validação de respostas do UNO/OBS; regras de caminho no RPC do inspetor |
| [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) `owasp-security` @ `8ac7965c`, MIT | ASVS 5.0: 14.2.1 (nada sensível em URL), 16.5.1 (erro genérico ao usuário, detalhe no log); dependências com hash | token na URL documentado como risco aceito; erro inesperado genérico; wheel com SHA-256 fixado |
| [openai/skills](https://github.com/openai/skills) `security-best-practices` (front-end) @ `49f948fa`, Apache-2.0 | JS-XSS-001 (sem `innerHTML` com dados de rede), JS-STORAGE-001 (segredos fora do Web Storage), CSP | inspetor sem `innerHTML` e sem `localStorage`; CSP impossível pelo script que o OpenDeck injeta ([SECURITY.md](../plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md)) |

Resultado em [SECURITY.md](../plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/SECURITY.md).

## LGPD

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [goul4rt/lgpd-skills](https://github.com/goul4rt/lgpd-skills) `lgpd-data-mapping`, `lgpd-international-transfer`, `lgpd-retention-erasure`, `lgpd-audit-logging` @ `d85d79ab`, MIT | inventário de dados (Art. 5º X, 37); transferência internacional (Art. 33); retenção e eliminação (Art. 16, 18 VI); "PII out" nos logs; incidente em 3 dias úteis (Res. CD/ANPD 15/2024) | [PRIVACY.md](../plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/docs/PRIVACY.md); **Clear log**; **Delete stored scene**; log sem conteúdo |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) `gdpr-compliant` @ `997e95a6`, MIT | logs sem dados pessoais e sem segredos; privado por padrão; testes com dados fictícios | backup sem tokens por padrão; nomes fictícios nos testes |
| [DanielSunami/gerador-lgpd](https://github.com/DanielSunami/gerador-lgpd) @ `d7e417c5`, MIT | autores que não recebem dados não são controlador nem operador; não inventar encarregado, base legal ou prazos; mapear cada direito do Art. 18 | papéis e tabela de direitos no PRIVACY.md |

As citações da lei foram conferidas com a cópia do Planalto incluída em
[manfredjr/legal-br](https://github.com/manfredjr/legal-br) @ `583853a8` (o site do
Planalto estava bloqueado para download direto neste ambiente).

## Usabilidade e acessibilidade

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) `web-design-guidelines` @ `063bee94` (regras em [web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines) @ `e3d624ba`), MIT | "Form controls need `<label>` or `aria-label`"; `:focus-visible`; "`color-scheme: dark`"; `autocomplete="off"` fora de login; erro com o próximo passo; movimento reduzido | `pi/css/styles.css`, rótulos em todo controle, mensagens de erro; o inspetor não tem animação |
| [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) `accessibility` @ `afa8da94`, MIT | contraste 4.5:1 (texto) e 3:1 (componentes); alvos de 24 × 24 px; não depender só de cor | cores do CSS; botões de 24 px; Status com cor **e** texto |
| [content-designer/ux-writing-skill](https://github.com/content-designer/ux-writing-skill) @ `98cacde4`, MIT | "[What failed]. [Why/context]. [What to do]." | textos de `UnoError` |

[mgifford/accessibility-skills](https://github.com/mgifford/accessibility-skills)
(`forms`, AGPL-3.0) foi só lida, sem copiar arquivos.

## Testes

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [obra/superpowers](https://github.com/obra/superpowers) `test-driven-development`, `verification-before-completion` @ `8ca22dba`, MIT | "Derive expectations independently"; "Mirror real data completely"; checagem por mutação; nenhuma afirmação de pronto sem rodar tudo | eventos no formato do OpenDeck (`GenericInstancePayload`, `tests/support.py`); mutações conferidas (permissão 600, rótulo removido) |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) `test-driven-development` @ `2686b620`, MIT | pirâmide pequeno/médio (sem I/O / só localhost); testar estado, não interações; evitar esperas fixas; zero erros no console | `test_units.py` puro; demais em loopback; `eventually()`; teste do navegador falha com erro ou aviso no console |
| [anthropics/skills](https://github.com/anthropics/skills) `webapp-testing` @ `8a1541c4`, Apache-2.0 | HTML estático por `file://`; capturar o console | `tests/pi/inspector.test.cjs` |

## Documentação

| Skill | Regras aplicadas | Onde |
| --- | --- | --- |
| [joshuadavidthomas/agent-skills](https://github.com/joshuadavidthomas/agent-skills) `crafting-effective-readmes` @ `516dee7a`, MIT | "Who will read this"; requisitos, instalação, uso e testes; conferir com o estado real do projeto | README do plugin (usuário) e da raiz (desenvolvedor) |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) `documentation-and-adrs` @ `2686b620`, MIT | Keep a Changelog; comentar o porquê | `CHANGELOG.md`; comentários com fonte |

## Por último: ponytail

[dietrichgebert/ponytail](https://github.com/dietrichgebert/ponytail) @ `e3ba2aa6`, MIT:
`ponytail-audit` no repositório inteiro depois de todas as outras etapas. O que
ele protege, não corta: validação nas fronteiras, tratamento de erro que evita
perda de dados, segurança, acessibilidade e o que foi pedido.

Resultado, aplicado e testado (69 testes Python + 35 do inspetor passando):

- **Inspetor: −189 linhas** (1 882 → 1 693). `utils.js` removido (o seletor de
  tempo virou opções do `select()` comum); `FormBuilder` sem ramos duplicados;
  `new Option` no lugar de opções montadas à mão; o ajudante `group()` no lugar de
  9 fieldsets repetidos; uma só fábrica de controles (`choose`, `textBox`);
  listas `FUNCTIONS`/`TIMER_OPERATIONS` reaproveitadas; atribuições a `window`,
  ids e CSS sem uso removidos. Ganho junto: campo do modelo com título oculto
  agora tem nome acessível (`aria-label`).
- **Plugin Python: −50 linhas** (3 881 → 3 831). Envio ao inspetor num só
  método (`to_inspector`); `field_spec` duplicava `model_field`; repassadores
  trocados por lambdas nas tabelas; `textwrap.wrap` (stdlib) no lugar da quebra
  de linha feita à mão; constantes sem uso ou repetidas (`TRIGGERS`, `GOAL_STATE`).
- **Testes**: ajudantes repetidos trocados pelos de `Case` (`request`,
  `set_global`, `show`); opção do emulador que nenhum teste usava removida.
- O audit também achou um **erro real**: o passo "OBS scene" da Macro chamava um
  método que a reorganização tinha renomeado. Corrigido, com teste que falhava
  antes da correção (`test_obs`) e um teste novo que roda todos os tipos de
  passo da Macro (`test_show_control`).

Mantidos de propósito: a fila e os limites do UNO, as validações de token e de
arquivo, o `websockets` vendorizado (a stdlib não tem cliente WebSocket).

## Página de configurações (30/09/2026)

A mudança da conexão com o OBS para uma página própria passou pelas mesmas skills:

- **Estrutura**: o servidor da página é um adaptador (`uno/localpage.py`) e a regra
  fica num mixin (`runtime/settingspage.py`); a validação do endereço do OBS mora no
  adaptador do OBS (`check_address`) e é usada pela página e pelo `configure_obs`,
  um único ponto por onde toda configuração passa.
- **Segurança**: nova porta aberta tratada como fronteira de confiança (sharp-edges,
  OWASP ASVS, getsentry): só `127.0.0.1`, token por sessão com `compare_digest` em
  bytes, `Host`/`Origin`, corpo limitado, CSP estrita, senha só de escrita, texto
  "false" não liga nada (sharp-edges: `"false"` é verdadeiro em muitas linguagens).
- **LGPD**: a senha não volta para a página e não entra no log; PRIVACY.md atualizado.
- **Usabilidade**: formulário com `label` em todo campo, Enter envia, estado da
  conexão em `role="status"`, mensagens com o próximo passo.
- **Testes**: cada regra nova tem teste, conferido por mutação (5 mutações, 5 falhas).
- **Ponytail** (revisão do diff): biblioteca padrão para servidor e navegador
  (`http.server`, `webbrowser`), nenhuma dependência nova, página sem framework.

## Forgejo: release por tag e reset do remoto (30/09/2026)

- **Segurança** (sharp-edges, insecure-defaults, OWASP): o token pessoal vem do
  credential helper do git ou é lido sem eco uma vez e entregue a ele; nunca vai para
  linha de comando (visível em `/proc`) ou log; o git o recebe por variáveis
  `GIT_CONFIG_*`, limitado ao host do Forgejo. Nada é apagado
  sem digitar o nome do repositório, e um espelho do histórico antigo fica salvo
  antes. A release usa o token automático do job, sem segredo guardado.
- **Testes**: um Forgejo de mentira com `git http-backend` que só aceita push com o
  token como senha e que, como o Cloudflare (erro 1010), recusa o User-Agent padrão do
  Python; 4 mutações conferidas (sem o cabeçalho de autenticação, sem apagar a release
  anterior, User-Agent padrão, sem salvar o token no helper), todas falham.
- **Ponytail**: biblioteca padrão (`urllib`, `getpass`, `subprocess`), nenhuma action
  nova além do checkout já usado, nenhum artefato.

## Versão 2.0.0 (01/10/2026)

As mesmas skills, nos mesmos commits: em 01/10/2026 o `HEAD` de cada repositório foi
conferido com `git ls-remote`. Só dois mudaram: `getsentry/skills` (`d18b7aa8`; a
`security-review` mudou só o cabeçalho, e entrou a `gha-security-review`, usada abaixo no
workflow) e `github/awesome-copilot` (`d6131471`; a `gdpr-compliant` não mudou).

- **Estrutura** (wshobson, mattpocock, addyosmani, wondelai): regras puras novas em
  módulos profundos e testáveis sozinhos (`uno/automations.py`, `uno/i18n.py`); um mixin
  por razão de mudança (`runtime/automation.py`, `runtime/reveal.py`); a migração da 1.0.0
  num só lugar (`adopt_key`); scripts usam a lista de idiomas e o catálogo do próprio
  plugin, sem cópia.
- **Segurança** (trailofbits sharp-edges e insecure-defaults, getsentry, OWASP ASVS 5.0,
  openai): o token fica uma vez, no registro; gatilhos, grupos, backup e log usam o
  `app_id`; a página nunca devolve um token e aceita um novo só depois de o UNO responder;
  listas e corpo com limite; valores fora da faixa são cortados, não confiados; o arquivo de
  idioma do OpenDeck é só lido, com tamanho máximo; o WeasyPrint do pipeline só lê arquivos
  do repositório (três CVEs abertos documentados em SECURITY.md). Sharp edge achado no
  limitador do datastore: atraso de rede podia fazer o servidor contar uma gravação a mais
  por segundo; a nova janela agora começa 0,1 s depois.
- **gha-security-review** no `.forgejo/workflows/build.yaml`: gatilho só `push` de tag
  `v*` (exige escrita no repositório, fora do modelo de ameaça da skill); o único `${{ }}`
  novo (`github.sha`) está em `env:` de passo, que a skill classifica como seguro; checkout
  fixado por SHA, sem credencial persistida. Nenhum achado.
- **LGPD** (goul4rt, awesome-copilot, DanielSunami): inventário do PRIVACY.md com os dados
  novos (registro de control apps, nomes, gatilhos, grupos, configurações guardadas, idioma);
  minimização (`app_id` no lugar do token); eliminação na página; contato pela issue do
  projeto; backup sem segredos por padrão.
- **Usabilidade e acessibilidade** (vercel, addyosmani accessibility, ux-writing): ajuda
  **?** em todo campo, aberta no hover e no foco, fechada com Esc, ligada por
  `aria-describedby` (WCAG 1.4.13), conferida no teste do navegador; listas no padrão
  "Adicionar" já usado pelo inspetor; mensagens no formato "o que houve. o que fazer"; toda
  mensagem ao usuário passa por `tr()` (teste por AST).
- **Testes** (obra/superpowers, addyosmani TDD, anthropics webapp-testing): os testes novos
  falharam contra o código da 1.0.0 antes da mudança; mutações conferidas
  ([TESTING.md](TESTING.md)); testes repetidos em Python 3.10–3.13 e sob carga paralela;
  inspetor em pt-BR e página de configurações no Chromium.
- **Documentação** (crafting-effective-readmes, documentation-and-adrs): README do plugin
  para quem usa (página de configurações, limitações, vindo da 1.0.0), README da raiz para
  quem desenvolve, CHANGELOG só com as diferenças para a 1.0.0, manual em PDF nos 9 idiomas
  com a mesma ajuda do inspetor.

### Por último: ponytail-audit (repositório inteiro)

Achados aplicados, com os testes passando depois de cada um:

- os três scripts do Forgejo usam um só cliente HTTP (`Forgejo` em `forgejo_reset.py`);
- o manual usa o catálogo do plugin (`uno.i18n`) e a lista de idiomas dele, como o
  `build_i18n.py`; rótulos do manual que nunca eram lidos saíram;
- `language()` sem uso fora dos testes, `shown_value`/`hidden_value` (uma função só),
  `rpc_obs_list` igual a `page_obs`, `app_id` calculado várias vezes, rota 404 conferida
  duas vezes na página, `clean_trigger` com variável intermediária, texto "This overlay"
  que nunca aparecia, reexportação de `app_id` só para teste;
- nos testes, a subida do OBS emulado e a entrada em contextos assíncronos ficaram em
  `support.Case` (`start_obs`, `enter`).

Um achado do audit estava errado e o teste pegou: tirar o primeiro `server.last` da página
deixava a thread ler o campo antes de ele existir; voltou, com comentário. Mantidos de
propósito: `UnoApi` no inspetor (prende o token, já mantido na 1.0.0), `store_factory`
(injeção usada pela arquitetura), funções repetidas entre `settings.js` e `inspector.js`
(a página não carrega o inspetor; um arquivo novo para 10 linhas seria mais estrutura, não
menos).

O audit também apontou três erros, corrigidos com teste que falhava antes: o idioma do
registro do OpenDeck não chegava ao runtime (`main.py`), a página de configurações perdia
uma seção alterada nos mesmos 500 ms de outra, e seis mensagens não passavam por `tr()`.
Depois, uma corrida achada ao rodar a suíte sob carga: um control app esquecido na página
voltava ao registro quando a conexão em tempo real aberta para um gatilho terminava depois.

## GitHub Actions (31/10/2026)

Pedido: o mesmo CI e a mesma release no GitHub, sem mudar o que já funciona no Forgejo, e o
README da raiz nos 9 idiomas do manual. Nenhum arquivo do Forgejo (`.forgejo/workflows`,
`scripts/forgejo_*.py`) mudou; o plugin, o manual e o CHANGELOG também não. As skills do
catálogo do projeto, cada uma no seu escopo:

- **Pesquisa e evidências** (deep-research, research-methodology, audit): cada decisão com
  fonte primária em [SOURCES.md](SOURCES.md) (seção GitHub Actions). Conferido antes de
  escrever: o Forgejo só lê `.github/workflows` sem `.forgejo/workflows`, então os dois
  convivem; o `GITHUB_TOKEN` não chega ao ambiente sozinho; o SHA e o runtime do
  `actions/checkout` v6.1.0 no próprio repositório.
- **Arquitetura** (software-architecture-analysis, software-architecture, codebase-design):
  um adaptador por forja, mesma regra. `scripts/github_release.py` reaproveita `notes()` e os
  caminhos de `forgejo_release.py` e o User-Agent de `forgejo_reset.py`, sem mudar esses
  arquivos; o workflow do GitHub é cópia do Forgejo e `tests/test_ci.py` impede que os passos
  divirjam.
- **API e integração** (api-design-and-evolution, backend-engineering): rascunho → anexos →
  publicar, que funciona com e sem releases imutáveis e nunca deixa release pública sem os
  arquivos; reexecução idempotente (apaga a release e o rascunho da mesma tag);
  `BUILD_COMMIT` contra tag movida; `concurrency` contra execuções simultâneas da mesma tag.
- **Qualidade** (wshobson python-development, clean-code, code-simplification): só biblioteca
  padrão, nenhuma dependência nova; nomes e ordem como nos scripts do Forgejo.
- **Segurança** (secure-software-engineering, sharp-edges, insecure-defaults, getsentry
  security-review e gha-security-review, OWASP ASVS 5.0, openai security-best-practices):
  gatilho só em push de tag `v*`; `permissions: {}` no workflow e só `contents: write` no
  job; token só no `env:` do passo da release, nunca em linha de comando ou log; nenhum
  `${{ }}` dentro de `run:`; checkout fixado por SHA, sem credencial persistida; sem TLS o
  script não envia o token (`http` só em loopback, para o teste); URL de upload conferida antes
  do uso. `actionlint` sem achados; `zizmor` (persona auditor) só aponta a imagem
  `node:22-bookworm-slim` sem digest: risco aceito, é a mesma imagem do Forgejo e o modelo do
  projeto, e fixar o digest congelaria as correções de segurança do Debian.
- **LGPD** (lgpd-skills, gdpr-compliant, gerador-lgpd): o workflow não trata dados pessoais;
  release só com notas do CHANGELOG e SHA-256; PRIVACY.md não muda.
- **Testes** (superpowers, TDD, verification-methodology): `tests/test_github.py` escrito
  antes do script e visto falhando; GitHub falso que, como um repositório com releases
  imutáveis, recusa anexo depois de publicar; 7 mutações no script e 5 no workflow, todas
  pegas ([TESTING.md](TESTING.md)).
- **Documentação** (crafting-effective-readmes, code-documenter TerminalSkills → 26zl
  coding-style → code-documenter Jeffallan → comment-analyzer → comment-cleanup): README da
  raiz com as mesmas seções em pt-BR, en, es, it, de, ja, zh-CN, ko e fr, na ordem do manual,
  com índice de idiomas (âncoras conferidas com o `github-slugger`); [GITHUB.md](GITHUB.md)
  para quem publica; docstrings com o contrato da API e comentários conferidos contra o código
  (um comentário sobre a ordem da lista de releases, sem fonte, saiu).

### Por último: ponytail-audit

- **Aplicado:** o laço de até 5 tags aninhadas virou um nível (o que `git tag -a` gera), com
  erro claro para o resto; a mutação que sobreviveu nesse ramo ganhou teste.
- **Mantido de propósito:** a repetição de ~15 linhas (versão, arquivos, corpo da release)
  entre `forgejo_release.py` e `github_release.py`, porque juntar exigiria mudar o script do
  Forgejo, fora do pedido; `concurrency` e `BUILD_COMMIT` juntos (um evita duas execuções ao
  mesmo tempo, o outro evita build antigo publicado depois do novo).
- **Achado anterior, não alterado (fora do pedido):** `ruff` 0.16 aponta 6 avisos de estilo em
  arquivos do plugin (5 × W292, fim de arquivo sem quebra de linha; 1 × E501, linha com 121
  colunas em `uno/runtime/automation.py`). O CI não instala o `ruff`, então não falha por isso.
