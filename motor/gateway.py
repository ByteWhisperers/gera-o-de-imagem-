"""Conversa com o gateway de imagem (repositório 22kofking/gateway-imagem) pela API HTTP.

  gerar          pede uma imagem (POST /v1/images), do zero ou a partir de uma
                 imagem de entrada (image-to-image, com `forca`), espera o job e
                 devolve a imagem e o custo que o gateway informou
  refazer_ramos  o equivalente do workflow do compilador: refaz cada camada da
                 peça na região dela da referência (loop do tentativa.py)
  placa          apaga a região da máscara de uma imagem (placas da desconstrução)

O gateway aceita qualquer tamanho com cada lado entre 256 e 1536. Fora disso,
`tamanho_aceito` muda a escala mantendo a proporção.

A chave do app fica na variável de ambiente GATEWAY_CHAVE, nunca em arquivo.
GATEWAY_URL, se definida, troca a url do integracoes/gateway/config.yaml.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
LADO_MIN, LADO_MAX = 256, 1536


class GatewayFalhou(RuntimeError):
    pass


class TetoDeGasto(RuntimeError):
    pass


def ler_config(raiz: Path = RAIZ) -> dict:
    cfg = yaml.safe_load((raiz / "integracoes/gateway/config.yaml").read_text(encoding="utf-8"))
    cfg["url"] = os.environ.get("GATEWAY_URL") or cfg["url"]
    return cfg


def chave() -> str:
    valor = os.environ.get("GATEWAY_CHAVE", "")
    if not valor:
        raise GatewayFalhou("defina a variável de ambiente GATEWAY_CHAVE com a chave deste app no gateway")
    return valor


@dataclass
class Caixa:
    """Quanto uma rodada pode gastar. Confere ANTES de cada pedido, pelo preço do config."""

    teto_usd: float
    preco_usd: float
    gasto_usd: float = 0.0
    pedidos: list[dict] = field(default_factory=list)

    def conferir(self, o_que: str) -> None:
        if self.gasto_usd + self.preco_usd > self.teto_usd + 1e-9:
            raise TetoDeGasto(f"{o_que}: gerar custaria US${self.preco_usd}, a rodada já gastou "
                              f"US${self.gasto_usd:.3f} e o teto é US${self.teto_usd}")

    def pagar(self, o_que: str, custo: float | None) -> float:
        custo = self.preco_usd if custo is None else custo
        self.gasto_usd += custo
        self.pedidos.append({"o_que": o_que, "custo_usd": custo})
        return custo


def tamanho_aceito(largura: int, altura: int) -> tuple[int, int]:
    """O tamanho mais perto de largura x altura com cada lado entre 256 e 1536, mesma proporção."""
    escala = 1.0
    if max(largura, altura) > LADO_MAX:
        escala = LADO_MAX / max(largura, altura)
    if min(largura, altura) * escala < LADO_MIN:
        escala = LADO_MIN / min(largura, altura)
    w, h = round(largura * escala), round(altura * escala)
    return min(max(w, LADO_MIN), LADO_MAX), min(max(h, LADO_MIN), LADO_MAX)


def data_uri(imagem: Image.Image) -> str:
    dados = io.BytesIO()
    imagem.convert("RGB").save(dados, "PNG")
    return "data:image/png;base64," + base64.b64encode(dados.getvalue()).decode()


def gerar(url: str, chave_app: str, modelo: str, prompt: str, largura: int, altura: int, semente: int,
          imagem: Image.Image | None = None, forca: float | None = None, espera_max: float = 300,
          intervalo: float = 1.5, abrir=urllib.request.urlopen) -> tuple[Image.Image, float | None]:
    """Pede a imagem ao gateway e espera. Devolve (imagem em largura x altura, custo em US$ ou None)."""
    w, h = tamanho_aceito(largura, altura)
    pedido = {"model": modelo, "prompt": prompt, "size": f"{w}x{h}", "seed": semente, "wait": True}
    if imagem is not None:
        pedido["image"] = data_uri(imagem.resize((w, h), Image.LANCZOS))
        if forca is not None:
            pedido["strength"] = forca
    cabecalho = {"Authorization": f"Bearer {chave_app}", "Content-Type": "application/json"}
    job = _json(abrir, urllib.request.Request(f"{url}/v1/images", json.dumps(pedido).encode(), cabecalho,
                                              method="POST"))
    limite = time.monotonic() + espera_max
    while job["status"] == "running":
        if time.monotonic() > limite:
            raise GatewayFalhou(f"o job {job['id']} não terminou em {espera_max:.0f} s")
        time.sleep(intervalo)
        job = _json(abrir, urllib.request.Request(f"{url}/v1/jobs/{job['id']}", headers=cabecalho))
    if job["status"] != "succeeded" or not job.get("images"):
        raise GatewayFalhou(f"o gateway não gerou a imagem: {job.get('error') or job['status']}")
    saida = Image.open(io.BytesIO(_baixar(abrir, job["images"][0])))
    saida = saida.convert("RGB")
    if saida.size != (largura, altura):
        saida = saida.resize((largura, altura), Image.LANCZOS)
    return saida, job.get("cost_usd")


def _json(abrir, pedido) -> dict:
    try:
        return json.load(abrir(pedido))
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace")[:300]
        raise GatewayFalhou(f"gateway respondeu {e.code}: {detalhe}") from e
    except urllib.error.URLError as e:
        raise GatewayFalhou(f"não consegui falar com o gateway em {pedido.full_url}: {e.reason}") from e


def _baixar(abrir, endereco: str) -> bytes:
    """A imagem vem como link (provedor ou bucket) ou como data URI (gateway sem bucket)."""
    if endereco.startswith("data:"):
        return base64.b64decode(endereco.split(",", 1)[1])
    return abrir(endereco).read()


# ------------------------------------------------- loop e placas pelo gateway


def refazer_ramos(comp, grafo: dict, cfg: dict, caixa: Caixa, gerar_=None) -> dict[str, tuple[Image.Image, int, int]]:
    """Faz pelo gateway o que o workflow compilado faria no ComfyUI.

    Para cada camada em `comp.saidas`: corta a placa na caixa da parte, reduz ao
    tamanho de geração, pede o image-to-image com a força (denoise) do ramo, volta
    ao tamanho da caixa e, fora o fundo, aplica a máscara da parte como alfa.
    Devolve camada -> (imagem, x, y), como o tentativa.py monta o PSD.
    """
    from . import grafo as G
    from .compilador import _placa, tamanho_geracao

    gerar_ = gerar_ or gerar
    url, chave_app = cfg["url"], chave()
    saidas = {}
    for camada, s in comp.saidas.items():
        x, y, w, h = s["x"], s["y"], s["w"], s["h"]
        if s["classe"] == "fundo":
            fonte = _placa(grafo, "cena_limpa")
        else:
            fonte = _placa(grafo, "sem_texto").crop((x, y, x + w, y + h))
        lado = cfg.get("loop", {}).get("lado", {}).get(s["classe"])
        gw, gh = tamanho_geracao(w, h, min(lado, LADO_MAX)) if lado else s["geracao"]
        caixa.conferir(camada)
        im, custo = gerar_(url, chave_app, cfg["modelo"], s["prompt"], gw, gh, comp.parametros["semente"],
                           imagem=fonte.resize((gw, gh), Image.LANCZOS), forca=s["denoise"],
                           espera_max=cfg.get("espera_max", 300))
        caixa.pagar(camada, custo)
        im = im.resize((w, h), Image.LANCZOS)
        if s["classe"] != "fundo":
            mascara = G.mascara_camada(grafo, camada)[y:y + h, x:x + w]
            im = im.convert("RGBA")
            im.putalpha(Image.fromarray((mascara * 255).astype(np.uint8)))
        saidas[camada] = (im, x, y)
        s["geracao"], s["motor"] = [gw, gh], f"gateway/{cfg['modelo']}"
    return saidas


def placa(preenchida: Image.Image, mascara: Image.Image, prompt: str, forca: float, semente: int, cfg: dict,
          caixa: Caixa, lado: int = 1024, gerar_=None) -> Image.Image:
    """Apaga a região branca da máscara: image-to-image da peça inteira e, fora do buraco,
    os pixels de `preenchida` voltam intactos (como o ImageCompositeMasked do ComfyUI)."""
    gerar_ = gerar_ or gerar
    W, H = preenchida.size
    escala = lado / max(W, H)
    gw, gh = round(W * escala / 16) * 16, round(H * escala / 16) * 16
    caixa.conferir("placa")
    im, custo = gerar_(cfg["url"], chave(), cfg["modelo"], prompt, gw, gh, semente,
                       imagem=preenchida.resize((gw, gh), Image.LANCZOS), forca=forca,
                       espera_max=cfg.get("espera_max", 300))
    caixa.pagar("placa", custo)
    im = im.resize((W, H), Image.LANCZOS)
    return Image.composite(im, preenchida.convert("RGB"), mascara.convert("L"))
