# GitHub: CI e releases

## O que o workflow faz

`.github/workflows/build.yaml` é o mesmo pipeline de `.forgejo/workflows/build.yaml`
(veja [FORGEJO.md](FORGEJO.md)): roda **só** num push de **tag de versão** (`v2.0.0`), na
mesma imagem `node:22-bookworm-slim`, com os mesmos passos (ferramentas, lint, testes,
inspetor, build, manual dos 9 idiomas, conferência do pacote). Só mudam dois passos:

- **Checkout:** `actions/checkout` do GitHub, fixado por SHA (v6.1.0), sem credencial
  persistida.
- **Release:** `scripts/github_release.py` em vez de `scripts/forgejo_release.py`. Apaga a
  release (ou o rascunho deixado por uma execução que falhou) da mesma tag, cria um
  **rascunho** com as notas do `CHANGELOG.md` e o SHA-256 dos dois arquivos, anexa o ZIP do
  plugin e `UNO-Overlays-<versão>-Manual.pdf` e só então **publica**. A tag git fica. Se a tag
  foi movida para outro commit enquanto o job rodava, não publica nada (`BUILD_COMMIT`).

`tests/test_ci.py` falha se os passos dos dois workflows deixarem de ser iguais (exceto o
da release) ou se uma action não estiver fixada por SHA.

Os dois workflows convivem no mesmo repositório: o Forgejo só lê `.github/workflows` quando
**não existe** `.forgejo/workflows`, e o GitHub só lê `.github/workflows`. Cada forja roda o
seu.

## Permissões e segredos

- Nenhum segredo para criar. A etapa da release usa o `GITHUB_TOKEN` do job, entregue só a
  ela (`env:` do passo), com `permissions: contents: write`; o resto do workflow fica com
  `permissions: {}`.
- A permissão é pedida no próprio workflow, o que vale mesmo com o padrão do repositório em
  somente leitura (**Settings → Actions → General → Workflow permissions**). Só uma política
  de organização ou de empresa que proíba escrita ao `GITHUB_TOKEN` impede; aí a etapa falha
  com HTTP 403.
- Execuções da mesma tag esperam umas pelas outras (`concurrency`), sem cancelar.

## Releases imutáveis

Com **immutable releases** ligado no repositório, o GitHub não aceita anexos depois de
publicar: por isso os arquivos entram no rascunho e a publicação é o último passo. Depois de
publicada, a tag e os anexos ficam travados: refazer a mesma versão falha, suba a versão.
Sem essa opção (padrão), a mesma tag de novo substitui a release, como no Forgejo.

## Enviar ao GitHub por HTTPS

O push leva `.github/workflows/build.yaml`, e o GitHub recusa um token pessoal sem permissão
de workflow (`refusing to allow a Personal Access Token to create or update workflow ...
without workflow scope`). Token clássico: escopos `repo` (ou `public_repo`) e `workflow`.
Token fine-grained: neste repositório, **Contents** e **Workflows** em *Read and write*.
O git pede usuário e token (sem eco) e o credential helper guarda.

## Nova versão, dia a dia (num clone)

```sh
git commit -am 'UNO Overlays 2.0.1'
git tag -a v2.0.1 -m 'UNO Overlays 2.0.1'
git push origin main v2.0.1
```

Refazer o build da mesma versão (substitui a release; não funciona com releases imutáveis):

```sh
git tag -fa v2.0.1 -m 'UNO Overlays 2.0.1'
git push --force origin v2.0.1
```

Com os dois remotos no mesmo clone (por exemplo `origin` no Forgejo e `github` no GitHub),
envie a tag para cada um: cada forja publica a sua release.
