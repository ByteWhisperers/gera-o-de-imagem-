# Produção de imagem

Copia o padrão visual de uma mídia de referência e gera peças novas no mesmo padrão, em camadas.

**Primeira vez aqui? Leia o [INSTALAR.md](INSTALAR.md):** ele leva do download até o fluxo funcionando, em quatro níveis (rascunho, geração no ComfyUI, loop de medição, acabamento no PhotoCraft). Tudo é grátis e local.

```
referências ──► ficha de estilo ──► partes geradas ──► composição em camadas ──► PSD + PNG/WebP
 (exemplos)     (desconstrução)     (portão de geração)  (pela ficha)              + relatório de QA
```

A **ficha de estilo** (`fichas/<marca>/ficha-vX.Y.yaml`) é o contrato entre as etapas. A desconstrução escreve nela; criação e composição só leem.

## Rodar

Depois de instalar (nível 1 do INSTALAR.md, com o ambiente virtual ativo):

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# custo zero: partes de rascunho, testa layout, texto e camadas
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram

# partes geradas no ComfyUI local (grátis) e registradas em partes/arara/registro.yaml
python pipeline.py fichas/arara/ficha-v1.2.yaml --provedor comfyui --tema telegram --formato promo

# partes geradas pelo gateway de imagem (pago, Z-Image Turbo, US$ 0,005 por parte nova), com teto de gasto
GATEWAY_CHAVE=... python pipeline.py fichas/arara/ficha-v1.2.yaml --provedor gateway --teto 0.05 --tema telegram --formato promo

# partes já registradas (por exemplo as do fal no teste 1, ficha v1.0)
python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --tema turista
```

A pasta `partes/<marca>/` é a **biblioteca de partes**: cada fundo, mascote e entorno fica guardado uma vez, com a receita, no `registro.yaml`. Com `--provedor comfyui` o portão reaproveita a parte que já existe com a mesma receita e só gera o que falta. Para pedir uma variação, use `--novo mascote` (ou `cena`, `entorno`, `frente`). Texto e logo não ficam guardados como imagem: saem do código toda vez.

O **tema** liga a mensagem ao mascote: escolhe o figurino, o que ele segura, os objetos em volta (camada `entorno`), o que fica na frente dele (camada `frente`, desde a ficha v1.2) e as linhas de texto de exemplo. Os temas ficam na ficha.

Saída em `saida/<marca>/`: um `.psd` com uma camada por item da ficha, `.png`, `.webp` e `relatorio-<provedor>-<tema>.json` com a origem de cada parte, o custo e o resultado do QA.

## Reproduzir uma referência e medir (o loop)

```
referência ──► grafo da peça ──► workflow do ComfyUI ──► PSD ──► notas por parte ──► diário
 (inteira)    (partes isoladas    (montado pelo           (texto e     (contra a mesma     (tentativas.jsonl)
               + relações)          compilador)             logo de      parte isolada
                                                            código)      na referência)
```

```bash
pip install -r requirements-desconstrucao.txt
# 1. desconstruir: o agente marca contornos aproximados, a ferramenta encaixa na borda e mede o resto
python ferramentas/desconstruir.py fichas/arara/grafos/promo-telegram.marcacao.yaml --placas
# 2. uma volta do loop: monta o workflow a partir do grafo, roda no ComfyUI, monta o PSD e compara
python tentativa.py fichas/arara/grafos/promo-telegram.json
# 3. a próxima volta muda uma coisa só e diz de onde partiu
python tentativa.py fichas/arara/grafos/promo-telegram.json --denoise personagem=0.4 --pai promo-telegram-001 --mudanca "mascote mais fiel"
```

O **grafo** (`fichas/<marca>/grafos/<peca>.json`) guarda a peça inteira, cada parte isolada (máscara e recorte em `fichas/<marca>/grafos/<peca>/`), as placas sem texto e de fundo limpo, e as relações entre as partes (quem segura o quê, o que o tema liga, contraste do texto). Não substitui a ficha: descreve uma peça.

O **compilador** (`motor/compilador.py`) transforma o grafo em workflow do ComfyUI: um ramo por camada gerada, cada um trabalhando na região da sua parte na referência. Texto e logo nunca viram ramo. O mesmo grafo sempre dá o mesmo workflow, guardado em `fluxos/<marca>/workflows/<sha256>.json`.

O **comparador** (`motor/comparar.py`) mede cada parte contra a mesma parte isolada na referência: diferença de cor (ΔE CIEDE2000), estrutura (SSIM), paleta, cobertura e corte reto na borda. Cada tentativa vira uma linha em `fluxos/<marca>/tentativas.jsonl`, com o workflow, os parâmetros, o tempo e as notas.

Integrações: `integracoes/comfyui/LEIA-ME.md` (geração e fluxo completo) e `integracoes/photocraft/LEIA-ME.md` (editor do PSD). Os dois têm MCP; veja `.mcp.json.exemplo`.

## Pastas

| Pasta | O que tem |
|---|---|
| `referencias/` | As mídias que queremos copiar |
| `fichas/` | Fichas de estilo, medidas, evidência e o grafo de cada peça de referência |
| `partes/` | Partes geradas por IA e o registro com a receita de cada uma |
| `fluxos/` | Workflows montados pelo compilador e o diário das tentativas do loop |
| `motor/` | Código: ficha, grafo, compilador, portão de geração, recorte, texto, compositor, QA, comparador |
| `ferramentas/` | Medição e desconstrução das referências |
| `integracoes/` | ComfyUI (nós, grafos, fluxo) e PhotoCraft (conferência do PSD) |
| `.claude/skills/` | Protocolo e memória de cada agente especialista |
| `testes/` | Testes automáticos |

## Estado

- Teste 1 (09/10/2026): ficha ARARA v1.0, partes geradas com `fal-ai/flux/schnell` (cerca de US$0,018 no total), composição em PSD funcionando.
- Fluxo ComfyUI (09/10/2026): ficha v1.1 aprovada com temas; ComfyUI local com SD-Turbo (grátis, CPU, licença não comercial) gera as 3 partes e monta o PSD num só fluxo; o PhotoCraft abre o PSD com as mesmas camadas.
- Loop e desconstrução (10/10/2026): as 11 referências viraram grafos de partes isoladas; o compilador monta o workflow do ComfyUI a partir do grafo e cada tentativa é medida contra a referência e anotada em `fluxos/arara/tentativas.jsonl`. Ficha v1.2 aprovada.
- Acabamento no PhotoCraft (11/10/2026): quatro agentes especialistas (recortista, colorista, retocador, iluminador) com memória, skills e réguas de medida. A receita do depósito é padrão aprovado; a do Telegram é proposta.

Fontes: Montserrat (SIL Open Font License 1.1, `fontes/OFL.txt`).
