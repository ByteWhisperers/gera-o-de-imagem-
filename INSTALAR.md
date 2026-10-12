# Instalar e rodar o projeto

Este guia leva uma pessoa que acabou de baixar o projeto até o fluxo funcionando. Tudo é **grátis e
local**: nada aqui chama serviço pago nem pede chave de API.

O projeto tem quatro níveis. Cada um funciona sozinho e o seguinte só acrescenta coisas ao anterior.
**Comece pelo Nível 1** e só avance se precisar.

| Nível | Para que serve | O que acrescenta | Instalação | Espaço |
|---|---|---|---|---|
| 1. Rascunho | Montar a peça em camadas (PSD + PNG + WebP) com partes de rascunho, rodar os testes | Python e 5 pacotes | 5 min | pouco |
| 2. Geração | Gerar fundo, mascote e objetos com IA no ComfyUI, no seu computador | ComfyUI, PyTorch, modelo de imagem (5,2 GB), modelo de recorte | 30 a 60 min | cerca de 8 GB |
| 3. Loop | Reproduzir uma referência, medir contra ela e anotar cada tentativa | Mais 1 pacote (e o ComfyUI do Nível 2 ligado) | 2 min | pouco |
| 4. Acabamento | Corrigir recorte, cor, nitidez e luz do PSD no PhotoCraft | PhotoCraft (compilado do código-fonte) | cerca de 10 min | cerca de 1,5 GB |

Os agentes especialistas (`.claude/`) são opcionais: veja "Agentes" no fim.

## O que foi testado

Linux x86_64, Python 3.13, sem placa de vídeo (CPU), 4 núcleos e 16 GB de memória. **macOS e Windows não
foram testados.** No Windows, use o WSL2 com Ubuntu. Os comandos abaixo são de Linux e macOS (no Windows
sem WSL, o ambiente virtual ativa com `.venv\Scripts\activate` e o link do Nível 2 vira `mklink /D`).

Versões que funcionaram juntas: ComfyUI 0.39.0, PyTorch 2.14 (CPU), numpy 2.5, Pillow 12.3, psd-tools 1.24,
scipy 1.18, rembg 2.0.85, scikit-image 0.26, PhotoCraft 0.7.0. Os pacotes do projeto não têm limite
superior de versão; se uma versão nova quebrar algo, use as de cima.

## Passo 0: baixar o projeto

```bash
git clone --branch claude/project-thread-uhy15s https://github.com/ByteWhisperers/gera-o-de-imagem-.git
cd gera-o-de-imagem-
```

O repositório só tem esse ramo (não existe `main`). Se for privado, o `git clone` pede o login da conta
com acesso. Precisa de Python 3.10 ou mais novo (testado com o 3.13) e de `git`.

Crie **um ambiente Python só** para tudo (projeto, ComfyUI e recorte). É o que o projeto espera, porque os
nós do ComfyUI importam o código do projeto:

```bash
python3 -m venv .venv
. .venv/bin/activate          # sempre que abrir um terminal novo, rode esta linha na pasta do projeto
```

## Nível 1: rascunho (sem IA)

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram
```

**Deu certo se:** os testes terminam em `passed` (os que dependem do PhotoCraft ou do scikit-image aparecem
como `skipped` enquanto você não instalar os Níveis 3 e 4) e existe `saida/arara/home-telegram-rascunho.psd`
com o `.png` e o `.webp` ao lado. Abra o PNG: é a peça com texto, logo e partes de rascunho.

Os temas ficam na ficha: `instagram`, `telegram`, `envelopes`, `vip`, `reembolso`, `deposito`, `convite`.
`--formato home` ou `--formato promo` escolhe o tamanho. O texto e o logo sempre saem de código
(`motor/texto.py`), nunca da IA.

Também funciona sem instalar mais nada: `--provedor registro`, que usa as partes que já estão guardadas em
`partes/arara/` (as do teste 1, feitas com o `fal-ai/flux/schnell`), só com a ficha antiga:

```bash
python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --tema turista
```

## Nível 2: gerar as partes com IA (ComfyUI local)

O ComfyUI fica **fora** da pasta do projeto, ao lado dela. Estes comandos partem de dentro da pasta do
projeto, com o `.venv` ativo:

```bash
# 1. PyTorch na versão de CPU (para placa de vídeo NVIDIA, use a linha que pytorch.org/get-started mostra)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. ComfyUI, na versão testada
git clone https://github.com/comfyanonymous/ComfyUI ../ComfyUI
git -C ../ComfyUI checkout 08ff3c11
pip install -r ../ComfyUI/requirements.txt

# 3. o que o projeto usa dentro do ComfyUI e para o recorte do mascote
pip install -r requirements-comfyui.txt

# 4. os nós do projeto no ComfyUI (um link, não uma cópia)
ln -s "$PWD/integracoes/comfyui/nos_gera_imagem" ../ComfyUI/custom_nodes/nos_gera_imagem

# 5. o modelo de imagem: SD-Turbo, 5,2 GB, grátis
curl -L -o ../ComfyUI/models/checkpoints/sd_turbo.safetensors \
  https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors
```

**A licença do SD-Turbo é de pesquisa, não comercial** (confira em stability.ai/license). Ele serve para
validar o fluxo. Para produzir de verdade, troque o `checkpoint` em `integracoes/comfyui/config.yaml`: a ficha
não muda, só esse arquivo.

Ligue o ComfyUI e **deixe esse terminal aberto** (use outro para os comandos do projeto):

```bash
python ../ComfyUI/main.py --cpu --listen 127.0.0.1 --port 8188
```

**Deu certo se**, em outro terminal:

```bash
curl -s http://127.0.0.1:8188/system_stats | head -c 120                     # responde com um JSON
curl -s http://127.0.0.1:8188/object_info/GeraComporPeca | head -c 120      # responde: os nós do projeto carregaram
```

Agora gere uma peça inteira (cerca de 2,5 minutos em CPU):

```bash
python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo --saida peca.png
# ou parte por parte pelo portão, que guarda cada parte em partes/arara/ com a receita:
python pipeline.py fichas/arara/ficha-v1.2.yaml --provedor comfyui --tema telegram --formato promo
```

Na **primeira vez** o recorte do mascote baixa o modelo `isnet-general-use` (cerca de 180 MB, para
`~/.rembg/models/`). Isso precisa de internet uma única vez. Sem ele o recorte cai para um método pior e o
QA reclama.

O fluxo completo grava em `ComfyUI/output/gera/arara/` (PSD, PNG, WebP e o relatório do QA). O comando
pelo portão grava em `saida/arara/`.

A configuração do modelo, dos tamanhos e do recorte está em `integracoes/comfyui/config.yaml`. Para o
ComfyUI em outro endereço, mude a chave `url` nesse arquivo.

## Nível 3: o loop (reproduzir uma referência e medir)

Precisa do ComfyUI ligado (Nível 2) e de mais um pacote:

```bash
pip install -r requirements-desconstrucao.txt
```

```bash
# monta o workflow a partir do grafo e confere nós e modelos, sem gerar nada
python tentativa.py fichas/arara/grafos/promo-telegram.json --so-compilar
# uma volta completa: gera, monta o PSD, compara cada parte com a referência e anota o diário
python tentativa.py fichas/arara/grafos/promo-telegram.json
```

**Deu certo se** aparece uma pasta nova em `saida/arara/tentativas/promo-telegram-NNN/` com `peca.psd`, a
prancha de comparação, e uma linha nova em `fluxos/arara/tentativas.jsonl`. A volta leva cerca de 2 minutos
(40 a 55 segundos quando o ComfyUI reaproveita partes iguais).

As referências, os grafos das 11 peças, as máscaras e as placas já estão no repositório. Para
desconstruir uma imagem **nova** (marcar contornos e gerar o grafo):
`python ferramentas/desconstruir.py fichas/arara/grafos/<peca>.marcacao.yaml --placas`.

## Nível 4: acabamento no PhotoCraft

O PhotoCraft é um editor de imagem tipo Photoshop, livre, que o projeto dirige por comando. Não existe
pacote pronto para instalar: compile do código-fonte (precisa do Rust 1.95 ou mais novo, de
https://rustup.rs). O binário não pede nenhuma biblioteca extra além das do sistema.

```bash
git clone https://github.com/storytold/photocraft ../photocraft
git -C ../photocraft checkout 7926161                     # a versão 0.7.0
(cd ../photocraft && cargo build --release -p photocraft-cli)   # cerca de 6 minutos com 4 núcleos
export PHOTOCRAFT_CLI="$PWD/../photocraft/target/release/photocraft-cli"
```

O `export` vale só para este terminal. Para ficar fixo, ponha o `photocraft-cli` no `PATH`
(`ln -s ... /usr/local/bin/photocraft-cli`) ou repita a linha no arquivo de inicialização do seu terminal.
No macOS, a página de versões do PhotoCraft no GitHub pode ter o executável pronto.

**Deu certo se** `"$PHOTOCRAFT_CLI" --version` mostra `photocraft-cli 0.7.0`.

Para usar, você precisa de um PSD de peça (o Nível 1 ou o 2 gera um). O diagnóstico mede cada parte
contra a referência e **não altera nada**:

```bash
python integracoes/photocraft/acabar.py medir saida/arara/promo-telegram-comfyui.psd \
    --grafo fichas/arara/grafos/promo-telegram.json
# aplicar uma receita (grava em saida/arara/acabamentos/ e anota fluxos/arara/acabamentos.jsonl):
python integracoes/photocraft/acabar.py aplicar saida/arara/promo-telegram-comfyui.psd \
    --grafo fichas/arara/grafos/promo-telegram.json \
    --receita integracoes/photocraft/receitas/arara/promo-telegram-comfyui-2.json \
    --mudanca "teste da instalação"
```

Cada medida leva cerca de 20 segundos e cada `aplicar`, cerca de 1 minuto. As receitas ficam em
`integracoes/photocraft/receitas/arara/`: a do depósito (`promo-deposito-1`) é padrão aprovado; a do Telegram
ainda é proposta. Receita só vale para o tipo de peça para o qual foi feita (veja `serve_para` dentro dela).
Mais detalhes em `integracoes/photocraft/LEIA-ME.md`.

## Agentes (opcional)

A pasta `.claude/` tem os agentes especialistas (recortista, colorista, retocador, iluminador), as skills e a
memória de cada um. Para usá-los, abra a pasta do projeto no **Claude Code**; ele lê o `CLAUDE.md` e carrega
sozinho tudo o que está em `.claude/`. Sem o Claude Code, nada muda: os mesmos comandos acima rodam à mão.

Para o Claude Code controlar o ComfyUI e o PhotoCraft por MCP, veja `.mcp.json.exemplo`.

## O que não vem no repositório

| Falta | Por quê | Onde resolver |
|---|---|---|
| `saida/` (PSDs e imagens de cada rodada) | Fica de fora de propósito; é regenerável | Os comandos acima recriam |
| ComfyUI, PyTorch e o modelo SD-Turbo | São de terceiros e pesados | Nível 2 |
| Modelo de recorte (`isnet-general-use`) | Baixa sozinho na primeira vez | Nível 2 |
| PhotoCraft | Compilado do código-fonte | Nível 4 |

## Quando algo dá errado

| O que aparece | O que fazer |
|---|---|
| `ModuleNotFoundError` | O `.venv` não está ativo (rode `. .venv/bin/activate`) ou falta um `pip install -r` do nível que você está usando |
| `Connection refused` ou o ComfyUI não responde | O servidor do ComfyUI não está rodando: ligue-o (Nível 2) e deixe o terminal aberto |
| `GeraComporPeca` (ou `GeraFichaPrompt`) desconhecido | O link do passo 4 do Nível 2 não existe ou aponta para o lugar errado: `ls -l ../ComfyUI/custom_nodes/` |
| `sd_turbo.safetensors` não encontrado | O modelo não está em `ComfyUI/models/checkpoints/` (passo 5) ou o nome no `config.yaml` é outro |
| `photocraft-cli não encontrado` | Defina `PHOTOCRAFT_CLI` ou ponha o executável no `PATH` (Nível 4) |
| Memória acabando na geração | O modelo em CPU usa muita memória: feche outros programas; com menos de 12 GB não foi testado |
| `acabar.py` recusa a receita | Leu a mensagem: ela diz qual passo e por quê (por exemplo, camada que a peça não tem) |

Para conferir tudo de uma vez depois de instalar: `python -m pytest -q` (os testes do Nível 3 e 4 só
rodam se o scikit-image e o PhotoCraft estiverem instalados).
