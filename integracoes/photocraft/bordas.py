"""Réguas de borda do acabamento: recorte, luz de contorno e estouro de nitidez.

O perfil (luz, contraste, saturação, nitidez) e o ΔE quase não mexem quando se limpa
uma franja ou se acende o contorno do mascote. Estas três réguas olham só a faixa em
volta do contorno de cada parte recortada (entorno, mascote, frente):

recorte (do recortista), com o alfa da camada e a peça com e sem a parte:
  franja          quanto a parte muda a luz do fundo do lado de fora da borda (4 px em
                  volta mais todo pixel meio transparente), por px de contorno.
                  Negativo = névoa ou franja escura; positivo = franja clara. Bom: até ±3.
  halo_fora       o mesmo em cor (ΔE76 por px de contorno); compare antes x depois.
  anel / anel_ref o anel de 2 px por dentro da borda contra a faixa logo atrás dele (ΔE76),
                  na peça e na referência: cor de fundo antigo presa na beirada sobe o anel.
  semi_%          pixels meio transparentes (alfa 8 a 128) em % da parte. Bom: até ~3.
  ilhas           pedacinhos soltos (alfa > 8, menos de 50 px). Bom: até ~5.
  borda_suave_%   pixels de beirada com alfa intermediário (0 = serrilhado).
  borda_opaca     fração opaca da moldura da camada que não encosta na borda da peça
                  (corte reto da imagem gerada). Bom: perto de 0.
  quadro_%        quanto da peça a parte cobre. Parte (fora a cena) com 90% ou mais
                  trouxe o fundo da imagem gerada junto.
  dE_borda        só em parte no lugar da referência (tentativa do loop): ΔE2000 numa
                  faixa de ±2 px na borda, contra a referência. Não deve subir.

contorno (do iluminador), na peça e na referência:
  brilho_fora     luz logo fora do contorno (0 a 15 px) menos a luz mais longe (30 a 60 px):
                  positivo = brilho em volta da parte.
  luz_borda       luz da faixa de dentro (0 a 8 px) menos a do miolo (15 a 40 px):
                  positivo = luz de contorno.
  lados           luz da faixa de dentro à esquerda, à direita e em cima (de onde vem a luz).

estouro (do retocador), nos pixels da própria camada antes x depois (filtros e retoques
nela; ajustes presos e estilos não contam):
  borda_% / dentro_%  pixels da faixa de dentro da borda (3 px) e do miolo que ficaram
                  mais claros que o máximo local de antes (5x5) por mais de 6 de luz:
                  o contorno branco da nitidez passada do ponto. Bom: borda até ~1%, miolo até ~3%.

Pixels cobertos por camadas da ficha acima da parte (frente, texto, logo...) ficam de fora.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

from motor import comparar as CMP
from motor import grafo as G

# ---------------------------------------------------------------- utilidades


def comer(m: np.ndarray, r: int) -> np.ndarray:
    return CMP._media_janela(m.astype(np.float64), r) > 0.999


def crescer(m: np.ndarray, r: int) -> np.ndarray:
    return CMP._media_janela(m.astype(np.float64), r) > 0.001


def lab(img) -> np.ndarray:
    rgb = np.asarray(img.convert("RGB")) if isinstance(img, Image.Image) else np.asarray(img)[..., :3]
    return CMP.rgb_para_lab(rgb)


def _anel_contra_miolo(L: np.ndarray, anel: np.ndarray, miolo: np.ndarray, r: int = 4) -> dict:
    cont = CMP._media_janela(miolo.astype(np.float64), r)
    medias = [CMP._media_janela(L[..., k] * miolo, r) / np.maximum(cont, 1e-9) for k in range(3)]
    ok = anel & (cont * (2 * r + 1) ** 2 >= 8)
    if not ok.any():
        return {"dE": None, "dL": None}
    d = np.stack([L[..., k][ok] - medias[k][ok] for k in range(3)], -1)
    return {"dE": round(float(np.sqrt((d ** 2).sum(-1)).mean()), 2), "dL": round(float(d[:, 0].mean()), 2)}


def _ilhas(alfa: np.ndarray) -> int:
    rot, n = ndimage.label(alfa > 8)
    if n <= 1:
        return 0
    return int((np.bincount(rot.ravel())[1:] < 50).sum())


def _faixa(m: np.ndarray, excluir: np.ndarray | None, de: float, ate: float, fora: bool) -> np.ndarray:
    dist = ndimage.distance_transform_edt(~m if fora else m)
    f = (dist > de) & (dist <= ate)
    return f & ~excluir if excluir is not None else f


def _media(L: np.ndarray, f: np.ndarray) -> float | None:
    return round(float(L[f].mean()), 1) if f.any() else None


# ---------------------------------------------------------------- as três réguas


def recorte(Lf: np.ndarray, Ls: np.ndarray, Lr: np.ndarray, rgba_tela: np.ndarray, rgba: np.ndarray,
            x: int, y: int, acima: np.ndarray, alvo: np.ndarray) -> dict:
    """Franja, névoa, ilhas e corte reto de uma parte (Lf peça, Ls peça sem a parte, Lr referência, em Lab)."""
    H, W = acima.shape
    alfa = rgba_tela[..., 3]
    dentro = alfa > 128
    longe = ~crescer(acima, 2)
    anel = dentro & ~comer(dentro, 2) & longe
    miolo = comer(dentro, 3) & ~comer(dentro, 7) & ~acima
    peca = _anel_contra_miolo(Lf, anel, miolo)
    junto = alvo & dentro
    alinhada = alvo.any() and junto.sum() >= 0.8 * (alvo | dentro).sum()
    if alinhada:
        ref = _anel_contra_miolo(Lr, anel, miolo)
        faixa = crescer(dentro, 2) & ~comer(dentro, 2) & longe
        de_borda = round(float(CMP.de2000(Lf[faixa], Lr[faixa]).mean()), 2) if faixa.any() else None
    else:
        ref = _anel_contra_miolo(Lr, alvo & ~comer(alvo, 2), comer(alvo, 3) & ~comer(alvo, 7)) if alvo.any() \
            else {"dE": None}
        de_borda = None
    fora = (crescer(dentro, 4) | (alfa > 0)) & ~dentro & longe
    contorno = max(1, int((dentro & ~comer(dentro, 1) & longe).sum()))
    d = Lf[fora] - Ls[fora]
    beira = ((dentro & ~comer(dentro, 1)) | (crescer(dentro, 1) & ~dentro)) & longe
    return {
        "franja": round(float(d[:, 0].sum()) / contorno, 2),
        "halo_fora": round(float(np.sqrt((d ** 2).sum(-1)).sum()) / contorno, 2),
        "anel": peca["dE"], "anel_ref": ref["dE"],
        "semi_%": round(100 * float(((alfa > 8) & (alfa <= 128)).sum()) / max(1, int(dentro.sum())), 2),
        "ilhas": _ilhas(alfa),
        "borda_suave_%": round(100 * float(((alfa > 8) & (alfa < 247))[beira].mean()), 1) if beira.any() else None,
        "borda_opaca": round(CMP.borda_opaca(rgba, x, y, W, H), 3),
        "quadro_%": round(100 * float(dentro.mean()), 1),
        "dE_borda": de_borda,
    }


def contorno(L: np.ndarray, m: np.ndarray, excluir: np.ndarray | None = None) -> dict:
    """Brilho em volta, luz de contorno e de que lado vem a luz (L* de 0 a 100)."""
    if not m.any():
        return {"brilho_fora": None, "luz_borda": None, "lados": None}
    L = L[..., 0]
    f0 = _media(L, _faixa(m, excluir, 0, 15, fora=True))
    f1 = _media(L, _faixa(m, excluir, 30, 60, fora=True))
    d0 = _faixa(m, excluir, 0, 8, fora=False)
    d1 = _media(L, _faixa(m, excluir, 15, 40, fora=False))
    ys, xs = np.nonzero(m)
    cx, cy, w, h = xs.mean(), ys.mean(), xs.max() - xs.min(), ys.max() - ys.min()
    yy, xx = np.mgrid[: m.shape[0], : m.shape[1]]
    lados = {"esquerda": _media(L, d0 & (xx < cx - 0.15 * w)), "direita": _media(L, d0 & (xx > cx + 0.15 * w)),
             "cima": _media(L, d0 & (yy < cy - 0.25 * h))}
    borda = _media(L, d0)
    return {"brilho_fora": round(f0 - f1, 1) if f0 is not None and f1 is not None else None,
            "luz_borda": round(borda - d1, 1) if borda is not None and d1 is not None else None,
            "lados": lados}


def estouro(antes: np.ndarray, depois: np.ndarray) -> dict:
    """Quanto da borda e do miolo da camada ficou mais claro que o máximo local de antes (RGBA na tela)."""
    m = (antes[..., 3] > 128) & (depois[..., 3] > 128)
    L_antes, L_depois = lab(antes)[..., 0], lab(depois)[..., 0]
    sobra = L_depois - ndimage.maximum_filter(np.where(m, L_antes, 0), size=5)
    faixa = m & ~ndimage.binary_erosion(m, iterations=3)
    miolo = ndimage.binary_erosion(m, iterations=4)
    return {"borda_%": round(100 * float((sobra[faixa] > 6).mean()), 2) if faixa.any() else None,
            "dentro_%": round(100 * float((sobra[miolo] > 6).mean()), 2) if miolo.any() else None}


# ---------------------------------------------------------------- por peça


def partes_recortadas(grafo: dict, camadas: dict) -> list[str]:
    """As partes geradas que têm contorno (a cena enche o quadro e não entra)."""
    return [c for c in G.camadas_geradas(grafo) if c != "cena" and c in camadas]


def medir(grafo: dict, tipos: dict[str, str], camadas: dict, final: Image.Image, sem: dict[str, Image.Image],
          sem_estilo: dict[str, Image.Image], acima_de) -> dict:
    """Recorte e contorno de cada parte recortada.

    `sem[parte]` é a peça com a parte escondida; `sem_estilo[parte]`, com a parte sem os estilos
    (só para partes que têm estilo); `acima_de(parte)` -> (cobertas na peça, na referência).
    """
    W, H = grafo["tamanho_px"]
    Lf = lab(final.convert("RGB").resize((W, H)))
    Lr = lab(Image.open(G.RAIZ / grafo["referencia"]).convert("RGB").resize((W, H)))
    saida = {}
    for parte in partes_recortadas(grafo, camadas):
        rgba, x, y = camadas[parte]
        tela = CMP.na_tela(rgba, x, y, W, H)
        acima_peca, acima_ref = acima_de(parte)
        alvo = G.mascara_camada(grafo, parte)
        r = {}
        if parte in sem:
            Ls = lab(sem[parte].convert("RGB").resize((W, H)))
            Lp = lab(sem_estilo[parte].convert("RGB").resize((W, H))) if parte in sem_estilo else Lf
            r["recorte"] = recorte(Lp, Ls, Lr, tela, rgba, x, y, acima_peca, alvo)
        r["contorno"] = {"peca": contorno(Lf, tela[..., 3] > 128, acima_peca),
                         "referencia": contorno(Lr, alvo, acima_ref)}
        saida[parte] = r
    return saida


def diagnostico(bordas: dict) -> list[tuple[float, str]]:
    """Frases dos problemas de borda, com um peso para ordenar junto com as do perfil."""
    achados = []
    for parte, b in bordas.items():
        r = b.get("recorte") or {}
        if r.get("quadro_%") is not None and r["quadro_%"] >= 90:
            achados.append((9.0, f"{parte}: cobre {r['quadro_%']:.0f}% da peça: o fundo da imagem gerada veio junto "
                                 "(recorte)"))
        if r.get("franja") is not None and abs(r["franja"]) > 3:
            cor = "escura" if r["franja"] < 0 else "clara"
            achados.append((abs(r["franja"]) / 10, f"{parte}: franja {cor} em volta do recorte "
                                                   f"(franja {r['franja']:+.1f}; bom até ±3) (recorte)"))
        if r.get("semi_%") is not None and r["semi_%"] > 3:
            achados.append((r["semi_%"] / 10, f"{parte}: névoa meio transparente na borda "
                                              f"({r['semi_%']:.1f}% da parte; bom até 3%) (recorte)"))
        if r.get("ilhas") is not None and r["ilhas"] > 5:
            achados.append((r["ilhas"] / 50, f"{parte}: {r['ilhas']} pedacinhos soltos em volta (bom até 5) (recorte)"))
        if r.get("borda_opaca") is not None and r["borda_opaca"] > 0.05:
            achados.append((r["borda_opaca"] * 2, f"{parte}: cortada reta na borda da imagem gerada "
                                                  f"({r['borda_opaca']:.0%} da moldura opaca) (recorte)"))
        c = b.get("contorno") or {}
        p, ref = c.get("peca") or {}, c.get("referencia") or {}
        for chave, (mais, menos) in {"brilho_fora": ("mais brilho em volta", "menos brilho em volta"),
                                     "luz_borda": ("mais luz de contorno", "menos luz de contorno")}.items():
            a, rr = p.get(chave), ref.get(chave)
            if a is None or rr is None or abs(a - rr) <= 3:
                continue
            achados.append((abs(a - rr) / 30, f"{parte}: {mais if a > rr else menos} que a referência "
                                              f"({chave} {a:+.1f} x {rr:+.1f}) (luz)"))
        e = b.get("estouro") or {}
        if (e.get("borda_%") or 0) > 1 or (e.get("dentro_%") or 0) > 3:
            achados.append((max(e.get("borda_%") or 0, e.get("dentro_%") or 0) / 10,
                            f"{parte}: a nitidez estourou: contorno claro em {e.get('borda_%')}% da borda e "
                            f"{e.get('dentro_%')}% do miolo (bom até 1% e 3%) (retoque)"))
    return achados
