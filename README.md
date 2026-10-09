# Produção de imagem

Copia o padrão visual de uma mídia de referência e gera peças novas no mesmo padrão, em camadas.

```
referências ──► ficha de estilo ──► partes geradas ──► composição em camadas ──► PSD + PNG/WebP
 (exemplos)     (desconstrução)     (portão de geração)  (pela ficha)              + relatório de QA
```

A **ficha de estilo** (`fichas/<marca>/ficha-vX.Y.yaml`) é o contrato entre as etapas. A desconstrução escreve nela; criação e composição só leem.

## Rodar

```bash
pip install -r requirements-dev.txt
python -m pytest -q

# custo zero: partes de rascunho, testa layout, texto e camadas
python pipeline.py fichas/arara/ficha-v1.1.yaml --tema telegram

# partes geradas no ComfyUI local (grátis) e registradas em partes/arara/registro.yaml
python pipeline.py fichas/arara/ficha-v1.1.yaml --provedor comfyui --tema telegram --formato promo

# partes já registradas (por exemplo as do fal no teste 1, ficha v1.0)
python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --tema turista
```

O **tema** liga a mensagem ao mascote: escolhe o figurino, o que ele segura, os objetos em volta (camada `entorno`) e as linhas de texto de exemplo. Os temas ficam na ficha.

Saída em `saida/<marca>/`: um `.psd` com uma camada por item da ficha, `.png`, `.webp` e `relatorio-<provedor>-<tema>.json` com a origem de cada parte, o custo e o resultado do QA.

Integrações: `integracoes/comfyui/LEIA-ME.md` (geração e fluxo completo) e `integracoes/photocraft/LEIA-ME.md` (editor do PSD). Os dois têm MCP; veja `.mcp.json.exemplo`.

## Pastas

| Pasta | O que tem |
|---|---|
| `referencias/` | As mídias que queremos copiar |
| `fichas/` | Fichas de estilo, medidas e evidência |
| `partes/` | Partes geradas por IA e o registro com a receita de cada uma |
| `motor/` | Código: ficha, portão de geração, recorte, texto, compositor, QA |
| `ferramentas/` | Medição das referências para a desconstrução |
| `integracoes/` | ComfyUI (nós, grafos, fluxo) e PhotoCraft (conferência do PSD) |
| `.claude/skills/` | Protocolo e memória de cada agente especialista |
| `testes/` | Testes automáticos |

## Estado

- Teste 1 (09/10/2026): ficha ARARA v1.0, partes geradas com `fal-ai/flux/schnell` (cerca de US$0,018 no total), composição em PSD funcionando.
- Fluxo ComfyUI (09/10/2026): ficha v1.1 aprovada com temas; ComfyUI local com SD-Turbo (grátis, CPU, licença não comercial) gera as 3 partes e monta o PSD num só fluxo; o PhotoCraft abre o PSD com as mesmas camadas.

Fontes: Montserrat (SIL Open Font License 1.1, `fontes/OFL.txt`).
