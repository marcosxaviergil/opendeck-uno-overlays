# Forgejo: CI e releases

## O que o workflow faz

`.forgejo/workflows/build.yaml` roda **só** num push de **tag de versão** (`v2.0.0`);
push em branch e pull request não disparam nada. Ele confere as ferramentas
(`make tools`), faz lint (inclusive os catálogos de idiomas), testes Python, teste
do inspetor (pulado sem Playwright), build do plugin, o manual em PDF dos 9 idiomas
(`scripts/build_manual.py`, WeasyPrint e fontes Noto CJK do Debian), conferência do
pacote (`launch.sh --version` e `SHA256SUMS`) e publica a **release** dessa versão
com dois anexos, o ZIP do plugin e `UNO-Overlays-<versão>-Manual.pdf`, as notas do
`CHANGELOG.md` e o SHA-256 dos dois. Tag da mesma versão de novo: a release anterior
e os anexos dela são apagados e só o build mais novo fica. Se a tag foi movida para
outro commit enquanto o job rodava, o job não publica nada (confere
`BUILD_COMMIT` contra o commit da tag). Nenhum artefato é enviado e nenhum segredo é necessário: a etapa usa
o token automático do job, que pode escrever no próprio repositório. A tag precisa
ser igual à versão do `manifest.json`, com `v` na frente; senão, a etapa falha.

Requisito do runner: label `docker` (troque só o `runs-on` se o seu usa outro).

## Nova versão a partir de uma pasta extraída (sem apagar nada)

`scripts/forgejo_publish.py` envia esta pasta como **um commit novo por cima do
histórico remoto**, com a tag `v<versão do manifest.json>`. Histórico, tags,
releases e execuções do Actions anteriores continuam lá; arquivos que não existem
mais na pasta saem só no commit novo.

```sh
python3 scripts/forgejo_publish.py --server https://forgejo.example --repo dono/nome
```

- Roda `scripts/build.py` antes (versões, vendor, `SHA256SUMS`).
- Para sem mudar nada se a release dessa versão já existe: suba a versão.
- Se a tag existe **sem** release (build que falhou), a tag passa para o commit novo,
  só se o commit antigo estiver no histórico, com `--force-with-lease`.
- O token vem do credential helper do git (o mesmo de `forgejo_reset.py`, abaixo) e
  chega ao git por variáveis `GIT_CONFIG_*`, nunca por linha de comando ou log.
- Precisa de `git config user.name` e `user.email` configurados.
- Antes de mover uma tag, confira em **Actions** que nenhum job está rodando.

## Nova versão, dia a dia (num clone)

```sh
git commit -am 'UNO Overlays 2.0.1'
git tag -a v2.0.1 -m 'UNO Overlays 2.0.1'
git push origin main v2.0.1
```

Refazer o build da mesma versão (substitui a release):

```sh
git tag -fa v2.0.1 -m 'UNO Overlays 2.0.1'
git push --force origin v2.0.1
```

## Zerar o repositório remoto e enviar este projeto

`scripts/forgejo_reset.py` apaga o repositório no Forgejo (commits, branches, tags,
releases, execuções e logs do Actions, issues, segredos e runners registrados só
nele) e o cria de novo com a mesma visibilidade e descrição, Actions e releases
ligados. Depois envia esta pasta como um único commit em `main` com a tag da versão,
o que dispara o workflow e publica a release. Antes de apagar, salva um espelho do
repositório antigo ao lado da pasta (`<nome>-backup-<data>.git`).

```sh
python3 scripts/forgejo_reset.py --server https://forgejo.example --repo dono/nome
```

- Usa o token salvo no credential helper do git (o mesmo que o `git push` usa). Se
  não houver token salvo, ou se o salvo for recusado (por exemplo, uma senha antiga),
  pede o token uma vez, sem mostrar o que é digitado, e o entrega ao helper: nas
  próximas vezes não pergunta. Escopos: escrita em `repository` e `user` (e
  `organization`, se o dono for uma organização). O token não vai para linha de
  comando nem log; em disco, fica onde o seu helper guarda (o helper `store` grava em
  texto puro em `~/.git-credentials`).
- Os pedidos à API usam User-Agent próprio: um Cloudflare na frente do Forgejo pode
  recusar o User-Agent padrão do Python com HTTP 403 (erro 1010).
- Só apaga depois que você digita o nome do repositório.
- Recusa uma pasta que já tenha `.git`: use uma cópia recém-extraída do projeto.
- Se o runner foi registrado só neste repositório, ele é apagado junto: registre de
  novo depois. Runners do usuário, da organização ou da instância não são afetados.
