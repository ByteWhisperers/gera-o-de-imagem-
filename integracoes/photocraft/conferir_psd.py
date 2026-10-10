"""Confere que o PhotoCraft abre o nosso PSD do jeito que nós o montamos.

Duas checagens, sem custo:
1. as camadas que o PhotoCraft lê têm os nomes e a ordem da ficha;
2. o PhotoCraft achata o PSD num PNG quase igual ao nosso (diferença média
   pequena, por arredondamento de mistura).

Uso:
    python integracoes/photocraft/conferir_psd.py saida/arara/promo-telegram-comfyui.psd \
        --ficha fichas/arara/ficha-v1.2.yaml --cli caminho/para/photocraft-cli
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from motor import ficha as F  # noqa: E402


def conferir(psd: Path, ficha: dict, cli: str, diferenca_max: float = 6.0) -> dict:
    info = json.loads(subprocess.run([cli, "info", str(psd), "--compact"], check=True,
                                     capture_output=True, text=True).stdout)
    nomes = [l["name"] for l in reversed(info["layers"])]   # o PhotoCraft lista de cima para baixo
    esperado = [c["id"] for c in ficha["camadas"]]
    with tempfile.TemporaryDirectory() as tmp:
        render = Path(tmp) / "render.png"
        subprocess.run([cli, "convert", str(psd), str(render)], check=True, capture_output=True)
        deles = np.asarray(Image.open(render).convert("RGB"), dtype=np.float32)
    nosso = np.asarray(Image.open(psd.with_suffix(".png")).convert("RGB"), dtype=np.float32)
    diferenca = float(np.abs(deles - nosso).mean()) if deles.shape == nosso.shape else float("inf")
    return {"camadas": nomes, "camadas_ok": nomes == esperado,
            "diferenca_media": round(diferenca, 2), "render_ok": diferenca <= diferenca_max}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("psd", type=Path)
    ap.add_argument("--ficha", default="fichas/arara/ficha-v1.2.yaml")
    ap.add_argument("--cli", default="photocraft-cli")
    a = ap.parse_args()
    r = conferir(a.psd, F.carregar(a.ficha), a.cli)
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0 if r["camadas_ok"] and r["render_ok"] else 1)


if __name__ == "__main__":
    main()
