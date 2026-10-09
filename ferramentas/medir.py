"""Mede as referências para a desconstrução: o analista lê números, não chuta.

Uso:
    python ferramentas/medir.py referencias/arara > fichas/arara/medidas.json

Para cada imagem devolve tamanho, proporção, brilho por faixa vertical
(esquerda / centro / direita), a paleta dominante e onde fica o ponto
mais claro do centro (o sol, nas peças da Arara).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FAIXAS = {"esquerda": (0.0, 0.35), "centro": (0.35, 0.65), "direita": (0.65, 1.0)}


def luminancia(rgb: np.ndarray) -> np.ndarray:
    """Luminância 0–255 (Rec. 601), a mesma escala usada nas fichas."""
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def paleta(im: Image.Image, n: int = 6) -> list[dict]:
    pequena = im.convert("RGB").resize((256, max(1, int(256 * im.height / im.width))))
    q = pequena.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    cores = q.getpalette()[: n * 3]
    contagem = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in contagem)
    saida = []
    for c, i in contagem:
        r, g, b = cores[i * 3 : i * 3 + 3]
        saida.append({"cor": f"#{r:02x}{g:02x}{b:02x}", "fracao": round(c / total, 3)})
    return saida


def ponto_claro(lum: np.ndarray, x0: float, x1: float) -> dict:
    """Centro de massa do 0,5% mais claro dentro da faixa [x0, x1] da largura."""
    h, w = lum.shape
    a, b = int(w * x0), int(w * x1)
    faixa = lum[:, a:b]
    corte = np.percentile(faixa, 99.5)
    ys, xs = np.nonzero(faixa >= corte)
    return {
        "x_w": round((xs.mean() + a) / w, 3),
        "y_h": round(ys.mean() / h, 3),
        "L": round(float(corte), 1),
    }


def medir(caminho: Path) -> dict:
    im = Image.open(caminho)
    rgb = np.asarray(im.convert("RGB").filter(ImageFilter.BoxBlur(2)), dtype=np.float32)
    lum = luminancia(rgb)
    h, w = lum.shape
    faixas = {}
    for nome, (x0, x1) in FAIXAS.items():
        parte = lum[:, int(w * x0) : int(w * x1)]
        faixas[nome] = {"media": round(float(parte.mean()), 1), "mediana": round(float(np.median(parte)), 1)}
    return {
        "arquivo": caminho.as_posix(),
        "largura": w,
        "altura": h,
        "proporcao": round(w / h, 3),
        "L_mediana": round(float(np.median(lum)), 1),
        "L_faixas": faixas,
        "ponto_claro_centro": ponto_claro(lum, 0.30, 0.70),
        "paleta": paleta(im),
    }


def main(pasta: str) -> None:
    arquivos = sorted(p for p in Path(pasta).rglob("*") if p.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg"})
    json.dump([medir(p) for p in arquivos], sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "referencias")
