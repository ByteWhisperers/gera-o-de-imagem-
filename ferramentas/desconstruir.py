"""Desconstrói uma referência: a peça inteira, as partes isoladas e o grafo das relações.

Uso:
    python ferramentas/desconstruir.py fichas/arara/grafos/promo-telegram.marcacao.yaml
    python ferramentas/desconstruir.py fichas/arara/grafos/promo-telegram.marcacao.yaml --placas

É semi-manual. O agente escreve a marcação (contornos aproximados do mascote
e dos objetos, e as relações que lê na peça). Esta ferramenta:
  1. encaixa cada contorno na borda real da imagem (random walker numa faixa
     em volta do contorno: dentro é parte, fora é fundo, a faixa se decide);
  2. mede sozinha o logo (casamento com o arquivo do logo), as linhas de
     texto (cor, altura, contorno, contraste) e o fundo (paleta, escurecimento);
  3. escreve o grafo <peca>.json, as máscaras, os recortes isolados e uma
     prancha de conferência para o dono aprovar;
  4. com --placas, apaga texto e logo (placa "sem_texto") e também mascote e
     entorno (placa "cena_limpa") por inpainting no ComfyUI local. Custo zero.

Precisa de scikit-image (requirements-desconstrucao.txt).

A marcação (YAML), em frações da largura e da altura:
  peca, referencia, ficha, formato, tema
  zona_texto, zona_logo   onde procurar o texto e o logo
  nos                     id -> tipo, z, camada_psd, descricao e UM destes:
                            contorno: [[x, y], ...]   polígono a olho (a ferramenta encaixa na borda)
                            elipses: [[x, y, w, h]]   uma ou várias (objeto_grupo conta quantas)
                            caixa: [x, y, w, h]        só posição, sem máscara (ex.: o que o mascote segura
                                                       quando já está dentro do contorno dele)
                          um nó tipo texto com caixa é um rótulo solto (ex.: "Nível 2"), fora do bloco
  arestas                 relações que se leem na peça (segura, apresenta, cerca, veste, tema_liga)
  texto_linhas            opcional: caixas [x, y, w, h] das linhas, quando a projeção erra
  logo_caixa              opcional: [x, y, w] do logo, quando o casamento com o arquivo erra
  observacoes             opcional: o que não cabe na ficha atual (vai para a próxima versão)
  estado, aprovacao       "proposta" até o dono aprovar o recorte; então "aprovada" + quem e quando

Uma camada_psd que a ficha ainda não tem (ex.: "frente", folhagem na frente
do mascote) é recortada e entra no grafo, mas fica embutida no fundo (a placa
cena_limpa não a apaga) até uma versão da ficha incluí-la.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from ferramentas.medir import luminancia, paleta  # noqa: E402
from motor import ficha as F  # noqa: E402
from motor import grafo as G  # noqa: E402


def _ndi():
    from scipy import ndimage

    return ndimage


# ---------------------------------------------------------------- contornos


def mascara_poligono(pontos: list, largura: int, altura: int) -> np.ndarray:
    m = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(m).polygon([(x * largura, y * altura) for x, y in pontos], fill=255)
    return np.asarray(m) > 127


def mascara_elipse(caixa: list, largura: int, altura: int) -> np.ndarray:
    x, y, w, h = caixa
    m = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(m).ellipse((x * largura, y * altura, (x + w) * largura, (y + h) * altura), fill=255)
    return np.asarray(m) > 127


def encaixar_na_borda(rgb: np.ndarray, aproximada: np.ndarray, banda: int | None = None) -> np.ndarray:
    """Ajusta uma máscara aproximada à borda real da imagem.

    Dentro do contorno (encolhido) é certeza de parte; fora (alargado) é certeza
    de fundo; a faixa entre os dois o random walker decide pela cor.
    """
    from skimage.segmentation import random_walker

    warnings.filterwarnings("ignore", message="The probability range is outside")
    ndi = _ndi()
    caixa = G.caixa_px(aproximada)
    if caixa is None:
        return aproximada
    _, _, bw, bh = caixa
    banda = banda or max(5, round(0.03 * min(bw, bh)))
    dentro = ndi.binary_erosion(aproximada, iterations=banda)
    fora = ~ndi.binary_dilation(aproximada, iterations=banda)
    x, y, w, h = G.caixa_px(~fora)
    passo = 2 if min(w, h) > 400 else 1
    sub = rgb[y : y + h : passo, x : x + w : passo] / 255.0
    sementes = np.zeros(sub.shape[:2], np.int32)
    sementes[dentro[y : y + h : passo, x : x + w : passo]] = 1
    sementes[fora[y : y + h : passo, x : x + w : passo]] = 2
    if not (sementes == 1).any():
        return aproximada
    rotulo = random_walker(sub, sementes, beta=130, mode="cg_j", channel_axis=-1, tol=1e-2)
    parte = Image.fromarray(((rotulo == 1) * 255).astype(np.uint8))
    if passo > 1:
        parte = parte.resize((w, h), Image.BILINEAR)
    saida = np.zeros_like(aproximada)
    saida[y : y + h, x : x + w] = np.asarray(parte)[:h, :w] > 127
    return ndi.binary_fill_holes(saida)


# ---------------------------------------------------------------- medidas automáticas


def medir_logo(im: Image.Image, arquivo_logo: Path, zona: list) -> dict:
    """Acha o logo na peça casando com o arquivo do logo, em várias escalas."""
    from skimage.feature import match_template

    W, H = im.size
    esc = 4
    logo = Image.open(arquivo_logo).convert("RGBA")
    zx, zy, zw, zh = zona
    cinza = np.asarray(im.convert("L").resize((W // esc, H // esc)), dtype=np.float32)
    x0, y0 = int(zx * W / esc), int(zy * H / esc)
    area = cinza[y0 : int((zy + zh) * H / esc), x0 : int((zx + zw) * W / esc)]
    melhor = None
    for frac in np.arange(0.10, zw, 0.005):
        lw = int(W * frac / esc)
        lh = int(lw * logo.height / logo.width)
        if lw < 8 or lh >= area.shape[0] or lw >= area.shape[1]:
            continue
        lg = logo.resize((lw, lh))
        a = np.asarray(lg.getchannel("A"), dtype=np.float32) / 255
        molde = np.asarray(lg.convert("L"), dtype=np.float32) * a
        r = match_template(area, molde)
        k = np.unravel_index(np.argmax(r), r.shape)
        if melhor is None or r[k] > melhor[0]:
            melhor = (float(r[k]), k, lw, lh)
    nota, (ly, lx), lw, lh = melhor
    x, y, w, h = (lx + x0) * esc, (ly + y0) * esc, lw * esc, lh * esc
    alfa = np.asarray(logo.resize((w, h)).getchannel("A")) > 127
    m = np.zeros((H, W), bool)
    m[y : y + h, x : x + w] = alfa[: max(0, min(h, H - y)), : max(0, min(w, W - x))]
    return {"mascara": m, "correlacao": round(nota, 3)}


def logo_na_caixa(im: Image.Image, arquivo_logo: Path, caixa: list) -> dict:
    """Logo posto onde o agente marcou ([x, y, w] em frações; a altura sai da proporção do arquivo)."""
    W, H = im.size
    logo = Image.open(arquivo_logo).convert("RGBA")
    x, y, w = round(caixa[0] * W), round(caixa[1] * H), round(caixa[2] * W)
    h = round(w * logo.height / logo.width)
    alfa = np.asarray(logo.resize((w, h)).getchannel("A")) > 127
    m = np.zeros((H, W), bool)
    m[y : y + h, x : x + w] = alfa[: max(0, min(h, H - y)), : max(0, min(w, W - x))]
    return {"mascara": m, "correlacao": None}


def _l_rel(c: np.ndarray) -> float:
    c = np.asarray(c, dtype=np.float64) / 255
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def _cores_de_letra(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lum = luminancia(rgb)
    sat = (rgb.max(2) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    ouro = (rgb[..., 0] > 200) & (rgb[..., 1] > 150) & (rgb[..., 2] < 120)
    branco = (lum > 215) & (sat < 0.12)
    return lum, sat, ouro, branco


def _linhas_por_projecao(cand: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Linhas (x0, y0, x1, y1) achadas pela projeção das letras nas linhas da imagem."""
    ndi = _ndi()
    W = cand.shape[1]
    lab, n = ndi.label(cand.mean(1) > 0.04)
    saida = []
    for j in range(1, n + 1):
        ys = np.nonzero(lab == j)[0]
        if len(ys) < 20:
            continue
        y0, y1 = int(ys[0]), int(ys[-1]) + 1
        dens = cand[y0:y1].mean(0)
        cols = np.nonzero(dens > 0.05)[0]
        if len(cols) == 0:
            continue
        fim = cols[0]
        for c in cols[1:]:                       # para no primeiro vão maior que um espaço entre palavras
            if c - fim > 0.035 * W:
                break
            fim = c
        saida.append((int(cols[0]), y0, int(fim) + 1, y1))
    return saida


def _linhas_das_caixas(cand: np.ndarray, caixas: list) -> list[tuple[int, int, int, int]]:
    """Linhas a partir das caixas que o agente marcou, apertadas nas letras que estão dentro."""
    H, W = cand.shape
    saida = []
    for x, y, w, h in caixas:
        x0, y0 = max(0, int(x * W)), max(0, int(y * H))
        x1, y1 = min(W, int(round((x + w) * W))), min(H, int(round((y + h) * H)))
        dentro = np.zeros((H, W), bool)
        dentro[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
        c = G.caixa_px(dentro)
        if c is not None:
            saida.append((c[0], c[1], c[0] + c[2], c[1] + c[3]))
    return saida


def completar_letras(rgb: np.ndarray, glifo: np.ndarray, caixa: tuple[int, int, int, int]) -> np.ndarray:
    """A letra inteira, inclusive o miolo e a parte escura da rampa de cor.

    O limiar de cor só pega as partes claras perto do contorno: o miolo das
    letras grandes e a base cinza das brancas ficam de fora. Dois jeitos de
    achar o resto, dentro de uma caixa um pouco maior que a linha:
      1. a região clara (L >= 70) cercada pelo contorno escuro: pedaços claros
         que não encostam na borda da caixa e que o limiar já toca em boa parte
         (contorno furado vaza para o fundo, encosta na borda e fica de fora);
      2. o miolo que o anel do limiar fecha (preencher buracos), quando a cor
         do miolo é de letra (branco a cinza, ou ouro a laranja). O miolo do O,
         do A e do R é fundo e não tem cor de letra: continua vazado.
    """
    ndi = _ndi()
    H, W = glifo.shape
    x, y, w, h = caixa
    m = round(0.15 * h) + 2
    x0, y0, x1, y1 = max(0, x - m), max(0, y - m), min(W, x + w + m), min(H, y + h + m)
    px = rgb[y0:y1, x0:x1]
    lum = luminancia(px)
    g = glifo[y0:y1, x0:x1]
    saida = glifo.copy()
    rot, n = ndi.label(lum >= 70)
    if n:
        idx = np.arange(1, n + 1)
        area = ndi.sum(np.ones_like(g), rot, idx)
        cobre = ndi.sum(g, rot, idx)
        na_borda = set(np.unique(np.concatenate([rot[0], rot[-1], rot[:, 0], rot[:, -1]]))) - {0}
        bons = [i for i, a, c in zip(idx, area, cobre) if c / max(a, 1) > 0.1 and i not in na_borda]
        saida[y0:y1, x0:x1] |= np.isin(rot, bons)
    sat = (px.max(2) - px.min(2)) / np.maximum(px.max(2), 1)
    cor_de_letra = ((sat < 0.2) & (lum > 120)) | ((px[..., 0] > 150) & (px[..., 2] < 110) & (px[..., 0] >= px[..., 1]))
    fechado = ndi.binary_closing(g, iterations=2)
    miolo = ndi.binary_fill_holes(fechado) & ~g
    rot, n = ndi.label(miolo)
    if n:
        idx = np.arange(1, n + 1)
        frac = ndi.mean(cor_de_letra, rot, idx)
        saida[y0:y1, x0:x1] |= np.isin(rot, idx[np.asarray(frac) > 0.6])
    # 3. o que tem cor de letra e se liga ao limiar sem atravessar o contorno escuro,
    #    só dentro da caixa justa da linha (o vazamento, se houver, fica preso nela)
    dentro = np.zeros_like(g)
    dentro[y - y0 : y - y0 + h, x - x0 : x - x0 + w] = True
    pode = cor_de_letra & ~ndi.binary_dilation(lum < 60, iterations=1) & dentro
    saida[y0:y1, x0:x1] |= ndi.binary_propagation(g & pode, mask=pode)
    return saida


def medir_texto(rgb: np.ndarray, zona: list, proibido: np.ndarray,
                caixas_linhas: list | None = None) -> tuple[np.ndarray, list[dict]]:
    """Linhas de texto da zona: letras claras (branco ou ouro) coladas num contorno escuro.

    Devolve a máscara das letras e, por linha, caixa, altura, estilo, rampa de
    cor, contorno e contraste com o fundo em volta. O conteúdo não é copiado.
    Com `caixas_linhas` (frações, marcadas pelo agente quando a projeção falha),
    cada caixa vira uma linha, apertada nas letras que estão dentro dela.
    """
    ndi = _ndi()
    H, W = rgb.shape[:2]
    lum, _, ouro, branco = _cores_de_letra(rgb)
    zx, zy, zw, zh = zona
    dentro_zona = np.zeros((H, W), bool)
    dentro_zona[int(zy * H) : int((zy + zh) * H), int(zx * W) : int((zx + zw) * W)] = True
    cand = (branco | ouro) & dentro_zona & ~proibido
    borda_escura = ndi.binary_dilation(lum < 60, iterations=4)
    cand &= borda_escura | ndi.binary_dilation(cand & borda_escura, iterations=6)
    cand = ndi.binary_opening(cand, iterations=1)
    spans = _linhas_das_caixas(cand, caixas_linhas) if caixas_linhas else _linhas_por_projecao(cand)
    linhas, letras = [], np.zeros((H, W), bool)
    for x0, y0, x1, y1 in sorted(spans, key=lambda s: s[1]):
        caixa = np.zeros((H, W), bool)
        caixa[y0:y1, x0:x1] = True
        limiar = cand & caixa
        glifo = completar_letras(rgb, limiar, (x0, y0, x1 - x0, y1 - y0)) & ~proibido
        inteira = glifo[y0:y1, x0:x1]
        tercos = []                                    # rampa de cor da letra inteira, de cima para baixo
        for a, b in ((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1)):
            sel = inteira[int(a * (y1 - y0)) : int(b * (y1 - y0))]
            c = np.median(rgb[y0:y1, x0:x1][int(a * (y1 - y0)) : int(b * (y1 - y0))][sel], axis=0) \
                if sel.any() else np.zeros(3)
            tercos.append("#%02x%02x%02x" % tuple(int(round(v)) for v in c))
        cols = limiar[y0:y1, x0:x1]                    # colunas com letra: quanto da linha é dourado
        com_letra = cols.any(0)
        dourada = (cols & ouro[y0:y1, x0:x1]).sum(0) > 0.5 * cols.sum(0)
        acima = np.zeros((H, W), bool)                 # acentos ficam acima da linha
        acima[max(0, y0 - round(0.45 * (y1 - y0))) : y0, x0:x1] = True
        anel = ndi.binary_dilation(caixa, iterations=25) & ~ndi.binary_dilation(cand | glifo, iterations=12) \
            & ~proibido
        lt, lf = _l_rel(rgb[glifo].mean(0)), _l_rel(rgb[anel].mean(0))
        faixa = ndi.binary_dilation(glifo, iterations=6) & ~glifo
        linhas.append({
            "caixa_px": [x0, y0, x1 - x0, y1 - y0],
            "altura_px": y1 - y0,
            "estilo_ficha": "dourado" if ouro[limiar].mean() > 0.5 else "branco",
            "fracao_dourada": round(float((com_letra & dourada).sum() / max(1, com_letra.sum())), 2),
            "rampa_tercos": tercos,
            "contorno_escuro_frac": round(float((lum[faixa] < 50).mean()), 2),
            "contraste_wcag": round((max(lt, lf) + 0.05) / (min(lt, lf) + 0.05), 1),
            "L_fundo_em_volta": round(float(lum[anel].mean()), 1),
        })
        letras |= glifo | (cand & acima)
    if linhas:
        for li in linhas:
            li["peso_rel"] = round(li["altura_px"] / linhas[0]["altura_px"], 2)
    return letras, linhas


def medir_rotulo(rgb: np.ndarray, caixa: list, proibido: np.ndarray) -> tuple[np.ndarray, dict]:
    """Letras de um rótulo solto (ex.: "Nível 2" numa plaquinha) dentro da caixa do agente.

    Sem exigir contorno escuro: rótulo costuma ser letra clara sobre uma placa lisa.
    """
    ndi = _ndi()
    H, W = rgb.shape[:2]
    lum, sat, ouro, _ = _cores_de_letra(rgb)
    x, y, w, h = caixa
    x0, y0, x1, y1 = int(x * W), int(y * H), int(round((x + w) * W)), int(round((y + h) * H))
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = True
    g = (((lum > 190) & (sat < 0.25)) | ouro) & m & ~proibido
    g = ndi.binary_opening(g, iterations=1)
    c = G.caixa_px(g)
    info = {"altura_px": c[3] if c else 0,
            "estilo_ficha": "dourado" if g.any() and ouro[g].mean() > 0.5 else "branco"}
    return g, info


def curva_escurecimento(lum: np.ndarray, fundo: np.ndarray, faixas: int = 10) -> list:
    W = lum.shape[1]
    curva = []
    for k in range(faixas):
        a, b = int(W * k / faixas), int(W * (k + 1) / faixas)
        sel = fundo[:, a:b]
        curva.append(round(float(np.median(lum[:, a:b][sel])), 1) if sel.any() else None)
    return curva


def paleta_de(rgb: np.ndarray, m: np.ndarray, n: int = 6) -> list[dict]:
    amostra = rgb[m].astype(np.uint8)
    if len(amostra) == 0:
        return []
    passo = max(1, len(amostra) // 65536)
    amostra = amostra[::passo]
    lado = int(np.sqrt(len(amostra)))
    return paleta(Image.fromarray(amostra[: lado * lado].reshape(lado, lado, 3)), n)


# ---------------------------------------------------------------- arquivos


def _salvar_mascara(m: np.ndarray, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((m * 255).astype(np.uint8)).save(caminho, optimize=True)


def recorte_isolado(im: Image.Image, m: np.ndarray) -> Image.Image | None:
    caixa = G.caixa_px(m)
    if caixa is None:
        return None
    x, y, w, h = caixa
    rgba = im.convert("RGBA")
    rgba.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    return rgba.crop((x, y, x + w, y + h))


def _xadrez(w: int, h: int, lado: int = 16) -> Image.Image:
    yy, xx = np.mgrid[0:h, 0:w]
    v = np.where(((xx // lado) + (yy // lado)) % 2 == 0, 70, 95).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v]), "RGB").convert("RGBA")


CORES = {"mascote": (255, 60, 60), "entorno": (255, 170, 0), "texto": (80, 255, 80), "logo": (0, 220, 255),
         "frente": (255, 0, 255)}
CORES_EXTRAS = [(255, 255, 255), (160, 120, 255), (120, 255, 200), (255, 140, 180)]


def cor_da_camada(nome: str, ordem: int = 0) -> tuple[int, int, int]:
    return CORES.get(nome, CORES_EXTRAS[ordem % len(CORES_EXTRAS)])


def prancha(im: Image.Image, mascaras: dict[str, np.ndarray], recortes: dict[str, Image.Image],
            placas: dict[str, Image.Image]) -> Image.Image:
    """Referência com os contornos encaixados em cima e as partes isoladas embaixo."""
    from motor.comparar import _fonte

    ndi = _ndi()
    W, H = im.size
    topo = np.asarray(im.convert("RGB")).copy()
    for i, (nome, m) in enumerate(mascaras.items()):
        borda = ndi.binary_dilation(m, iterations=3) & ~m
        topo[borda] = cor_da_camada(nome, i)
    largura = 1600
    escala = largura / W
    blocos = [Image.fromarray(topo).resize((largura, round(H * escala)))]
    pecas = [(k, v) for k, v in placas.items()] + [(k, v) for k, v in recortes.items()]
    if pecas:
        alt, vao = 300, 14
        miniaturas = []
        for nome, p in pecas:
            p = p.convert("RGBA")
            f = min((alt - 10) / p.height, 520 / p.width)
            miniaturas.append((nome, p, f))
        total = sum(round(p.width * f) for _, p, f in miniaturas) + vao * (len(miniaturas) - 1)
        caber = min(1.0, (largura - 20) / total)        # tudo numa linha só: encolhe se não couber
        linha = Image.new("RGB", (largura, round(alt * caber) + 34), (24, 24, 24))
        d = ImageDraw.Draw(linha)
        fonte = _fonte(16)
        x = 10
        for nome, p, f in miniaturas:
            f *= caber
            p = p.resize((max(1, round(p.width * f)), max(1, round(p.height * f))))
            fundo = _xadrez(p.width, p.height)
            fundo.alpha_composite(p)
            linha.paste(fundo.convert("RGB"), (x, 28))
            d.text((x, 6), nome, font=fonte, fill=cor_da_camada(nome) if nome in CORES else (240, 240, 240))
            x += p.width + vao
        blocos.append(linha)
    total = Image.new("RGB", (largura, sum(b.height for b in blocos)), (24, 24, 24))
    y = 0
    for b in blocos:
        total.paste(b, (0, y))
        y += b.height
    return total


# ---------------------------------------------------------------- placas (inpainting no ComfyUI)


def preencher_buraco(rgb: np.ndarray, buraco: np.ndarray, reducao: int = 4) -> np.ndarray:
    """Pré-preenche o buraco com as cores de volta (convolução normalizada).

    O inpainting do SD-Turbo sai melhor partindo de cores plausíveis do que de um buraco.
    """
    ndi = _ndi()
    H, W = buraco.shape
    peq = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((W // reducao, H // reducao)), np.float32)
    conhecido = np.asarray(Image.fromarray(((~buraco) * 255).astype(np.uint8)).resize(
        (W // reducao, H // reducao), Image.NEAREST)) > 127
    conhecido = ndi.binary_erosion(conhecido, iterations=1)
    acc, peso = peq * conhecido[..., None], conhecido.astype(np.float32)
    cheio = np.where(conhecido[..., None], peq, 0)
    feito = conhecido.copy()
    for sigma in (2, 4, 8, 16, 32, 64, 128):
        num = np.stack([ndi.gaussian_filter(acc[..., c], sigma) for c in range(3)], -1)
        den = ndi.gaussian_filter(peso, sigma)
        novo = ~feito & (den > 1e-3)
        cheio[novo] = (num / np.maximum(den, 1e-6)[..., None])[novo]
        feito |= novo
    grande = np.asarray(Image.fromarray(cheio.clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32)
    return np.where(buraco[..., None], grande, rgb)


def buracos(grafo: dict, mascaras: dict[str, np.ndarray], linhas: list[dict],
            partes: set | None = None) -> dict[str, np.ndarray]:
    """Onde apagar: texto e logo (sem_texto); e também as figuras que a IA refaz (cena_limpa).

    Camada que a ficha ainda não conhece (fora de `partes`) fica embutida no fundo:
    não é apagada, e a folga das outras não come a borda dela.
    """
    ndi = _ndi()
    W, H = grafo["tamanho_px"]
    # as letras com folga para o contorno escuro e a sombra (cerca de 20% da altura da linha)
    folga = round(0.2 * np.mean([li["altura_px"] for li in linhas])) if linhas else 0
    texto = ndi.binary_dilation(mascaras["texto"], iterations=folga) if folga else mascaras["texto"]
    sem_texto = texto | ndi.binary_dilation(mascaras["logo"], iterations=10)
    figuras = [k for k in mascaras if k not in ("texto", "logo", "cena")]
    refeitas = [k for k in figuras if partes is None or k in partes]
    figura = np.zeros((H, W), bool)
    for k in refeitas:
        figura |= mascaras[k]
    figura = ndi.binary_dilation(figura, iterations=8)
    for k in figuras:
        if k not in refeitas:
            figura &= ~mascaras[k]
    return {"sem_texto": sem_texto, "cena_limpa": sem_texto | figura}


def fazer_placas(grafo: dict, ficha: dict, im: Image.Image, buracos_: dict[str, np.ndarray],
                 semente: int = 7) -> dict[str, Image.Image]:
    from motor import comfyui as CU
    from motor import compilador as C

    cfg = C.ler_config()
    rgb = np.asarray(im.convert("RGB"), np.float32)
    saida = {}
    for nome, buraco in buracos_.items():
        cheio = preencher_buraco(rgb, buraco)
        suave = Image.fromarray((buraco * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(
            ImageFilter.GaussianBlur(3))
        comp = C.compilar_placa(ficha, grafo, cfg, Image.fromarray(cheio.astype(np.uint8)), suave,
                                semente=semente, prefixo=f"gera/{grafo['peca']}-{nome}")
        for arq, imagem in comp.entradas.items():
            CU.enviar_imagem(cfg["url"], arq, imagem)
        resultado = CU.executar(cfg["url"], comp.workflow)
        saida[nome] = resultado[comp.saidas["placa"]["no"]][0].convert("RGB")
        print(f"placa {nome}: pronta")
    return saida


# ---------------------------------------------------------------- principal


def desconstruir(caminho_marcacao: str | Path, com_placas: bool = False) -> dict:
    ndi = _ndi()
    caminho_marcacao = Path(caminho_marcacao).resolve()
    mc = yaml.safe_load(caminho_marcacao.read_text(encoding="utf-8"))
    ficha = F.carregar(RAIZ / mc["ficha"])
    im = Image.open(RAIZ / mc["referencia"]).convert("RGB")
    W, H = im.size
    rgb = np.asarray(im, dtype=np.float32)
    lum = luminancia(rgb)
    destino = caminho_marcacao.parent / mc["peca"]
    rel = destino.relative_to(RAIZ).as_posix()

    # logo e texto: medidos sozinhos (a marcação pode dar a caixa quando a medida falha)
    logo_arq = next(c["arquivo"] for c in ficha["camadas"] if c["tipo"] == "arquivo")
    if "logo_caixa" in mc:
        logo = logo_na_caixa(im, RAIZ / logo_arq, mc["logo_caixa"])
    else:
        logo = medir_logo(im, RAIZ / logo_arq, mc["zona_logo"])
    perto_do_logo = ndi.binary_dilation(logo["mascara"], iterations=6)
    letras, linhas = medir_texto(rgb, mc["zona_texto"], perto_do_logo, mc.get("texto_linhas"))
    rotulos: dict[str, tuple[np.ndarray, dict]] = {}
    for id_, n in mc["nos"].items():
        if n["tipo"] == "texto":
            rotulos[id_] = medir_rotulo(rgb, n["caixa"], perto_do_logo | letras)
            letras = letras | rotulos[id_][0]

    # contornos marcados: encaixados na borda
    mascaras_no: dict[str, np.ndarray] = {}
    for id_, n in mc["nos"].items():
        if n["tipo"] == "texto":
            continue
        if "contorno" in n:
            mascaras_no[id_] = encaixar_na_borda(rgb, mascara_poligono(n["contorno"], W, H))
        elif "elipses" in n:
            m = np.zeros((H, W), bool)
            for e in n["elipses"]:
                m |= encaixar_na_borda(rgb, mascara_elipse(e, W, H))
            mascaras_no[id_] = m
    # o que está na frente ganha a disputa pelos pixels
    ordem = sorted(mascaras_no, key=lambda k: mc["nos"][k].get("z", 0), reverse=True)
    ocupado = letras | logo["mascara"]
    for k in ordem:
        mascaras_no[k] &= ~ocupado
        ocupado |= mascaras_no[k]
    fundo = ~ocupado

    # camadas do PSD: as da marcação (mascote, entorno, e outras como "frente"), depois texto e logo
    camadas: dict[str, np.ndarray] = {}
    for k in sorted(mascaras_no, key=lambda k: mc["nos"][k].get("z", 0)):
        c = mc["nos"][k].get("camada_psd")
        if not c or c in ("cena", "texto", "logo"):
            raise ValueError(f"{caminho_marcacao.name}: o nó '{k}' tem contorno, então precisa de uma "
                             f"camada_psd própria (mascote, entorno, frente...), não '{c}'")
        camadas[c] = camadas.get(c, np.zeros((H, W), bool)) | mascaras_no[k]
    camadas["texto"], camadas["logo"] = letras, logo["mascara"]

    # nós do grafo
    nos: list[dict] = []
    for id_, n in mc["nos"].items():
        if n["tipo"] == "texto":
            continue                                   # rótulos entram depois das linhas de texto
        no = {"id": id_, "tipo": n["tipo"], "z": n.get("z", 0), "camada_psd": n.get("camada_psd")}
        no.update({k: v for k, v in n.items() if k in ("descricao", "figurino", "pose", "tema", "nota")})
        if id_ in mascaras_no:
            no["mascara"] = f"mascaras/{id_}.png"
            no["caixa"] = G.caixa_frac(G.caixa_px(mascaras_no[id_]), W, H)
            no["fonte_caixa"] = "medido:contorno do agente encaixado na borda (random walker)"
        elif "caixa" in n:
            no["caixa"] = n["caixa"]
            no["fonte_caixa"] = "estimativa do agente"
        if n["tipo"] == "fundo":
            no["mascara"] = "mascaras/cena.png"
            no["caixa"] = [0, 0, 1, 1]
            no["estilo"] = {"paleta": paleta_de(rgb, fundo), "fonte": "medido:só os pixels de fundo"}
        if "quantidade" in n:
            no["quantidade"] = n["quantidade"]
        elif n["tipo"] == "objeto_grupo" and "elipses" in n:
            no["quantidade"] = len(n["elipses"])
        nos.append(no)
    esc = ficha["escurecimento"]
    nos.append({"id": "escurecimento", "tipo": "efeito", "z": 1, "camada_psd": "escurecimento",
                "caixa": [0, 0, esc["fim_x"], 1], "na_referencia": "embutido no fundo",
                "estilo": {"L_fundo_por_decimo_de_W": curva_escurecimento(lum, fundo),
                           "fonte": "medido:mediana de L do fundo por faixa de 10% da largura"}})
    claros = (lum > 235) & (rgb[..., 2] < 200) & fundo
    rot, nb = ndi.label(claros)
    pequenos = int((ndi.sum(claros, rot, range(1, nb + 1)) < 40).sum()) if nb else 0
    nos.append({"id": "brilho", "tipo": "efeito", "z": 5, "camada_psd": "brilho", "na_referencia": "embutido no fundo",
                "estilo": {"pontos_claros_pequenos": pequenos, "fonte": "medido:L>235, <40 px (grosseiro)"}})
    for i, li in enumerate(linhas, start=1):
        m = np.zeros((H, W), bool)
        x, y, w, h = li["caixa_px"]
        m[y : y + h, x : x + w] = True
        mascaras_no[f"texto_l{i}"] = letras & m
        nos.append({"id": f"texto_l{i}", "tipo": "texto", "z": 6, "camada_psd": "texto",
                    "conteudo": "<não copiado: o texto sai de motor/texto.py>",
                    "mascara": f"mascaras/texto_l{i}.png", "caixa": G.caixa_frac(li["caixa_px"], W, H),
                    "estilo": {k: li[k] for k in ("estilo_ficha", "fracao_dourada", "altura_px", "peso_rel",
                                                  "rampa_tercos", "contorno_escuro_frac")},
                    "fonte": "medido:limiar de cor + " + ("caixas de linha do agente" if mc.get("texto_linhas")
                                                          else "projeção por linha")})
    for id_, (m, info) in rotulos.items():
        n = mc["nos"][id_]
        mascaras_no[id_] = m
        c = G.caixa_px(m)
        nos.append({"id": id_, "tipo": "texto", "papel": "rotulo", "z": n.get("z", 6), "camada_psd": "texto",
                    "conteudo": "<não copiado: o texto sai de motor/texto.py>", "mascara": f"mascaras/{id_}.png",
                    "caixa": G.caixa_frac(c, W, H) if c else n["caixa"],
                    **{k: v for k, v in n.items() if k in ("descricao", "nota")},
                    "estilo": info, "fonte": "medido:letras claras dentro da caixa do agente"})
    mascaras_no["logo"] = logo["mascara"]
    nos.append({"id": "logo", "tipo": "logo", "z": 7, "camada_psd": "logo", "arquivo": logo_arq,
                "mascara": "mascaras/logo.png", "caixa": G.caixa_frac(G.caixa_px(logo["mascara"]), W, H),
                "fonte_caixa": f"medido:casamento com o arquivo do logo, correlação {logo['correlacao']}"
                if logo["correlacao"] is not None else "estimativa do agente (logo_caixa)"})
    mascaras_no["cena"] = fundo

    # arestas: as lidas pelo agente + as medidas
    arestas = [dict(a) for a in mc.get("arestas", [])]
    ids = {n["id"] for n in nos}
    arestas = [a for a in arestas if a["de"] in ids and a["para"] in ids]
    for n in nos:
        if n["tipo"] in G.GERAVEIS and n["tipo"] != "fundo" and "mascara" in n:
            arestas.append({"de": n["id"], "rel": "fica_sobre", "para": "cena"})
    for i, li in enumerate(linhas, start=1):
        arestas.append({"de": f"texto_l{i}", "rel": "fica_sobre", "para": "escurecimento"})
        arestas.append({"de": f"texto_l{i}", "rel": "contraste", "para": "cena", "wcag": li["contraste_wcag"],
                        "L_fundo_em_volta": li["L_fundo_em_volta"]})
        if i < len(linhas):
            prox = linhas[i]
            vao = prox["caixa_px"][1] - (li["caixa_px"][1] + li["altura_px"])
            arestas.append({"de": f"texto_l{i}", "rel": "empilhado_acima", "para": f"texto_l{i + 1}",
                            "vao_rel_altura": round(vao / li["altura_px"], 2)})
    if linhas:
        lx = G.caixa_px(logo["mascara"])[0]
        arestas.append({"de": "texto_l1", "rel": "alinhado_com", "para": "logo", "eixo": "esquerda",
                        "delta_x": round((linhas[0]["caixa_px"][0] - lx) / W, 3)})

    # arquivos
    for k, m in mascaras_no.items():
        _salvar_mascara(m, destino / "mascaras" / f"{k}.png")
    recortes = {}
    (destino / "recortes").mkdir(parents=True, exist_ok=True)
    for nome in camadas:
        r = recorte_isolado(im, camadas[nome])
        if r is not None:
            r.save(destino / "recortes" / f"{nome}.webp", "WEBP", quality=92)
            recortes[nome] = r
    estado = mc.get("estado", "proposta")
    if estado not in ("proposta", "aprovada"):
        raise ValueError(f"{caminho_marcacao.name}: estado '{estado}' (use proposta ou aprovada)")
    grafo = {
        "formato": G.FORMATO, "estado": estado, "peca": mc["peca"], "marca": ficha["marca"],
        "ficha": mc["ficha"], "referencia": mc["referencia"], "formato_peca": mc["formato"], "tema": mc["tema"],
        "tamanho_px": [W, H], "pasta": rel, "marcacao": caminho_marcacao.relative_to(RAIZ).as_posix(),
        "convencao": "caixa = [x, y, w, h] em fração de W e H; z = ordem de baixo (0) para cima; "
                     "cada número diz de onde veio (medido:<método> ou estimativa)",
        "recortes": {k: f"recortes/{k}.webp" for k in recortes},
        "placas": {},
        "nos": nos, "arestas": arestas,
    }
    if "aprovacao" in mc:
        grafo["aprovacao"] = mc["aprovacao"]
    if mc.get("observacoes"):
        grafo["observacoes"] = mc["observacoes"]
    fora = [c for c in camadas if c not in ("texto", "logo") and c not in ficha["partes"]]
    if fora:
        grafo["camadas_fora_da_ficha"] = fora
    placas = {}
    for nome in ("sem_texto", "cena_limpa"):
        arq = destino / f"{nome.replace('_', '-')}.webp"
        if arq.exists():
            placas[nome] = Image.open(arq).convert("RGB")
    if com_placas:
        placas = fazer_placas(grafo, ficha, im, buracos(grafo, camadas, linhas, set(ficha["partes"])))
        for nome, p in placas.items():
            p.save(destino / f"{nome.replace('_', '-')}.webp", "WEBP", quality=94)
    grafo["placas"] = {nome: f"{nome.replace('_', '-')}.webp" for nome in placas}
    G.conferir(grafo, caminho_marcacao)
    saida = caminho_marcacao.parent / f"{mc['peca']}.json"
    saida.write_text(json.dumps(grafo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    vistas = {"cena limpa": placas["cena_limpa"]} if "cena_limpa" in placas else {}
    prancha(im, camadas, recortes, vistas).save(destino / "conferencia.jpg", quality=88)
    return {"grafo": saida, "estado": estado, "nos": len(nos), "arestas": len(arestas), "linhas_texto": len(linhas),
            "rotulos": len(rotulos), "logo_correlacao": logo["correlacao"], "camadas": list(camadas),
            "camadas_fora_da_ficha": fora, "placas": sorted(placas),
            "conferencia": (destino / "conferencia.jpg").relative_to(RAIZ).as_posix()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("marcacao")
    ap.add_argument("--placas", action="store_true", help="faz as placas sem texto e de fundo limpo no ComfyUI")
    a = ap.parse_args()
    r = desconstruir(a.marcacao, a.placas)
    print(json.dumps({k: (v.as_posix() if isinstance(v, Path) else v) for k, v in r.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
