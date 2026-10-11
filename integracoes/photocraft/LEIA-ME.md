# PhotoCraft no projeto

O PSD é o contrato da composição: qualquer editor que abre PSD serve. O
PhotoCraft (https://github.com/storytold/photocraft, editor livre do tipo
Photoshop, sem IA generativa) é o editor da etapa de **acabamento**: camadas de
ajuste presas a cada parte, estilos de camada, máscaras e filtros inteligentes,
tudo por comando, sem custo.

O ArtCraft, do mesmo time, não tem MCP; o MCP é do PhotoCraft.

## Instalar (testado com a 0.7.0)

```bash
git clone https://github.com/storytold/photocraft
cd photocraft && cargo build --release -p photocraft-cli    # gera target/release/photocraft-cli
```

Ponha o `photocraft-cli` no PATH ou aponte `PHOTOCRAFT_CLI` para ele. No macOS a
página de versões do GitHub tem o CLI pronto (`photocraft-cli-<versão>-macos-universal.zip`).

## O que tem aqui

| Arquivo | Para quê |
|---|---|
| `sessao.py` | Abre `photocraft-cli serve` e mantém um documento aberto: `abrir`, `executar(id, params)`, `camada(nome)`, `render`, `exportar`, `salvar` |
| `acabar.py` | `medir` (ΔE, perfil e bordas de cada parte contra a referência), `curvas` (o casar_cor e o casar_luz de uma camada) e `aplicar` (roda uma receita, grava PSD/PNG/WebP e prancha, anota no diário) |
| `casar_cor.py` | Curvas por canal (e a curva só de luz) que levam uma parte para a referência, com inclinação limitada |
| `bordas.py` | Réguas de borda: recorte (franja, névoa, ilhas, corte reto), luz de contorno e estouro de nitidez |
| `catalogo.py` | Escreve `.claude/skills/photocraft/referencia/catalogo.md` com os comandos do CLI instalado |
| `receitas/<marca>/` | Receitas de acabamento; só viram padrão depois que o dono aprova |
| `conferir_psd.py` | Confere que o PhotoCraft lê o nosso PSD com as camadas e o render certos |

```bash
python integracoes/photocraft/acabar.py medir saida/arara/tentativas/promo-deposito-001/peca.psd
python integracoes/photocraft/acabar.py aplicar saida/arara/tentativas/promo-deposito-001/peca.psd \
    --receita integracoes/photocraft/receitas/arara/<receita>.json --mudanca "o que mudou"
python integracoes/photocraft/catalogo.py          # depois de atualizar o PhotoCraft
```

`aplicar` grava em `saida/<marca>/acabamentos/<id>/` e acrescenta uma linha em
`fluxos/<marca>/acabamentos.jsonl` com a receita guardada pelo sha256 e `"decisao": null`.
Recusa receita que mexa no texto ou no logo (que saem de código), que ponha camada acima deles,
que esconda uma parte, que use camada que a peça não tem ou comando que não volta do PSD (o
`doc.save` avisa). O formato da receita (campos `alvo`, `props`, `prender`, `nome` e os passos
medidos `casar_cor`, `casar_luz`, `selecao_do_grafo`, `mascara_do_grafo`) está no começo do
`acabar.py` e na skill `photocraft`.

## Três réguas

- **ΔE** (fidelidade): diferença de cor contra a referência, parte por parte. O acabamento não
  deve piorá-lo mais que uns 0,5.
- **Perfil** (acabamento): luz, contraste, saturação e nitidez de cada parte, comparados com a
  mesma parte na referência. Serve até para parte nova, em outra posição. A meta é ficar a uns
  10% da referência.
- **Bordas**: em volta do contorno de cada parte recortada, a franja e a névoa do recorte, a luz
  de contorno e o brilho em volta (contra a referência) e o contorno claro de nitidez demais.
  ΔE e perfil quase não mexem quando se limpa uma franja ou se acende o contorno.

Nitidez a mais sobe um pouco o ΔE (o detalhe novo não cai no mesmo pixel do detalhe da
referência); por isso as duas réguas andam juntas.

## Os agentes

A equipe de acabamento está em `.claude/agents/` (recortista, colorista, retocador, iluminador,
nessa ordem) e o protocolo do diretor em `.claude/skills/acabamento/`. O que se sabe da ferramenta fica em
`.claude/skills/photocraft/` (comandos testados, armadilhas, catálogo) e a experiência de cada
especialista em `.claude/agent-memory/<nome>/MEMORY.md`.

## MCP

Sem janela (o agente edita sozinho):

```bash
photocraft-cli mcp --automation-read-root . --automation-write-root saida
```

Com o app aberto (o dono vê cada passo na tela): abra o app com o canal de controle e ligue o
MCP nele.

```bash
photocraft --control 7878 --control-token-file /caminho/privado/photocraft-control.token \
    --automation-read-root <repo> --automation-write-root <repo>/saida
photocraft-cli mcp --bridge 127.0.0.1:7878 --control-token-file /caminho/privado/photocraft-control.token
```

Ferramentas: `doc_open`, `doc_inspect`, `command_list`, `command_run`, `command_batch`,
`render_preview`, `doc_save`, e no modo com app `ui_screenshot`, `ui_set`, `ui_pointer`. O exemplo
de configuração está em `.mcp.json.exemplo`. Teste rápido:

```bash
python integracoes/testar_mcp.py -- photocraft-cli mcp --automation-read-root .
```

## Conferir um PSD nosso

```bash
python integracoes/photocraft/conferir_psd.py saida/arara/promo-telegram-comfyui.psd \
    --ficha fichas/arara/ficha-v1.2.yaml --cli photocraft-cli
```

Confere que as camadas lidas pelo PhotoCraft têm os nomes e a ordem da ficha e
que o render dele bate com o nosso PNG (diferença média de 2 a 5 em 255 nos testes).
