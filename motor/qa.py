"""Revisor automático: compara a peça final com a ficha e diz o que passou."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageColor

from ferramentas.medir import luminancia


def conferir(ficha: dict, formato: str, final: Image.Image, camadas: list) -> list[dict]:
    regras = ficha["qa"]
    rgb = np.asarray(final.convert("RGB"), dtype=np.float32)
    lum = luminancia(rgb)
    h, w = lum.shape
    resultados = []

    def registrar(nome: str, ok: bool, valor, esperado):
        resultados.append({"regra": nome, "ok": bool(ok), "valor": valor, "esperado": esperado})

    lo, hi = regras["L_mediana"]
    med = round(float(np.median(lum)), 1)
    registrar("L_mediana", lo <= med <= hi, med, [lo, hi])

    if regras.get("esquerda_mais_escura_que_centro"):
        esq = round(float(np.median(lum[:, : int(w * 0.35)])), 1)
        cen = round(float(np.median(lum[:, int(w * 0.35) : int(w * 0.65)])), 1)
        registrar("esquerda_mais_escura_que_centro", esq < cen, {"esquerda": esq, "centro": cen}, "esquerda < centro")

    ouro = np.array(ImageColor.getrgb(ficha["cores"]["ouro"]), dtype=np.float32)
    perto = np.linalg.norm(rgb - ouro, axis=2) < 60
    fracao = round(float(perto.mean()), 4)
    registrar("ouro_presente", fracao >= regras["ouro_presente_min"], fracao, f">= {regras['ouro_presente_min']}")

    # Partes que a ficha pede transparentes precisam chegar recortadas.
    for c in camadas:
        parte = next((k["parte"] for k in ficha["camadas"] if k["id"] == c.nome and k["tipo"] == "gerada"), None)
        if parte and ficha["partes"][parte].get("transparente"):
            vazio = round(float((np.asarray(c.imagem.getchannel("A")) < 10).mean()), 3)
            registrar(f"{c.nome}_recortado", vazio >= regras.get("recorte_vazio_min", 0.15), vazio,
                      f">= {regras.get('recorte_vazio_min', 0.15)}")

    if regras.get("texto_dentro_da_zona"):
        caixa = ficha["layout"][formato]["texto"]
        texto = next(c for c in camadas if c.nome == "texto")
        a = np.asarray(texto.imagem.getchannel("A")) > 200
        ys, xs = np.nonzero(a)
        x0, x1 = (xs.min() + texto.x) / w, (xs.max() + texto.x) / w
        y0, y1 = (ys.min() + texto.y) / h, (ys.max() + texto.y) / h
        folga = 0.02
        dentro = (x0 >= caixa["x"] - folga and x1 <= caixa["x"] + caixa["w"] + folga
                  and y0 >= caixa["y"] - folga and y1 <= caixa["y"] + caixa["h"] + folga)
        registrar("texto_dentro_da_zona", dentro, [round(v, 3) for v in (x0, y0, x1, y1)],
                  [caixa["x"], caixa["y"], round(caixa["x"] + caixa["w"], 3), round(caixa["y"] + caixa["h"], 3)])
    return resultados
