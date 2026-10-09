"""Roda o fluxo inteiro dentro do ComfyUI: 3 partes geradas + composição em PSD.

Uso:
    python integracoes/comfyui/rodar_fluxo.py --tema telegram --formato promo

O mesmo grafo (grafos/fluxo.json) pode ser aberto no canvas do ComfyUI para
ver e mexer em cada etapa. A peça sai em ComfyUI/output/gera/<marca>/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from motor.portao import executar_comfyui, preencher  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ficha", default="fichas/arara/ficha-v1.1.yaml")
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
    }
    grafo = preencher(json.loads((RAIZ / "integracoes/comfyui/grafos/fluxo.json").read_text()), valores)
    final = executar_comfyui(cfg["url"], grafo)
    if a.saida:
        final.save(a.saida)
    print(f"ok: {final.size[0]}x{final.size[1]}" + (f" -> {a.saida}" if a.saida else ""))


if __name__ == "__main__":
    main()
