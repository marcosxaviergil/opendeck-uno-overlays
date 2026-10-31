# Evolução analisada

A decisão funcional segue a última correção consolidada; recursos removidos
explicitamente não foram reintroduzidos. O número de versão do README permaneceu
3.1.0 em todos os anexos, por isso a comparação foi feita no código e nos manifests.

| Anexo | Mudança observada e decisão para OpenDeck |
| --- | --- |
| exemplo_de_site_controle_overlay.zip | Captura de recursos do Control App; referência da estrutura de slots com id, name e payload. Não é um plugin instalável. |
| plugin.zip | Captura HTML do Quiz Show Stream Pack e seus recursos. A criação de New Slot a partir de subCompPayloads e a seleção currentSlotId confirmam a lógica de presets. Conteúdo pessoal da captura não foi distribuído. |
| v3.1.1-Funcionando-Perfeitamente-Sem-AutoFechamentox | Cinco ações, formulário dinâmico e descoberta numérica por modelo + conteúdo + títulos de campos irmãos. Já contém o workaround GetOverlayContent/SetOverlayContent para números em TEXT. |
| v4.0.0 | Smart toggle, Delay/Auto Close e utilitários compartilhados; elimina overlay-manager.js. |
| v4.0.1 | Manifest interno diz **4.1.0**. Carrega modelo e conteúdo remoto e introduz guarda de sincronização para evitar ciclo de settings. |
| v4.2.0 | keyDown e dialDown acionam; dialRotate considera sinal e magnitude. Manifest usa Knob, convertido para Encoder no OpenDeck. |
| v4.3.0 | Knob Control com três gestos independentes, reaproveitando operações numéricas e toggle. |
| v5.0.0 | Display, módulo PIData e SDK; timers por gesto, polling e ícone P&B quando oculto. |
| v5.0.1 | Adiciona formulários/conteúdo para Toggle Overlay de cada gesto do knob. |
| v5.0.1-fixed | Retira polling e P&B; Display passa a leitura pontual. Adiciona comparação de settings para suprimir eco. Preservado. |
| v5.0.1-fixed2 | Mesclagem/comparação recursiva, presets locais e temporizadores curtos de 1–4 segundos. |
| v5.0.1-fixed3 | Tanto presets locais quanto slots do servidor passam a aplicar + Take quando aplicável + Show; não ocultam no segundo clique. |
| v5.0.1-fixed3-save1 | Tentativa de salvar input/change e separar Live de presets. O handler onDynamicFormChanged referenciado não existe nesta versão. |
| v5.0.1-fixed4 | Troca por salvamento delegado com debounce e setActivePayload; introduz acidentalmente um literal `\1` onde deveria existir resolveActivePayload. |
| v5.0.1-fixed5 | Remove optional chaining/nullish coalescing para compatibilidade do WebView e melhora detecção de mudanças do token; o literal inválido ainda está presente. |
| v5_0_1-fixed6 | Restaura resolveActivePayload, priorizando o conteúdo salvo. Referência final da adaptação. |

## Correções adicionais necessárias na adaptação

- A versão final ainda tinha dois caminhos de salvamento: um deles atribuía
  `settings.content` mesmo durante a edição de um preset. O port tem um único
  destino por edição, mantendo Live e cada preset independentes.
- No inspetor original do knob, loadGestureModel sobrescrevia conteúdo salvo
  com valores remotos a cada reabertura. Agora o conteúdo salvo prevalece.
- O salvamento acontece em input/change, sem esperar um debounce perder a
  última edição ao fechar o inspetor. Respostas assíncronas de uma seleção
  anterior são descartadas antes de modificar o formulário.
- Ao editar um payload parcial, somente o campo editado é acrescentado ao
  patch. Campos JSON estruturados continuam sendo objetos/listas, sem virar
  a string `[object Object]`. Campos fora dos grupos também aparecem.
- `localStorage` foi substituído por get/setGlobalSettings do OpenDeck.
- A API continua usando PUT e os mesmos nomes/corpos de comandos do original.
  O transporte agora fica no processo Python para não depender de CORS no
  WebView; o inspetor reutiliza sendToPlugin/sendToPropertyInspector.
- Down/Up foram testados em pares. O port, como o original, executa no Down.
- Os timers passam a ser controlados por token/overlay, evitando que um botão
  antigo oculte um overlay que outro botão acabou de reabrir.

Os arquivos originais completos não são redistribuídos: este projeto contém os
componentes reaproveitados, sua adaptação e os hashes de proveniência abaixo.

## SHA-256 dos anexos analisados

```text
4a663147fb8e9e592a5def3137bafe2352c88eccfe0cc999fbfe93f203827ddd  exemplo_de_site_controle_overlay.zip
a03f35cab0a43333b09501a95fa9f705d417bc172aa2f02e1f8c95ced30ff89f  plugin.zip
c0586d71ed28fafdb28197c40ca17f0fb486584565a0a8e8eb9f3d30d6b6be7f  uno-overlay-plugin-v3.1.1-Funcionando-Perfeitamente-Sem-AutoFechamentox.zip
41d81acd1ff5e9fa5290a7d0071f6c011dda6a1bd40a5aa0f682b480f71a6458  uno-overlay-plugin-v4.0.0.zip
3151a06dd3f3d5b55cb814846be52b3ef20124f1ed757be0f7e747d508c8368c  uno-overlay-plugin-v4.0.1.zip
edfde7c55558d710a11f4ec0b0083a3c67911ef73b36ed037f08efe450bcf800  uno-overlay-plugin-v4.2.0.zip
0b7720dab7f06cd8762627bb5829f9391807315ce82ccb7fff4a3155df728c72  uno-overlay-plugin-v4.3.0.zip
4a84bd21b354f1d7ce8d3d3f7f8aab37347c3a3126afed3529350e7b934e055f  uno-overlay-plugin-v5.0.0.zip
d480bc4b24a40cd594ab7da5184463d1cc6d5cfd5b9ef3ceda23ea3d465f4033  uno-overlay-plugin-v5.0.1-fixed.zip
d6d08cf7e7f16147d493815defe6178ce99ab1d276f719444089146d843b4d4a  uno-overlay-plugin-v5.0.1-fixed2.zip
53e7d76db89a7f75f3abc3ef170a6627a18ce5bb0eef43844e17b3b0522435c3  uno-overlay-plugin-v5.0.1-fixed3-save1.zip
9b78f9e445c82b25ffa39d7e6eccea80308515aadc1b696f07a2d49ae934223c  uno-overlay-plugin-v5.0.1-fixed3.zip
ad313d1d45341d7353807c4828dba923e44597597b06e675e69356c997c2e204  uno-overlay-plugin-v5.0.1-fixed4.zip
09509d3b625d30d75a7eba498257886fab71765a1775de9befa363f5c84b5228  uno-overlay-plugin-v5.0.1-fixed5.zip
cf77b81a8f3f46f99052c03282d8f97acca1c6cda458f45e8e4b98fa554db158  uno-overlay-plugin-v5.0.1.zip
f420d73f8329f3ae5a2fb7343724b3de52e7f0b153deabcf0d3eb31759c1b48c  uno-overlay-plugin-v5_0_1-fixed6.zip
```
