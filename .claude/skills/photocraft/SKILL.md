---
name: photocraft
description: Como operar o PhotoCraft 0.7.0 (editor tipo Photoshop, sem IA) por receita, sessão ou MCP, medir o resultado contra a referência e não cair nas armadilhas conhecidas. Base de todo agente de acabamento (colorista, recortista, retocador, iluminador) e do diretor.
---

# PhotoCraft: a ferramenta

PhotoCraft 0.7.0 (`photocraft-cli`, 858 comandos) é um editor tipo Photoshop, livre e
local: camadas, camadas de ajuste, máscaras, estilos, objetos e filtros inteligentes,
seleções, canais, retoque. Não tem IA: não redesenha nada. Aqui ele faz o **acabamento** do
PSD que o pipeline ou o loop montaram, para a peça chegar mais perto da referência.

Esta skill é a base. O que cada especialista sabe a mais está na skill dele
(`photocraft-cor`, `-recorte`, `-retoque`, `-luz`) e na memória dele
(`.claude/agent-memory/<nome>/MEMORY.md`).

| Arquivo | O que tem |
|---|---|
| `referencia/comandos-testados.md` | comandos rodados aqui, com os parâmetros exatos e o que fizeram |
| `referencia/armadilhas.md` | o que dá errado sem aviso, a mensagem de erro e a saída |
| `referencia/catalogo.md` | os 858 comandos com parâmetros (gerado por `integracoes/photocraft/catalogo.py`). Procure com `grep`, não leia inteiro |
| `integracoes/photocraft/receitas/<marca>/` | receitas da casa (estado `proposta` até o dono aprovar) |

## As regras que nunca mudam

1. **Texto e logo saem de código.** Nenhum passo mexe neles nem põe camada acima deles. O
   `acabar.py` recusa a receita e confere pixel a pixel no fim.
2. **Não destrutivo sempre que der**: camada de ajuste presa à parte, estilo de camada,
   máscara feita pela seleção, objeto inteligente com filtro inteligente, remendo em camada
   nova. Mexer nos pixels da parte só quando não há outro jeito (retoque em camada de pixels,
   descontaminar a franja do recorte).
3. **Só vale o que volta do PSD.** Filtro inteligente sem par no PSD (`smartSharpen`,
   `reduceNoise`, `lensBlur`, `blurGallery.*`, `relight`, `lightingEffects`...) parece certo e
   some na próxima edição. O `acabar.py` para quando o `doc.save` avisa.
4. **Medir antes e depois, sempre**, com as réguas abaixo. Número sem olhar a imagem também
   engana: olhe a prancha.
5. **Tudo por receita.** O que vai ao dono sai de `acabar.py aplicar` (reproduzível). Edição
   feita à mão no app vira receita antes de valer.
6. **Grátis e local.** Nada de serviço pago, nada de modelo novo baixado.
7. A receita só vira padrão depois que o dono aprova (`decisao` no diário).

## Como dirigir a ferramenta

### 1. Receita + `acabar.py` (o jeito oficial)

```bash
python integracoes/photocraft/acabar.py medir <psd> [--grafo fichas/<marca>/grafos/<peca>.json]
python integracoes/photocraft/acabar.py curvas <psd> --camada mascote [--grafo G]     # o que casar_cor/casar_luz fariam
python integracoes/photocraft/acabar.py aplicar <psd> --receita <r.json> [--grafo G] --mudanca "..." \
    [--saida <pasta>/saida --fluxos <pasta>/fluxos]
```

- Peça do loop acha o grafo pelo diário; peça do pipeline precisa de `--grafo` (o da
  referência mais parecida: mesmo formato e tema).
- **Para testar, use sempre `--saida` e `--fluxos` numa pasta sua** (o scratchpad). Sem isso
  o teste entra no diário do projeto.
- `medir` leva ~20 s; `aplicar` 45 a 60 s (quase tudo é medida antes e depois).
- `aplicar` grava `acabado.psd`, `acabado.png`, `acabado.webp` e `prancha.jpg` (antes x depois)
  e uma linha no diário com `passos`, `notas`, `perfis`, `bordas`, `diagnostico` (antes e depois).

Formato da receita:

```json
{"nome": "...", "descricao": "...", "estado": "proposta", "serve_para": "...",
 "passos": [
  {"camada": "mascote", "casar_luz": {"forca": 1.0}},
  {"camada": "mascote", "comando": "layer.newAdjustmentLayer.vibrance", "params": {"vibrance": 15},
   "prender": true, "nome": "acabamento mascote vibração", "props": {"opacity": 0.6}},
  {"camada": "cena", "comando": "layer.duplicate", "nome": "raios de luz", "props": {"blend": "Screen"}},
  {"camada": "cena", "alvo": "raios de luz", "comando": "image.adjustments.levels", "params": {"inBlack": 170}},
  {"camada": "frente", "mascara_do_grafo": {}}]}
```

| campo | o que faz |
|---|---|
| `camada` | camada da ficha a que o passo pertence; é selecionada antes do comando |
| `alvo` | outra camada (pelo nome) para selecionar no lugar dela: uma criada num passo anterior, um remendo |
| `comando`, `params` | id do catálogo e parâmetros. `"layer": "<nome>"` vira o id da camada visível de cima com esse nome |
| `prender` | a camada nova fica presa (máscara de corte) à camada de baixo |
| `nome` | nome da camada nova (padrão "acabamento <camada> <n>") |
| `props` | `blend`, `opacity` (0 a 1), `visible`... da camada nova. O comando que cria ignora modo e opacidade |
| `casar_cor` `{forca, inclinacao}` | Curvas por canal calculadas contra a mesma parte na referência, presa |
| `casar_luz` `{forca, inclinacao}` | Curvas só de luz em modo Luminosidade, presa: contraste e brilho sem mexer na cor |
| `selecao_do_grafo` `{}` | seleção = contorno da parte no grafo (só parte no lugar da referência) |
| `mascara_do_grafo` `{}` | o mesmo, gravado como máscara da camada (troca a que houver) |

O `acabar.py` já resolve sozinho: comando que troca o id (converter em objeto inteligente)
mantém o nome da parte; `select.deselect` sem seleção é pulado; `casar_*` olha a parte já com
o que os passos anteriores fizeram. E recusa: passo em texto ou logo, máscara vetorial,
difusão/densidade ao vivo na máscara, `refineEdge` com `decontaminate`, comando que age na
camada ativa (`image.adjustments.*`, `edit.fill`, `paint.gradient`) com `layer` diferente do
selecionado (use `alvo`), camada que a peça não tem, parte escondida ou sumida no fim, camada
acima do texto, e aviso no `doc.save`.

### 2. Sessão em Python (para experimentar rápido, sem diário)

```python
import sys; sys.path.insert(0, ".")
from integracoes.photocraft.sessao import Sessao
from integracoes.photocraft import acabar as A
with Sessao(leitura=psd.parent, escrita=Path(pasta)) as pc:     # raízes: o que pode ler e gravar
    pc.abrir(psd)
    A.aplicar_passos(pc, {"passos": passos}, grafo, A.camadas_de_pixels(psd))
    img = pc.render(lado_max=0)          # peça achatada, tamanho cheio (PIL)
    pc.salvar(Path(pasta) / "teste.psd")  # devolve {"warnings": [...]}: lista vazia é o certo
```

`pc.camadas()` lista as camadas (de cima para baixo) com `kind`, `blend`, `opacity`,
`clipped`, `hasMask`, `visible`, `effects`, `smartFilters`. `pc.executar(id, params)` roda um
comando; `pc.inspecionar()` traz `hasSelection`, `channels`, `activeLayer`.

### 3. MCP (com o app aberto, o dono vê cada passo)

`photocraft-cli mcp --bridge 127.0.0.1:7878 --control-token-file <arquivo privado>` com o app
aberto em `photocraft --control 7878 ...` (ver `integracoes/photocraft/LEIA-ME.md`). Ferramentas
`command_run`, `command_batch`, `render_preview`, `doc_save`, `ui_screenshot`. Serve para
mostrar ao dono; o que valer vira receita.

## A pilha (onde a camada nova nasce)

- A camada nova nasce **logo acima da camada selecionada**. Cada passo seleciona a parte, então
  o passo de depois fica mais perto da parte e age antes dos anteriores.
- Ajuste preso vale para tudo o que está abaixo dele no mesmo grupo de corte (a parte e o que
  estiver preso abaixo dele).
- Para uma camada nova valer **também sobre um remendo** já preso à parte, use `alvo` com o
  remendo: ela nasce acima dele, presa à mesma parte.
- Ajuste geral da peça: `camada` = a camada logo abaixo do texto (`brilho`), sem prender. Prefira
  ajuste preso a cada parte.
- Converter em objeto inteligente leva a máscara da camada para dentro dele e mantém o que está
  preso em cima.

Ordem da equipe: **recortista → colorista → retocador → iluminador**. Borda limpa antes de tudo
(sujeira de recorte vira "cor errada" na medida); cor antes da nitidez (contraste sobe a régua
de nitidez); retoque e nitidez antes da luz (o brilho não é afiado nem remendado por cima).

## As réguas

| régua | o que mede | meta |
|---|---|---|
| ΔE (`notas`) | diferença de cor contra a referência, parte por parte | não piorar mais que ~0,5 (peça do loop); cair (peça nova) |
| perfil (`perfis`) | luz, contraste, saturação, nitidez de cada parte contra a mesma parte na referência | ~10% da referência |
| recorte (`bordas.<parte>.recorte`) | `franja` (±3), `semi_%` (≤3), `ilhas` (≤5), `borda_opaca` (~0), `quadro_%` (<90 fora a cena), `dE_borda` (não subir) | — |
| contorno (`bordas.<parte>.contorno`) | `brilho_fora`, `luz_borda`, `lados` na peça e na referência | ~3 de luz da referência |
| estouro (`bordas.<parte>.estouro`) | contorno claro da nitidez nos pixels da camada | borda ≤1%, miolo ≤3% |

O `diagnostico` traduz tudo em frases, da maior diferença para a menor, com a área entre
parênteses: `(recorte)`, `(cor)`, `(retoque)`, `(luz)`.

Leitura por tipo de peça:
- **Peça do loop** (img2img da referência, partes no lugar): a cor já vem certa; o ΔE é de
  detalhe e quase não cai. Falta nitidez (~40%) e um pouco de contraste.
- **Peça nova** (gerada do zero, recortada por rembg): tudo lavado (saturação -20%, nitidez
  -50%), franja do recorte, objetos fora do lugar da referência. Aqui o ΔE cai com acabamento
  bom, mas não chega perto: desenho diferente não se corrige no PhotoCraft.

## O que outros editores veem

- A prévia achatada que o PhotoCraft grava no PSD é igual ao render: quem lê a prévia vê tudo.
- Quem recompõe o PSD camada a camada (psd-tools `composite(force=True)`, GIMP) **não desenha**:
  estilos de camada (brilho, sombra, cetim, chanfro), Blend If, e no psd-tools também Curvas,
  Vibração, Equilíbrio de Cor, Cor Seletiva, Filtro de Fotos e Mapa de Gradiente. Desenha:
  Níveis, Matiz/Saturação, Brilho/Contraste, Exposição, preenchimentos, modos de mesclagem,
  máscaras, objetos inteligentes (pixels já filtrados).
- O `acabar.py` mede pelo render do PhotoCraft, então mede o que o dono vê no PhotoCraft.

## Como aprender (memória)

- Antes de começar: leia a sua `MEMORY.md` e a memória do diretor
  (`.claude/skills/acabamento/memoria.md`).
- Ao terminar: uma linha por aprendizado novo, com data, peça e números (o que funcionou e o
  que não). Erro novo do PhotoCraft vai também para `referencia/armadilhas.md`; comando novo
  testado, para `referencia/comandos-testados.md`. Nunca grave texto de oferta nem token.
- Ao atualizar o PhotoCraft: `python integracoes/photocraft/catalogo.py` e rode de novo as
  receitas da casa num teste (`--saida`/`--fluxos` numa pasta sua) antes de confiar nelas.
