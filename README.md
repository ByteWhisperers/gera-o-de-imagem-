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
python pipeline.py fichas/arara/ficha-v1.0.yaml

# partes geradas por IA e registradas em partes/arara/registro.yaml
python pipeline.py fichas/arara/ficha-v1.0.yaml --provedor registro --figurino turista
```

Saída em `saida/<marca>/`: um `.psd` com uma camada por item da ficha, `.png`, `.webp` e `relatorio-<provedor>-<figurino>.json` com a origem de cada parte, o custo e o resultado do QA.

## Pastas

| Pasta | O que tem |
|---|---|
| `referencias/` | As mídias que queremos copiar |
| `fichas/` | Fichas de estilo, medidas e evidência |
| `partes/` | Partes geradas por IA e o registro com a receita de cada uma |
| `motor/` | Código: ficha, portão de geração, recorte, texto, compositor, QA |
| `ferramentas/` | Medição das referências para a desconstrução |
| `.claude/skills/` | Protocolo e memória de cada agente especialista |
| `testes/` | Testes automáticos |

## Estado

Teste 1 (09/10/2026): ficha ARARA v1.0 em proposta, partes geradas com `fal-ai/flux/schnell` (cerca de US$0,018 no total), composição em PSD funcionando. ComfyUI entra como provedor do portão na fase 3.

Fontes: Montserrat (SIL Open Font License 1.1, `fontes/OFL.txt`).
