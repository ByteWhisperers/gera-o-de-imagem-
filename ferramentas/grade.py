"""Grade de frações sobre uma referência, para marcar contornos a olho com precisão.

Uso:
    python ferramentas/grade.py referencias/arara/home/banner1.webp -o grade.jpg
    python ferramentas/grade.py fichas/arara/grafos/home-convite-1.marcacao.yaml -o grade.jpg
    python ferramentas/grade.py fichas/arara/grafos/home-convite-1.marcacao.yaml --zoom 0.6 0 0.4 1 -o zoom.jpg
    python ferramentas/grade.py fichas/arara/grafos/home-convite-1.marcacao.yaml --zoom 0.6 0 0.4 1 --encaixado -o z.jpg

As linhas e os números são frações da peça INTEIRA (também no zoom), as mesmas
da marcação. Com uma marcação, desenha por cima o que o agente marcou:
polígonos com os vértices numerados, elipses, caixas e as zonas de texto e logo.
Com --encaixado, desenha também a borda das máscaras que a desconstrução já
encaixou (pasta do grafo), para conferir o recorte de perto.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.comparar import _fonte  # noqa: E402

CORES = [(255, 60, 60), (255, 170, 0), (0, 220, 255), (255, 0, 255), (120, 255, 120), (160, 120, 255),
         (255, 255, 255), (255, 140, 180)]


def _passo_auto(lado_frac: float) -> float:
    for p in (0.005, 0.01, 0.02, 0.025, 0.05, 0.1):
        if lado_frac / p <= 24:
            return p
    return 0.1


def grade(im: Image.Image, zoom: tuple[float, float, float, float] = (0, 0, 1, 1), largura: int = 1600,
          passo: float | None = None, marcacao: dict | None = None, encaixado: Path | None = None) -> Image.Image:
    W, H = im.size
    zx, zy, zw, zh = zoom
    caixa = (round(zx * W), round(zy * H), round((zx + zw) * W), round((zy + zh) * H))
    recorte = im.convert("RGB").crop(caixa)
    esc = largura / recorte.width
    tela = recorte.resize((largura, round(recorte.height * esc)), Image.LANCZOS)
    d = ImageDraw.Draw(tela)
    f, fp = _fonte(15), _fonte(13)

    def px(x: float, y: float) -> tuple[float, float]:
        return ((x * W - caixa[0]) * esc, (y * H - caixa[1]) * esc)

    if encaixado is not None:
        from scipy import ndimage

        arr = np.asarray(tela).copy()
        for i, arq in enumerate(sorted(encaixado.glob("*.png"))):
            if arq.stem == "cena":
                continue
            m = np.asarray(Image.open(arq).convert("L").crop(caixa).resize(tela.size, Image.NEAREST)) > 127
            borda = ndimage.binary_dilation(m, iterations=2) & ~m
            arr[borda] = CORES[i % len(CORES)]
        tela = Image.fromarray(arr)
        d = ImageDraw.Draw(tela)

    passo = passo or _passo_auto(max(zw, zh))
    k0 = int(np.floor(zx / passo))
    for k in range(k0, int(np.ceil((zx + zw) / passo)) + 1):
        x = round(k * passo, 4)
        if zx <= x <= zx + zw:
            X = px(x, 0)[0]
            forte = abs(x * 10 - round(x * 10)) < 1e-6
            d.line([(X, 0), (X, tela.height)], fill=(255, 255, 255) if forte else (170, 170, 170), width=1)
            d.text((X + 2, 2), f"{x:g}", font=fp, fill=(255, 255, 0))
    for k in range(int(np.floor(zy / passo)), int(np.ceil((zy + zh) / passo)) + 1):
        y = round(k * passo, 4)
        if zy <= y <= zy + zh:
            Y = px(0, y)[1]
            forte = abs(y * 10 - round(y * 10)) < 1e-6
            d.line([(0, Y), (tela.width, Y)], fill=(255, 255, 255) if forte else (170, 170, 170), width=1)
            d.text((2, Y + 2), f"{y:g}", font=fp, fill=(255, 255, 0))

    if marcacao:
        for nome in ("zona_texto", "zona_logo"):
            if nome in marcacao:
                x, y, w, h = marcacao[nome]
                d.rectangle([px(x, y), px(x + w, y + h)], outline=(80, 255, 80), width=1)
                d.text(px(x, y + h), nome, font=fp, fill=(80, 255, 80))
        for x, y, w, h in marcacao.get("texto_linhas", []):
            d.rectangle([px(x, y), px(x + w, y + h)], outline=(80, 255, 80), width=2)
        for i, (id_, n) in enumerate(marcacao.get("nos", {}).items()):
            cor = CORES[i % len(CORES)]
            if "contorno" in n:
                pts = [px(x, y) for x, y in n["contorno"]]
                d.line(pts + [pts[0]], fill=cor, width=2)
                for j, p in enumerate(pts):
                    d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=cor)
                    d.text((p[0] + 4, p[1] - 14), str(j), font=fp, fill=cor)
                d.text(pts[0], id_, font=f, fill=cor)
            for e in n.get("elipses", []):
                x, y, w, h = e
                d.ellipse([px(x, y), px(x + w, y + h)], outline=cor, width=2)
                d.text(px(x, y), id_, font=fp, fill=cor)
            if "caixa" in n:
                x, y, w, h = n["caixa"]
                d.rectangle([px(x, y), px(x + w, y + h)], outline=cor, width=2)
                d.text(px(x, y), id_, font=fp, fill=cor)
    return tela


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", help="imagem da referência ou arquivo de marcação (.yaml)")
    ap.add_argument("-o", "--saida", required=True)
    ap.add_argument("--zoom", nargs=4, type=float, metavar=("X", "Y", "W", "H"), default=(0, 0, 1, 1))
    ap.add_argument("--passo", type=float, help="distância entre as linhas, em fração (padrão: automático)")
    ap.add_argument("--largura", type=int, default=1600)
    ap.add_argument("--encaixado", action="store_true", help="borda das máscaras já encaixadas (pasta do grafo)")
    a = ap.parse_args()
    entrada = Path(a.entrada).resolve()
    marcacao, pasta = None, None
    if entrada.suffix in (".yaml", ".yml"):
        marcacao = yaml.safe_load(entrada.read_text(encoding="utf-8"))
        imagem = RAIZ / marcacao["referencia"]
        pasta = entrada.parent / marcacao["peca"] / "mascaras"
    else:
        imagem = entrada
    if a.encaixado and (pasta is None or not pasta.exists()):
        sys.exit("--encaixado precisa de uma marcação já desconstruída (rode ferramentas/desconstruir.py antes)")
    tela = grade(Image.open(imagem), tuple(a.zoom), a.largura, a.passo, marcacao, pasta if a.encaixado else None)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    tela.save(a.saida, quality=88)
    print(a.saida)


if __name__ == "__main__":
    main()
