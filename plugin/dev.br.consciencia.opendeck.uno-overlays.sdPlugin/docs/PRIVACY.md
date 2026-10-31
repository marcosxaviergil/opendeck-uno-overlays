# Privacidade e LGPD

Este documento mostra quais dados o plugin trata, para onde vão e como apagá-los,
para quem usa o plugin cumprir a Lei 13.709/2018 (LGPD). Não é parecer jurídico:
as interpretações abaixo estão marcadas como tais.

## Papéis (Art. 5º, VI e VII)

| Quem | Papel | Por quê |
| --- | --- | --- |
| Você (quem opera a transmissão) ou a instituição | **controlador** | decide quais nomes e textos vão para os overlays |
| Singular.live / overlays.uno | **operador** do controlador | guarda e exibe o conteúdo dos overlays em seu nome |
| Autores do plugin | nenhum | o plugin roda no seu computador e **não envia nada aos autores**: sem telemetria, sem servidor próprio |

Interpretação: o Art. 4º, I exclui o tratamento "realizado por pessoa natural para
fins exclusivamente particulares e não econômicos"; transmissões institucionais
provavelmente não se encaixam nessa exceção.

## Dados tratados

| Dado | Onde fica | Vai para | Quanto tempo |
| --- | --- | --- | --- |
| Textos dos overlays (nomes, cargos, placares, legendas) | UNO; cópia em memória enquanto o plugin roda | UNO (HTTPS e WSS) | no UNO, conforme os termos do UNO; na memória, até fechar o OpenDeck |
| Linhas de fontes de dados (.txt/.csv ou lista digitada) | arquivo seu; lista nas configurações globais do OpenDeck | só os campos **mapeados** vão ao UNO | até você apagar a fonte ou o arquivo |
| Cenas (Scene) | configurações globais do OpenDeck | ficam no computador | até **Delete stored scene** |
| Token da API UNO e senha do OBS | configurações do OpenDeck (JSON em `~/.config/opendeck/`): o token na tecla e, uma vez, no registro de control apps das configurações globais; a senha é digitada na página de configurações do plugin e nunca é mostrada de volta | token: UNO; senha: só o OBS local | até você removê-los (a página tem **Remove the saved password** e remover control app) |
| Nome que você dá a um control app | configurações globais | fica no computador | até remover o control app |
| Gatilhos e grupos exclusivos | configurações globais: evento, cena do OBS, identificador curto do control app (`app_id`) e overlay | ficam no computador | até você apagá-los na página |
| Configuração guardada de Clock e Reveal Answer | configurações globais, por campo, sem token | fica no computador | substituída quando a tecla muda |
| Idioma e atraso das edições | configurações globais; o plugin **lê** só o campo `language` do `settings.json` do OpenDeck | ficam no computador | até você mudar |
| Log do Status | memória, últimas 200 linhas | fica no computador | até **Clear log** ou fechar o OpenDeck |
| Contador de chamadas | configurações globais, por dia | fica no computador | substituído a cada novo dia |
| Backup (Export) | arquivo JSON que você escolhe, permissão 600 | fica no computador | até você apagá-lo |

- O log e o contador nunca mostram o token: cada control app aparece como
  "UNO app" + 6 caracteres do SHA-256 do token (o mesmo `app_id` de gatilhos e
  grupos), mais o nome que você der a ele. O log registra comandos, eventos do OBS,
  decisões dos gatilhos e resultados, não o conteúdo dos campos.
- Edições no ar ficam em memória pelo atraso configurado (padrão 1 s) e são
  enviadas ao fechar o inspetor, ao mudar de campo, ao tocar a tecla ou no Panic;
  nada é descartado.
- O log do OpenDeck (`~/.local/share/opendeck/logs/plugins/`) recebe avisos sem
  token, URL ou conteúdo.
- Votos e totais de enquete são números agregados (interpretação: não identificam pessoas).

## Transferência internacional (Art. 33)

O conteúdo dos overlays vai para um serviço em nuvem de terceiros
(Singular.live / overlays.uno), que pode tratá-lo fora do Brasil. Consulte os
termos e a política de privacidade do UNO. Escolher a hipótese do Art. 33 que
permite a transferência cabe ao controlador (por exemplo, cláusulas-padrão
contratuais, II "b", ou o inciso IX).

## Princípios aplicados no código (Art. 6º e Art. 46)

- **Necessidade** (Art. 6º, III): de uma linha de CSV só vão ao UNO as colunas
  mapeadas ou usadas no *Format*.
- **Segurança** (Art. 46): HTTPS/WSS com certificado verificado, token validado
  e nunca registrado, backup com permissão 600 que não sobrescreve outros
  arquivos. Detalhes em [SECURITY.md](SECURITY.md).
- **Privacidade por padrão**: backup sem tokens, sem o registro de control apps e
  sem senha, a não ser que você marque a opção; recursos novos vêm desligados.
- **Minimização**: gatilhos, grupos e backups guardam o `app_id`, não o token; o
  token fica uma vez só, no registro.

## Direitos do titular (Art. 18) e como atendê-los

| Direito | Como fazer com o plugin |
| --- | --- |
| Confirmação e acesso (I, II) | veja o conteúdo no inspetor da tecla ou no Control App do UNO |
| Correção (III) | edite o campo no inspetor, a lista da fonte de dados ou o arquivo CSV/TXT |
| Eliminação (IV, VI) | **Delete stored scene** (tecla Scene), **Delete** na fonte de dados, apague a linha do arquivo, **Clear log** (tecla Status), remova control apps, gatilhos e grupos na página de configurações, apague o arquivo de backup e o conteúdo no Control App do UNO |
| Informação sobre compartilhamento (VII) | esta página: UNO (Singular.live) e, localmente, o OBS |

## Incidentes (Art. 48)

Se um token ou backup vazar: troque o token no UNO se o serviço permitir,
troque a senha do WebSocket do OBS e apague cópias do backup. Havendo risco ou
dano relevante aos titulares, o controlador comunica a ANPD e os titulares; a
Resolução CD/ANPD nº 15/2024 fixa o prazo de três dias úteis.

## OpenDeck

O OpenDeck, e não este plugin, coleta por padrão "minimal statistics (such as
operating system and plugins installed)" (código do OpenDeck, `src-tauri/src/main.rs`).
Para desligar: **Settings** → desmarque **Contribute statistics** (em português:
**Configurações** → **Contribuir com estatísticas**).

## Contato

Para exercer os direitos acima em relação ao plugin, abra uma issue no projeto
(sem colar tokens, backups ou dados pessoais). Os autores não recebem dados do plugin;
pedidos sobre o conteúdo dos overlays vão ao controlador e ao UNO.

## Testes

Os testes usam nomes fictícios e servidores locais; nenhum dado real é enviado.
