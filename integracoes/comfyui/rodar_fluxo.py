"""Roda o fluxo inteiro dentro do ComfyUI: as partes geradas + composição em PSD.

Uso:
    python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo

O mesmo grafo (grafos/fluxo.json) pode ser aberto no canvas do ComfyUI para
ver e mexer em cada etapa. A peça sai em ComfyUI/output/gera/<marca>/.
O grafo traz um ramo por parte (cena, mascote, entorno, frente); os ramos de
partes que a ficha escolhida não tem saem antes de mandar (a v1.1 não tem frente).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from motor import ficha as F  # noqa: E402
from motor.portao import executar_comfyui, preencher  # noqa: E402


def so_partes_da_ficha(grafo: dict, partes) -> dict:
    """Tira os ramos de partes que a ficha não tem e os nós que só serviam a eles."""
    fora = {i for i, n in grafo.items() if n["class_type"] == "GeraFichaPrompt" and n["inputs"]["parte"] not in partes}
    grafo = {i: n for i, n in grafo.items() if i not in fora}
    for n in grafo.values():
        if n["class_type"] == "GeraComporPeca":
            for p in [p for p in n["inputs"] if p not in partes and p not in ("cena", "ficha", "formato", "tema")]:
                del n["inputs"][p]
    # do nó de saída para trás: o que ninguém usa sai
    usados = {i for i, n in grafo.items() if n["class_type"] == "GeraComporPeca"}
    pilha = list(usados)
    while pilha:
        for v in grafo[pilha.pop()]["inputs"].values():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] in grafo and v[0] not in usados:
                usados.add(v[0])
                pilha.append(v[0])
    return {i: n for i, n in grafo.items() if i in usados}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ficha", default="fichas/arara/ficha-v1.2.yaml")
    ap.add_argument("--tema", default="instagram")
    ap.add_argument("--formato", default="promo", choices=["home", "promo"])
    ap.add_argument("--semente", type=int, default=519)
    ap.add_argument("--saida", help="onde salvar o PNG final devolvido pelo ComfyUI")
    a = ap.parse_args()
    cfg = yaml.safe_load((RAIZ / "integracoes/comfyui/config.yaml").read_text(encoding="utf-8"))
    t = cfg["tamanhos"]
    valores = {
        "checkpoint": cfg["checkpoint"], "negativo": cfg["negativo"], "passos": cfg["passos"], "cfg": cfg["cfg"],
        "ficha": a.ficha, "tema": a.tema, "formato": a.formato, "semente": a.semente,
        "cena_largura": t["cena"][a.formato][0], "cena_altura": t["cena"][a.formato][1],
        "mascote_largura": t["mascote"][0], "mascote_altura": t["mascote"][1],
        "entorno_largura": t["entorno"][0], "entorno_altura": t["entorno"][1],
        "frente_largura": t["frente"][0], "frente_altura": t["frente"][1],
    }
    grafo = json.loads((RAIZ / "integracoes/comfyui/grafos/fluxo.json").read_text())
    grafo = preencher(so_partes_da_ficha(grafo, F.carregar(RAIZ / a.ficha)["partes"]), valores)
    final = executar_comfyui(cfg["url"], grafo)
    if a.saida:
        final.save(a.saida)
    print(f"ok: {final.size[0]}x{final.size[1]}" + (f" -> {a.saida}" if a.saida else ""))


if __name__ == "__main__":
    main()
