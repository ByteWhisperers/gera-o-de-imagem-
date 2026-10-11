"""Comparador: mede cada parte da peça gerada contra a mesma parte isolada na referência.

O QA antigo (motor/qa.py) só confere faixas de números da ficha e aprovou
um rascunho com uma elipse vermelha no lugar da arara. Aqui a régua é a
própria referência, parte por parte, usando as máscaras do grafo:

  dE00          diferença média de cor (CIEDE2000) pixel a pixel, em 1/4 da
                resolução (para não punir detalhe fino). Abaixo de 2 o olho não
                vê; de 2 a 10 vê de relance; acima de 10 é outra cor.
  ssim          semelhança de estrutura (formas e bordas), de 0 a 1.
  paleta_dE     diferença entre as paletas de 8 cores (o "clima" de cor),
                que não depende de as formas estarem no mesmo lugar.
  cobertura     sobreposição (IoU) entre onde a parte está na gerada e onde
                está na referência. Mostra parte perdida, sobrando ou fora do lugar.
  borda_opaca   fração da borda da camada que é opaca sem encostar na borda da
                peça: é o "corte reto" que aparece quando um recorte sai torto.

A peça inteira é medida sem a zona do texto e do logo, que são de código e
mudam de propósito (os testes usam texto neutro).

Os limites de aprovação ainda não estão calibrados: isso é a fase 3 (faixa
natural medida entre as referências). Por enquanto as faixas de leitura são
as usuais do CIEDE2000.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import grafo as G

# ---------------------------------------------------------------- cor


def rgb_para_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB 0-255 -> CIELAB (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """Diferença de cor CIEDE2000 (Sharma, Wu e Dalal, 2005), vetorizada."""
    L1, a1, b1 = np.moveaxis(np.asarray(lab1, np.float64), -1, 0)
    L2, a2, b2 = np.moveaxis(np.asarray(lab2, np.float64), -1, 0)
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G_ = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G_) * a1, (1 + G_) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm = (L1 + L2) / 2, (C1p + C2p) / 2
    soma = h1p + h2p
    hpm = np.where(C1p * C2p == 0, soma,
                   np.where(np.abs(h1p - h2p) <= 180, soma / 2, np.where(soma < 360, (soma + 360) / 2, (soma - 360) / 2)))
    T = (1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm))
         + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63)))
    dtheta = 30 * np.exp(-(((hpm - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def leitura_de(de: float) -> str:
    if de < 2:
        return "igual a olho nu"
    if de < 5:
        return "quase igual"
    if de < 10:
        return "parecido"
    if de < 20:
        return "diferente"
    return "muito diferente"


# ---------------------------------------------------------------- medidas


def _reduzir(rgb: np.ndarray, m: np.ndarray, f: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Média por bloco f x f, só dos pixels da máscara."""
    H, W = m.shape
    h, w = H // f, W // f
    r = rgb[: h * f, : w * f].astype(np.float64).reshape(h, f, w, f, 3)
    k = m[: h * f, : w * f].astype(np.float64).reshape(h, f, w, f)
    soma = (r * k[..., None]).sum((1, 3))
    n = k.sum((1, 3))
    return soma / np.maximum(n, 1)[..., None], n >= f * f / 2


def de_medio(a: np.ndarray, b: np.ndarray, m: np.ndarray) -> float:
    ra, ok = _reduzir(a, m)
    rb, _ = _reduzir(b, m)
    if not ok.any():
        return float("nan")
    return float(de2000(rgb_para_lab(ra[ok]), rgb_para_lab(rb[ok])).mean())


def _media_janela(x: np.ndarray, r: int) -> np.ndarray:
    """Média numa janela (2r+1)^2 por imagem integral (bordas repetidas)."""
    p = np.pad(x, r + 1, mode="edge").cumsum(0).cumsum(1)
    n = 2 * r + 1
    s = p[n:, n:] - p[:-n, n:] - p[n:, :-n] + p[:-n, :-n]
    return s[: x.shape[0], : x.shape[1]] / (n * n)


def ssim(a: np.ndarray, b: np.ndarray, m: np.ndarray, r: int = 3) -> float:
    """SSIM em cinza (janela 7x7), média só dentro da máscara."""
    ga = a.astype(np.float64) @ [0.299, 0.587, 0.114]
    gb = b.astype(np.float64) @ [0.299, 0.587, 0.114]
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _media_janela(ga, r), _media_janela(gb, r)
    va = _media_janela(ga * ga, r) - ma ** 2
    vb = _media_janela(gb * gb, r) - mb ** 2
    cab = _media_janela(ga * gb, r) - ma * mb
    s = ((2 * ma * mb + c1) * (2 * cab + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))
    return float(s[m].mean()) if m.any() else float("nan")


def paleta_lab(rgb: np.ndarray, m: np.ndarray, n: int = 8) -> tuple[np.ndarray, np.ndarray]:
    amostra = rgb[m].astype(np.uint8)
    amostra = amostra[:: max(1, len(amostra) // 40000)]
    lado = max(1, int(np.sqrt(len(amostra))))
    q = Image.fromarray(amostra[: lado * lado].reshape(lado, lado, 3)).quantize(n, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[: n * 3], np.float64).reshape(-1, 3)
    contagem = dict((i, c) for c, i in q.getcolors())
    pesos = np.array([contagem.get(i, 0) for i in range(len(pal))], np.float64)
    return rgb_para_lab(pal), pesos / max(pesos.sum(), 1)


def paleta_de(a: np.ndarray, b: np.ndarray, ma: np.ndarray, mb: np.ndarray) -> float:
    """Cada cor de uma paleta procura a mais próxima na outra; média ponderada, nos dois sentidos."""
    la, pa = paleta_lab(a, ma)
    lb, pb = paleta_lab(b, mb)
    d = de2000(la[:, None, :], lb[None, :, :])
    return float(((d.min(1) * pa).sum() + (d.min(0) * pb).sum()) / 2)


def perfil(rgb: np.ndarray, m: np.ndarray) -> dict:
    """Quatro números de acabamento de uma região, comparáveis entre peças de posições diferentes.

    luz        L* médio (0 preto, 100 branco)
    contraste  desvio de L*
    saturacao  croma médio (a*, b*)
    nitidez    energia de detalhe fino: média de |L* - L* desfocado em 5x5|
    """
    if not m.any():
        return {"luz": None, "contraste": None, "saturacao": None, "nitidez": None}
    lab = rgb_para_lab(rgb)
    L = lab[..., 0]
    detalhe = np.abs(L - _media_janela(L, 2))
    dentro = m & _sem_borda(m)
    return {"luz": round(float(L[m].mean()), 1), "contraste": round(float(L[m].std()), 1),
            "saturacao": round(float(np.hypot(lab[..., 1], lab[..., 2])[m].mean()), 1),
            "nitidez": round(float(detalhe[dentro if dentro.any() else m].mean()), 2)}


def _sem_borda(m: np.ndarray, r: int = 3) -> np.ndarray:
    """A máscara sem uma faixa de r pixels na borda (o recorte não conta como detalhe)."""
    return _media_janela(m.astype(np.float64), r) > 0.999


def cobertura(alfa: np.ndarray, ref: np.ndarray) -> float:
    u = (alfa | ref).sum()
    return float((alfa & ref).sum() / u) if u else float("nan")


def borda_opaca(rgba: np.ndarray, x: int, y: int, largura: int, altura: int) -> float:
    """Fração opaca da borda da camada, sem contar o que encosta na borda da peça."""
    a = rgba[..., 3] > 128
    h, w = a.shape
    lados = []
    if y > 0:
        lados.append(a[0])
    if y + h < altura:
        lados.append(a[-1])
    if x > 0:
        lados.append(a[:, 0])
    if x + w < largura:
        lados.append(a[:, -1])
    if not lados:
        return 0.0
    return float(np.concatenate(lados).mean())


# ---------------------------------------------------------------- peça


def camadas_do_psd(caminho: str | Path) -> dict[str, tuple[np.ndarray, int, int]]:
    """Camadas de imagem do PSD por nome, de baixo para cima, com a máscara de camada no alfa.

    Só camadas de pixels e objetos inteligentes (a prévia guardada do objeto já vem com
    os filtros inteligentes); ajustes, preenchimentos e grupos ficam de fora. Com nomes
    repetidos vale a de cima que está visível, a mesma que o PhotoCraft mostra por cima
    e que `Sessao.camada` escolhe para editar.
    """
    from psd_tools import PSDImage

    escolhidas: dict[str, object] = {}
    for l in reversed(list(PSDImage.open(caminho))):
        if l.kind not in ("pixel", "smartobject") or not l.visible or l.name in escolhidas:
            continue
        escolhidas[l.name] = l
    saida = {}
    for nome, l in reversed(list(escolhidas.items())):
        im = l.topil()
        if im is None:
            continue
        rgba = np.asarray(im.convert("RGBA")).copy()
        if l.mask is not None and not l.mask.disabled:
            rgba[..., 3] = (rgba[..., 3].astype(np.uint16) * _mascara_na_camada(l) // 255).astype(np.uint8)
        saida[nome] = (rgba, l.left, l.top)
    return saida


def _mascara_na_camada(l) -> np.ndarray:
    """A máscara de camada do psd-tools no tamanho da camada (fora dela, a cor de fundo da máscara)."""
    m = l.mask
    h, w = l.height, l.width
    tela = np.full((h, w), m.background_color, np.uint16)
    im = m.topil()
    if im is not None:
        a = np.asarray(im.convert("L"), np.uint16)
        x0, y0 = m.left - l.left, m.top - l.top
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(w, x0 + a.shape[1]), min(h, y0 + a.shape[0])
        if xb > xa and yb > ya:
            tela[ya:yb, xa:xb] = a[ya - y0 : yb - y0, xa - x0 : xb - x0]
    return tela


def camadas_no_final(final: Image.Image, camadas: dict[str, tuple[np.ndarray, int, int]]) -> dict[str, tuple[np.ndarray, int, int]]:
    """Cada camada com as cores da peça achatada no lugar dela e o alfa da própria camada.

    Para medir as partes de um PSD em que ajustes, estilos e filtros só aparecem no
    achatamento (o acabamento no PhotoCraft): a nota da parte passa a ser a de como
    ela ficou na peça.
    """
    fim = np.asarray(final.convert("RGB"))
    H, W = fim.shape[:2]
    saida = {}
    for nome, (rgba, x, y) in camadas.items():
        h, w = rgba.shape[:2]
        nova = np.zeros_like(rgba)
        nova[..., 3] = rgba[..., 3]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 > x0 and y1 > y0:
            nova[y0 - y : y1 - y, x0 - x : x1 - x, :3] = fim[y0:y1, x0:x1]
        saida[nome] = (nova, x, y)
    return saida


def na_tela(rgba: np.ndarray, x: int, y: int, largura: int, altura: int) -> np.ndarray:
    tela = np.zeros((altura, largura, 4), np.uint8)
    h, w = rgba.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(largura, x + w), min(altura, y + h)
    tela[y0:y1, x0:x1] = rgba[y0 - y : y1 - y, x0 - x : x1 - x]
    return tela


def medir(grafo: dict, final: Image.Image, camadas: dict[str, tuple[np.ndarray, int, int]],
          so: list[str] | None = None) -> dict:
    """Notas da peça inteira e de cada camada gerada, contra a referência do grafo.

    `so` limita as camadas medidas (as que o workflow gerou); sem ele, todas as do grafo.
    """
    W, H = grafo["tamanho_px"]
    ref = np.asarray(Image.open(G.RAIZ / grafo["referencia"]).convert("RGB"))
    fim = np.asarray(final.convert("RGB").resize((W, H)))
    codigo = np.zeros((H, W), bool)
    for n in grafo["nos"]:
        if n["tipo"] in ("texto", "logo") and "caixa" in n:
            x, y, w, h = n["caixa"]
            f = 0.3 * h * H
            codigo[max(0, int(y * H - f)) : int((y + h) * H + f), max(0, int(x * W - f)) : int((x + w) * W + f)] = True
    resto = ~codigo
    notas = {"peca": {"dE00": round(de_medio(ref, fim, resto), 2), "ssim": round(ssim(ref, fim, resto), 3),
                      "paleta_dE": round(paleta_de(ref, fim, resto, resto), 2), "fora": "texto e logo"}}
    notas["peca"]["leitura"] = leitura_de(notas["peca"]["dE00"])
    for camada in (so if so is not None else G.camadas_geradas(grafo)):
        if camada not in camadas:
            notas[camada] = {"falta": True}
            continue
        rgba, x, y = camadas[camada]
        tela = na_tela(rgba, x, y, W, H)
        alvo = G.mascara_camada(grafo, camada)
        if camada == "cena":
            alvo = alvo & resto                        # onde o fundo aparece na referência
            gerada = np.ones((H, W), bool)
        else:
            gerada = tela[..., 3] > 128
        dentro = alvo & gerada
        n = {"dE00": round(de_medio(ref, tela[..., :3], dentro), 2) if dentro.any() else None,
             "ssim": round(ssim(ref, tela[..., :3], dentro), 3) if dentro.any() else None,
             "paleta_dE": round(paleta_de(ref, tela[..., :3], alvo, gerada), 2) if gerada.any() else None}
        if camada != "cena":                           # o fundo cobre a peça toda por definição
            n["cobertura"] = round(cobertura(gerada, alvo), 3)
            n["borda_opaca"] = round(borda_opaca(rgba, x, y, W, H), 3)
        n["leitura"] = leitura_de(n["dE00"]) if n["dE00"] is not None else "parte ausente"
        notas[camada] = n
    return notas


# ---------------------------------------------------------------- prancha


def _fonte(tamanho: int):
    for nome in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            pass
    return ImageFont.load_default(size=tamanho)


def prancha(grafo: dict, pecas: dict[str, Image.Image], notas: dict[str, dict], largura: int = 1800) -> Image.Image:
    """Uma linha por peça (a referência primeiro) com as notas ao lado, e embaixo o
    detalhe de cada camada gerada: o mesmo recorte na referência e em cada candidata."""
    W, H = grafo["tamanho_px"]
    ref = Image.open(G.RAIZ / grafo["referencia"]).convert("RGB")
    todas = {"referência": ref, **pecas}
    f1, f2 = _fonte(30), _fonte(24)
    lado = 1100
    alt = round(lado * H / W)
    blocos = []
    for nome, im in todas.items():
        b = Image.new("RGB", (largura, alt + 30), (22, 22, 22))
        b.paste(im.convert("RGB").resize((lado, alt)), (20, 15))
        d = ImageDraw.Draw(b)
        x, y = lado + 50, 20
        d.text((x, y), nome, font=f1, fill=(240, 240, 240))
        y += 50
        if nome == "referência":
            d.text((x, y), "a régua: cada parte é", font=f2, fill=(170, 170, 170))
            d.text((x, y + 32), "medida contra esta", font=f2, fill=(170, 170, 170))
        for parte, n in notas.get(nome, {}).items():
            if n.get("falta"):
                texto, cor = f"{parte}: não tem", (240, 150, 90)
            else:
                texto = f"{parte}: ΔE {n['dE00']:.1f} ({n['leitura']})"
                cor = (120, 220, 120) if n["dE00"] < 10 else (240, 200, 90) if n["dE00"] < 20 else (240, 120, 90)
            d.text((x, y), texto, font=f2, fill=cor)
            y += 36
            if "cobertura" in n and n["cobertura"] < 0.9:
                d.text((x + 30, y), f"só {n['cobertura']:.0%} no lugar certo", font=f2, fill=(240, 120, 90))
                y += 36
        blocos.append(b)
    for camada in G.camadas_geradas(grafo):
        if camada == "cena":
            continue
        cx, cy, cw, ch = G.caixa_px(G.mascara_camada(grafo, camada), margem=0.03)
        # todas as candidatas lado a lado: um recorte largo (ex.: a frente) encolhe para caber
        lado_d = min(round(cw * 360 / ch), (largura - 20) // len(todas) - 20)
        alt_d = round(ch * lado_d / cw)
        n_col = len(todas)
        b = Image.new("RGB", (largura, alt_d + 70), (22, 22, 22))
        d = ImageDraw.Draw(b)
        d.text((20, 12), f"detalhe: {camada}", font=f2, fill=(240, 240, 240))
        for i, (nome, im) in enumerate(list(todas.items())[:n_col]):
            corte = im.convert("RGB").resize((W, H)).crop((cx, cy, cx + cw, cy + ch)).resize((lado_d, alt_d))
            b.paste(corte, (20 + i * (lado_d + 20), 54))
            d.text((24 + i * (lado_d + 20), 58), nome, font=_fonte(20), fill=(255, 255, 255))
        blocos.append(b)
    total = Image.new("RGB", (largura, sum(b.height for b in blocos)), (22, 22, 22))
    y = 0
    for b in blocos:
        total.paste(b, (0, y))
        y += b.height
    return total
