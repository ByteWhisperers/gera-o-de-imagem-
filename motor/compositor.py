"""Monta as camadas na ordem da ficha e salva PSD (editável) e PNG/WebP (final).

O PSD é o contrato da composição: qualquer editor de camadas abre
(PhotoCraft, ArtCraft, Photopea, GIMP, Photoshop) e cada camada tem o nome
do id da ficha.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter

from . import ficha as F
from . import texto as T
from .recorte import recortar_conteudo, remover_fundo

RAIZ = Path(__file__).resolve().parent.parent


@dataclass
class Camada:
    nome: str
    imagem: Image.Image      # RGBA
    x: int = 0
    y: int = 0
    visivel: bool = True


def cobrir(im: Image.Image, largura: int, altura: int) -> Image.Image:
    """Redimensiona e corta ao centro para preencher largura x altura."""
    escala = max(largura / im.width, altura / im.height)
    nova = im.resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
    x, y = (nova.width - largura) // 2, (nova.height - altura) // 2
    return nova.crop((x, y, x + largura, y + altura))


def escurecimento(cfg: dict, largura: int, altura: int) -> Image.Image:
    r, g, b = ImageColor.getrgb(cfg["cor"])
    fim = max(1, int(largura * cfg["fim_x"]))
    alfa = np.zeros(largura, dtype=np.float32)
    t = np.linspace(0, 1, fim, dtype=np.float32)
    alfa[:fim] = cfg["opacidade_inicio"] * (1 - t) ** 1.5 * 255
    camada = np.zeros((altura, largura, 4), dtype=np.uint8)
    camada[..., 0], camada[..., 1], camada[..., 2] = r, g, b
    camada[..., 3] = alfa[None, :].astype(np.uint8)
    return Image.fromarray(camada, "RGBA")


def brilho(cfg: dict, largura: int, altura: int) -> Image.Image:
    rnd = random.Random(cfg.get("semente", 0))
    cor = ImageColor.getrgb(cfg["cor"])
    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    base = min(largura, altura)
    for _ in range(cfg["particulas"]):
        x, y = rnd.random() * largura, rnd.random() * altura
        r = base * rnd.uniform(0.002, 0.007)
        d.ellipse((x - r, y - r, x + r, y + r), fill=cor + (rnd.randint(120, 230),))
    halo = camada.filter(ImageFilter.GaussianBlur(base * 0.006))
    halo.alpha_composite(camada)
    return halo


def encaixar(im: Image.Image, caixa: dict, largura: int, altura: int) -> tuple[Image.Image, int, int]:
    """Coloca a parte na caixa da ficha, mantendo a proporção. Âncora 'base' encosta embaixo."""
    cx, cy = round(caixa["x"] * largura), round(caixa["y"] * altura)
    cw = round(caixa["w"] * largura)
    ch = round(caixa.get("h", 1.0) * altura) if "h" in caixa else None
    escala = cw / im.width if ch is None else min(cw / im.width, ch / im.height)
    nova = im.resize((max(1, round(im.width * escala)), max(1, round(im.height * escala))), Image.LANCZOS)
    x = cx + (cw - nova.width) // 2 if ch is not None else cx
    if caixa.get("ancora") == "base" and ch is not None:
        y = cy + ch - nova.height
    else:
        y = cy
    return nova, x, y


def montar(ficha: dict, formato: str, partes: dict[str, Image.Image], linhas: list[dict],
           recorte: dict[str, str] | None = None, posicionadas: dict[str, tuple] | None = None,
           ocultas: set[str] | None = None, vazias: set[str] | None = None) -> list[Camada]:
    """`recorte` diz o método de tirar o fundo de cada parte (padrão: liso).

    `posicionadas` traz partes que já chegam recortadas e no lugar certo, como
    (imagem RGBA, x, y): é o caso das partes refeitas a partir do grafo da
    referência. `ocultas` são camadas que entram no PSD desligadas (por exemplo,
    um efeito que já vem embutido no fundo da referência). `vazias` são camadas
    geradas que esta peça não tem (por exemplo, a frente numa referência sem nada
    na frente do mascote): entram no PSD vazias, para a ordem seguir a ficha.
    """
    largura, altura = F.tamanho(ficha, formato)
    layout = ficha["layout"][formato]
    posicionadas = posicionadas or {}
    camadas: list[Camada] = []
    for c in ficha["camadas"]:
        nome, tipo = c["id"], c["tipo"]
        if nome in posicionadas:
            im, x, y = posicionadas[nome]
            im = im.convert("RGBA")
            caixa = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, im.width, im.height)
            camadas.append(Camada(nome, im.crop(caixa), x + caixa[0], y + caixa[1]))
        elif nome in (vazias or set()):
            camadas.append(Camada(nome, Image.new("RGBA", (1, 1), (0, 0, 0, 0))))
        elif tipo == "gerada" and c["parte"] == "cena":
            camadas.append(Camada(nome, cobrir(partes["cena"], largura, altura).convert("RGBA")))
        elif tipo == "gerada":
            im = partes[c["parte"]]
            if ficha["partes"][c["parte"]].get("transparente") and im.mode != "RGBA":
                im = remover_fundo(im, (recorte or {}).get(c["parte"], "liso"))
            im, x, y = encaixar(recortar_conteudo(im.convert("RGBA")), layout[nome], largura, altura)
            camadas.append(Camada(nome, im, x, y))
        elif nome == "escurecimento":
            camadas.append(Camada(nome, escurecimento(ficha["escurecimento"], largura, altura)))
        elif nome == "brilho":
            camadas.append(Camada(nome, brilho(ficha["brilho"], largura, altura)))
        elif tipo == "texto":
            caixa = layout["texto"]
            w, h = round(caixa["w"] * largura), round(caixa["h"] * altura)
            im, folga = T.bloco(ficha, linhas, w, h)
            camadas.append(Camada(nome, im, round(caixa["x"] * largura) - folga, round(caixa["y"] * altura) - folga))
        elif tipo == "arquivo":
            logo = recortar_conteudo(Image.open(RAIZ / c["arquivo"]).convert("RGBA"))
            im, x, y = encaixar(logo, layout[nome], largura, altura)
            camadas.append(Camada(nome, im, x, y))
        else:
            raise ValueError(f"camada '{nome}' de tipo '{tipo}' não sei montar")
    for c in camadas:
        c.visivel = c.nome not in (ocultas or set())
    return camadas


def achatar(camadas: list[Camada], largura: int, altura: int) -> Image.Image:
    final = Image.new("RGBA", (largura, altura), (0, 0, 0, 255))
    for c in camadas:
        if not c.visivel:
            continue
        tela = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
        tela.paste(c.imagem, (c.x, c.y), c.imagem)
        final.alpha_composite(tela)
    return final


def salvar(camadas: list[Camada], largura: int, altura: int, base: Path) -> dict[str, Path]:
    """Grava <base>.psd, <base>.png e <base>.webp. Devolve os caminhos."""
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer

    base.parent.mkdir(parents=True, exist_ok=True)
    psd = PSDImage.new("RGBA", (largura, altura))
    for c in camadas:
        # recorta o que sai da tela: o PSD guarda só a parte visível de cada camada
        caixa = (max(0, -c.x), max(0, -c.y), min(c.imagem.width, largura - c.x), min(c.imagem.height, altura - c.y))
        visivel = c.imagem.crop(caixa)
        camada = PixelLayer.frompil(visivel, psd, c.nome, top=max(0, c.y), left=max(0, c.x))
        camada.visible = c.visivel
        psd.append(camada)
    caminhos = {"psd": base.with_suffix(".psd"), "png": base.with_suffix(".png"), "webp": base.with_suffix(".webp")}
    psd.save(caminhos["psd"])
    final = achatar(camadas, largura, altura).convert("RGB")
    final.save(caminhos["png"])
    final.save(caminhos["webp"], "WEBP", quality=90)
    return caminhos
