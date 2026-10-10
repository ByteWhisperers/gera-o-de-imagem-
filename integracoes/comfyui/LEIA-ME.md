# ComfyUI no projeto

O ComfyUI gera as partes (cena, mascote, entorno) e, pelo fluxo completo, já
monta a peça em PSD. A lógica fica em `motor/`; aqui estão só a ligação.

| Arquivo | Para que serve |
|---|---|
| `config.yaml` | Modelo, passos, tamanhos e método de recorte. Trocar de modelo mexe aqui, não na ficha. |
| `grafos/parte.json` | Grafo de uma parte só. O portão usa (`--provedor comfyui`). |
| `grafos/fluxo.json` | Fluxo completo: 3 partes + nó "Compor peça (PSD)". |
| `nos_gera_imagem/` | Nós próprios: "Ficha de estilo: prompt" e "Compor peça (PSD)". |
| `rodar_fluxo.py` | Roda o fluxo completo pela API, sem abrir o navegador. |
| (gerado) `fluxos/<marca>/workflows/*.json` | Workflows que o compilador (`motor/compilador.py`) monta a partir do grafo de uma referência. Não se escreve à mão. |

## Instalar (testado com ComfyUI 0.39.0, CPU)

```bash
git clone https://github.com/comfyanonymous/ComfyUI
python -m venv comfy-venv && . comfy-venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # ou a versão da sua GPU
pip install -r ComfyUI/requirements.txt
pip install -r <repo>/requirements.txt "rembg[cpu]"                  # o motor e o recorte por modelo
ln -s <repo>/integracoes/comfyui/nos_gera_imagem ComfyUI/custom_nodes/nos_gera_imagem
# modelo de teste: sd_turbo.safetensors em ComfyUI/models/checkpoints/
python ComfyUI/main.py --cpu --listen 127.0.0.1 --port 8188
```

## Rodar

```bash
# uma peça inteira (cerca de 2,5 min em CPU)
python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo --saida peca.png

# ou parte por parte pelo portão, que registra a receita em partes/<marca>/registro.yaml
python pipeline.py fichas/arara/ficha-v1.1.yaml --provedor comfyui --tema telegram --formato promo
```

## Workflow montado a partir do grafo (fase 1)

O `motor/compilador.py` lê o grafo de uma referência (`fichas/<marca>/grafos/<peca>.json`)
e monta o workflow: um ramo por camada gerada, cada um na região da sua parte na
referência (recorte, img2img, máscara). Os botões ficam em `config.yaml`, chave `compilador`.

```bash
python tentativa.py fichas/arara/grafos/promo-telegram.json --so-compilar   # monta e confere (nós, modelos, nada pago)
python tentativa.py fichas/arara/grafos/promo-telegram.json                 # roda, monta o PSD e compara
comfy --json workflow validate --workflow fluxos/arara/workflows/<sha>.json # segunda conferência, com o comfy-cli
```

O fluxo completo salva em `ComfyUI/output/gera/<marca>/<formato>-<tema>-comfyui.{psd,png,webp,qa.json}`.

## MCP

O `comfy-mcp` (https://github.com/Comfy-Org/comfy-mcp, `pip install comfy-mcp "comfy-cli>=1.14.0"`)
deixa um agente rodar fluxos e ver a fila. Teste rápido:

```bash
python integracoes/testar_mcp.py --chamar server_info -- comfy-mcp
```

## Limites do modelo de teste

- **SD-Turbo** é grátis e roda em CPU, mas a licença é de pesquisa, **não comercial**. Serve para validar o fluxo; para produção, troque o `checkpoint` no `config.yaml`.
- Ele não obedece ao "fundo cinza liso" do prompt. Por isso o `config.yaml` manda recortar o mascote com modelo (`rembg`, isnet) e o entorno pela cor da borda.
- Ele escreve letras falsas em camisetas e placas. O texto de verdade sempre vem do código.
