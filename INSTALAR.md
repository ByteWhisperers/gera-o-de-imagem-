# Instalar e rodar o projeto

Este guia leva uma pessoa que acabou de baixar o projeto até o fluxo funcionando. Tudo é **grátis e
local**: nada aqui chama serviço pago nem pede chave de API. Alguns comandos imprimem no fim um "custo das
partes usadas" (por exemplo US$ 0,0032): é o custo **antigo** de partes que já estavam guardadas no
repositório (feitas no teste 1, com um serviço pago), não um gasto novo.

O projeto tem quatro níveis. Cada um funciona sozinho e o seguinte só acrescenta coisas ao anterior.
**Comece pelo Nível 1** e só avance se precisar.

| Nível | Para que serve | O que acrescenta | Instalação | Espaço |
|---|---|---|---|---|
| 1. Rascunho | Montar a peça em camadas (PSD + PNG + WebP) com partes de rascunho, rodar os testes | Python e 5 pacotes | alguns minutos | pouco |
| 2. Geração | Gerar fundo, mascote e objetos com IA no ComfyUI, no seu computador | ComfyUI, PyTorch, modelo de imagem (5,2 GB), modelo de recorte | 30 a 60 min | cerca de 8 GB |
| 3. Loop | Reproduzir uma referência, medir contra ela e anotar cada tentativa | O ComfyUI do Nível 2 ligado (e 1 pacote, só para desconstruir imagem nova) | 2 min | pouco |
| 4. Acabamento | Corrigir recorte, cor, nitidez e luz do PSD no PhotoCraft | PhotoCraft (compilado do código-fonte) | cerca de 10 min a 15 min | cerca de 2,5 GB (com o Rust) |

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
com acesso. Precisa de `git` e de Python 3.11 ou mais novo (**testado só com o 3.13**; confira com `python3 --version`).

Crie **um ambiente Python só** para tudo (projeto, ComfyUI e recorte). É o que o projeto espera, porque os
nós do ComfyUI importam o código do projeto:

```bash
python3 -m venv .venv
. .venv/bin/activate          # sempre que abrir um terminal novo, rode esta linha na pasta do projeto
```

No Ubuntu ou Debian (e no WSL), se o primeiro comando reclamar de `ensurepip` ou `venv`, rode antes
`sudo apt install python3-venv python3-pip`.

## Nível 1: rascunho (sem IA)

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python pipeline.py fichas/arara/ficha-v1.2.yaml --tema telegram
```

**Deu certo se:**
- os testes terminam em `passed`, em menos de 3 minutos. Numa máquina limpa, **5 testes aparecem como
  `skipped`**: 1 do scikit-image e 4 do PhotoCraft, que só rodam depois de você instalar o Nível 4
  (e com o `photocraft-cli` no `PATH`, veja lá);
- existem `saida/arara/home-telegram-rascunho.psd` e `saida/arara/promo-telegram-rascunho.psd`, cada um com o
  `.png` e o `.webp` ao lado, mais `relatorio-rascunho-telegram.json`. Sem `--formato`, saem os dois formatos.
  Abra um PNG: é a peça com texto, logo e partes de rascunho. O comando leva alguns segundos.

Os temas ficam na chave `temas` da ficha, por exemplo `instagram`, `telegram`, `envelopes`, `vip`,
`reembolso`, `deposito`, `convite` (a lista completa está em `fichas/arara/ficha-v1.2.yaml`).
`--formato home` (2048 x 682) ou `--formato promo` (1867 x 842) escolhe só um tamanho. O texto e o logo
sempre saem de código (`motor/texto.py`), nunca da IA.

Também funciona sem instalar mais nada: `--provedor registro`, que usa as partes que já estão guardadas em
`partes/arara/` (as do teste 1, feitas com o `fal-ai/flux/schnell`), só com a ficha antiga:

```bash
python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --tema turista
```

No fim ele mostra um custo (cerca de US$ 0,008). É o custo **antigo** dessas partes, que já estavam
guardadas: o comando em si não gasta nada.

## Nível 2: gerar as partes com IA (ComfyUI local)

O ComfyUI fica **fora** da pasta do projeto, ao lado dela. Estes comandos partem de dentro da pasta do
projeto, com o `.venv` ativo:

```bash
# 1. PyTorch na versão de CPU (para placa de vídeo NVIDIA, use a linha que pytorch.org/get-started mostra).
#    O torchvision TEM de vir junto e do mesmo lugar: senão o passo 2 traz um que não casa com o torch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. ComfyUI, na versão testada
git clone https://github.com/comfyanonymous/ComfyUI ../ComfyUI
git -C ../ComfyUI checkout 08ff3c11
pip install -r ../ComfyUI/requirements.txt

# 3. o que o projeto usa dentro do ComfyUI e para o recorte do mascote
pip install -r requirements-comfyui.txt

# 4. os nós do projeto no ComfyUI (um link, não uma cópia)
ln -s "$PWD/integracoes/comfyui/nos_gera_imagem" ../ComfyUI/custom_nodes/nos_gera_imagem

# 5. o modelo de imagem: SD-Turbo, 5,2 GB, grátis
curl -fL -o ../ComfyUI/models/checkpoints/sd_turbo.safetensors \
  https://huggingface.co/stabilityai/sd-turbo/resolve/main/sd_turbo.safetensors

# 6. o modelo de recorte do mascote (cerca de 180 MB, de github.com): baixe já, com internet
python -c "from rembg import new_session; new_session('isnet-general-use')"
```

**A licença do SD-Turbo é de pesquisa, não comercial** (confira em stability.ai/license). Ele serve para
validar o fluxo. Para produzir de verdade, troque o `checkpoint` em `integracoes/comfyui/config.yaml`: a ficha
não muda, só esse arquivo.

Ligue o ComfyUI e **deixe esse terminal aberto** (use outro para os comandos do projeto):

```bash
python ../ComfyUI/main.py --cpu --listen 127.0.0.1 --port 8188
```

Espere cerca de 20 segundos, até aparecer `To see the GUI go to: http://127.0.0.1:8188` nesse terminal.
Se aparecer um `Traceback`, o servidor não subiu: veja "Quando algo dá errado".

**Deu certo se**, em outro terminal (se você mudou a porta, mude também nestes comandos):

```bash
curl -s http://127.0.0.1:8188/system_stats | head -c 120                     # responde com um JSON
curl -s http://127.0.0.1:8188/object_info/GeraComporPeca | head -c 120      # começa com {"GeraComporPeca": ...
```

Se o segundo comando responder só `{}`, o link do passo 4 está errado.

Agora gere uma peça inteira. Em CPU de 4 núcleos a conta é de **3 a 12 minutos**: a primeira geração depois
de ligar o servidor é a mais lenta, porque carrega o modelo de 5,2 GB para a memória.

```bash
python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo --saida peca.png
# ou parte por parte pelo portão, que guarda cada parte em partes/arara/ com a receita:
python pipeline.py fichas/arara/ficha-v1.2.yaml --provedor comfyui --tema telegram --formato promo
```

**Deu certo se** o `rodar_fluxo.py` termina com `ok: 1867x842 -> peca.png` e o `peca.png` é uma peça com
selva, mascote, moedas, texto e logo (é rascunho de modelo de teste: tem recortes retos e rosto estranho).

O fluxo completo grava em `ComfyUI/output/gera/arara/` (PSD, PNG, WebP e o relatório do QA). O comando
pelo portão grava em `saida/arara/`. **O portão reaproveita** as partes que já estão em `partes/arara/` e só
gera o que falta (por isso é mais rápido e a cena pode ser a do repositório, não a do modelo local). O que ele
gera entra em `partes/arara/` e em `partes/arara/registro.yaml`, que são arquivos versionados: o
`git status` mostra a diferença. Para pedir uma versão nova de uma parte, use `--novo mascote` (ou `cena`,
`entorno`, `frente`).

Sobre o recorte do mascote: se o passo 6 não foi feito, o modelo baixa na primeira geração e **precisa de
internet nessa hora**: sem ela o comando termina com erro de conexão com `github.com`. O recorte só cai
para um método mais simples (pela cor da borda) se o pacote `rembg` nem estiver instalado, e então o QA
reclama: rode de novo o `pip install -r requirements-comfyui.txt`.

A configuração do modelo, dos tamanhos e do recorte está em `integracoes/comfyui/config.yaml`. Para o
ComfyUI em outro endereço, mude a chave `url` nesse arquivo.

## Nível 3: o loop (reproduzir uma referência e medir)

Precisa do ComfyUI **ligado** (Nível 2), até para o `--so-compilar`, que lê do servidor a lista de nós e
modelos para conferir o workflow:

```bash
# monta o workflow a partir do grafo e confere nós e modelos, sem gerar nada
python tentativa.py fichas/arara/grafos/promo-telegram.json --so-compilar
# uma volta completa: gera, monta o PSD, compara cada parte com a referência e anota o diário
python tentativa.py fichas/arara/grafos/promo-telegram.json
```

**Deu certo se** o `--so-compilar` imprime `"conferencia": "ok"` em cerca de 1 segundo, e a volta completa cria
uma pasta nova em `saida/arara/tentativas/promo-telegram-NNN/` (o número continua o do diário) com `peca.psd`,
a prancha de comparação, e acrescenta uma linha em `fluxos/arara/tentativas.jsonl`. A volta leva de 3 a 12
minutos em CPU de 4 núcleos (menos quando o servidor já está com o modelo carregado). Os dois comandos mexem em
arquivos versionados de `fluxos/arara/` (o workflow montado e o diário): o `git status` mostra o que mudou.

As referências, os grafos das 11 peças, as máscaras e as placas já estão no repositório. Para
desconstruir uma imagem **nova** (marcar contornos e gerar o grafo):
`python ferramentas/desconstruir.py fichas/arara/grafos/<peca>.marcacao.yaml --placas`. Isso usa o
scikit-image, que o Nível 2 já instalou (junto com o `rembg`). Sem o Nível 2:
`pip install -r requirements-desconstrucao.txt`.

## Nível 4: acabamento no PhotoCraft

O PhotoCraft é um editor de imagem tipo Photoshop, livre, que o projeto dirige por comando. No Linux
e no Windows (WSL), compile do código-fonte. Precisa do **Rust 1.95 ou mais novo** (https://rustup.rs) e de um
compilador C: no Ubuntu ou Debian (inclusive WSL), `sudo apt install build-essential`; no macOS,
`xcode-select --install`. O binário pronto não pede nenhuma biblioteca além das do sistema. No macOS, a
página de versões do PhotoCraft no GitHub pode ter o `photocraft-cli` já compilado.

```bash
git clone https://github.com/storytold/photocraft ../photocraft
git -C ../photocraft checkout 7926161                     # a versão 0.7.0
(cd ../photocraft && cargo build --release -p photocraft-cli)   # cerca de 6 minutos com 4 núcleos, mais o download das dependências
export PHOTOCRAFT_CLI="$PWD/../photocraft/target/release/photocraft-cli"
```

O `export` vale só para este terminal. Para ficar fixo, ponha o `photocraft-cli` no `PATH`
(`ln -s ... /usr/local/bin/photocraft-cli`) ou repita a linha no arquivo de inicialização do seu terminal.
No macOS, a página de versões do PhotoCraft no GitHub pode ter o executável pronto.

**Deu certo se** `"$PHOTOCRAFT_CLI" --version` mostra uma linha que começa com `photocraft-cli 0.7.0`
(o `(dev build)` no fim é normal). Com o `PHOTOCRAFT_CLI` definido, os 4 testes do PhotoCraft deixam de
aparecer como `skipped` no `python -m pytest -q`.

Para testar, você precisa de um PSD de peça. O do Nível 1 serve:
`saida/arara/promo-telegram-rascunho.psd`. O diagnóstico mede cada parte contra a referência e **não
altera nada** (cerca de 20 segundos):

```bash
python integracoes/photocraft/acabar.py medir saida/arara/promo-telegram-rascunho.psd \
    --grafo fichas/arara/grafos/promo-telegram.json
```

Aplicar uma receita (cerca de 1 minuto). Este é só um **teste da instalação**: o rascunho tem partes de mentira
e a receita `nova-nitidez` está aqui só para exercitar o caminho todo. Os dois destinos abaixo deixam o teste
fora de `saida/` e do diário do projeto:

```bash
python integracoes/photocraft/acabar.py aplicar saida/arara/promo-telegram-rascunho.psd \
    --grafo fichas/arara/grafos/promo-telegram.json \
    --receita integracoes/photocraft/receitas/arara/nova-nitidez.json \
    --mudanca "teste da instalação" \
    --saida ../teste-acabamento/saida --fluxos ../teste-acabamento/fluxos
```

**Deu certo se** existe `../teste-acabamento/saida/arara/acabamentos/promo-telegram-ac001/` com `acabado.psd`,
`acabado.png`, `acabado.webp` e a `prancha.jpg` (antes x depois). Sem os dois destinos, o `aplicar` grava em
`saida/` e **acrescenta uma linha em `fluxos/arara/acabamentos.jsonl`**, que é versionado.

As receitas ficam em `integracoes/photocraft/receitas/arara/`. A do depósito (`promo-deposito-1`) é padrão
aprovado; as outras, inclusive a do Telegram, ainda são proposta. **Cada receita serve para um tipo de peça**
(o campo `serve_para`, dentro dela): o `acabar.py` mostra esse aviso, mas não confere. Uma receita feita para
outra peça roda sem erro e dá resultado sem sentido. Por exemplo, `promo-telegram-comfyui-2.json` só faz
sentido na peça gerada pelo Nível 2 (`saida/arara/promo-telegram-comfyui.psd`).
Mais detalhes em `integracoes/photocraft/LEIA-ME.md`.

## Agentes (opcional)

A pasta `.claude/` tem os agentes especialistas (recortista, colorista, retocador, iluminador), as skills e a
memória de cada um. Para usá-los, abra a pasta do projeto no **Claude Code**; ele lê o `CLAUDE.md` e carrega
sozinho tudo o que está em `.claude/`. Sem o Claude Code, nada muda: os mesmos comandos acima rodam à mão.

Para o Claude Code controlar o ComfyUI e o PhotoCraft por MCP: copie `.mcp.json.exemplo` para `.mcp.json`,
instale `pip install comfy-mcp "comfy-cli>=1.14.0"` no mesmo ambiente e abra o Claude Code a partir dele
(o `photocraft-cli` precisa estar no `PATH`). Detalhes em `integracoes/comfyui/LEIA-ME.md`.

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
| `o ComfyUI não respondeu` ou `Connection refused` | O servidor do ComfyUI não está rodando: ligue-o (Nível 2) e deixe o terminal aberto. Confira também a porta e a chave `url` do `integracoes/comfyui/config.yaml` |
| `operator torchvision::nms does not exist` ao ligar o ComfyUI | O torchvision não casa com o torch (veio um de placa de vídeo). Rode `pip install --force-reinstall --no-deps torchvision --index-url https://download.pytorch.org/whl/cpu` |
| `Node 'GeraComporPeca' not found` (ou `GeraFichaPrompt`) | O link do passo 4 do Nível 2 não existe ou aponta para o lugar errado: `ls -l ../ComfyUI/custom_nodes/`. Reinicie o ComfyUI depois de criar o link |
| `WorkflowRecusado` ou `Prompt outputs failed validation`, citando `ckpt_name` | O modelo não está em `ComfyUI/models/checkpoints/` (passo 5) ou o nome no `integracoes/comfyui/config.yaml` é outro. O motivo completo aparece no terminal do ComfyUI |
| `photocraft-cli não encontrado` | Defina `PHOTOCRAFT_CLI` ou ponha o executável no `PATH` (Nível 4) |
| Memória acabando na geração | O modelo em CPU usa muita memória: feche outros programas; com menos de 12 GB não foi testado |
| `acabar.py` recusa a receita | Leu a mensagem: ela diz qual passo e por quê (por exemplo, camada que a peça não tem) |

Para conferir tudo de uma vez depois de instalar: `python -m pytest -q`. Os testes que dependem do
scikit-image ou do PhotoCraft aparecem como `skipped` enquanto eles não estiverem instalados.
