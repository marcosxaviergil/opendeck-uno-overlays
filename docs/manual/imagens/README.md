# Imagens do manual

O manual (`scripts/build_manual.py`) procura cada imagem pelo nome, nesta ordem:

1. `docs/manual/imagens/<idioma>/<nome>` (captura de tela de um idioma, por exemplo `ja/inspetor_overlay.jpg`);
2. `docs/manual/imagens/<nome>` (a mesma imagem para todos os idiomas).

Se não achar, o PDF mostra uma caixa com `<nome>` no lugar, e o build lista no log as imagens que faltam.
Para substituir, coloque o arquivo com o mesmo nome aqui e gere o manual de novo (ou publique uma nova versão).

Imagens usadas hoje:

| Nome | O que mostrar |
| --- | --- |
| `botao_instalar_plugins.jpg` | OpenDeck: Plugins → Install from file |
| `inspetor_overlay.jpg` | Inspetor de uma tecla Overlay, com os **?** de ajuda |
| `engrenagem_plugins.jpg` | OpenDeck: cartão UNO Overlays em Plugins, com a engrenagem verde |
| `pagina_configuracoes.jpg` | Página de configurações do plugin no navegador |

Formatos aceitos: `.jpg`, `.jpeg` e `.png`; o nome só pode ter letras, números, `_`, `.` e `-`.
