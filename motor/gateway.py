"""Conversa com o gateway de imagem (repositório 22kofking/gateway-imagem) pela API HTTP.

  gerar   pede uma imagem (POST /v1/images), espera o job e devolve a imagem e o
          custo que o gateway informou

O gateway só aceita alguns tamanhos. `tamanho_do_gateway` escolhe o de proporção
mais parecida com a parte e `ajustar` corta o centro na proporção certa, sem
diminuir a imagem: a composição redimensiona depois.

A chave do app fica na variável de ambiente GATEWAY_CHAVE, nunca em arquivo.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

from PIL import Image

# Os tamanhos que o gateway aceita (gateway/app/schemas.py, SIZES).
TAMANHOS = ((1024, 1024), (1024, 768), (768, 1024), (1280, 720), (720, 1280))


class GatewayFalhou(RuntimeError):
    pass


def tamanho_do_gateway(largura: int, altura: int) -> tuple[int, int]:
    """O tamanho aceito pelo gateway com a proporção mais parecida com largura x altura."""
    alvo = largura / altura
    return min(TAMANHOS, key=lambda t: abs(t[0] / t[1] - alvo) / alvo)


def ajustar(imagem: Image.Image, largura: int, altura: int) -> Image.Image:
    """Corta o centro da imagem na proporção largura x altura, mantendo o maior tamanho possível."""
    w, h = imagem.size
    alvo = largura / altura
    if w / h > alvo:
        novo_w = round(h * alvo)
        x = (w - novo_w) // 2
        return imagem.crop((x, 0, x + novo_w, h))
    novo_h = round(w / alvo)
    y = (h - novo_h) // 2
    return imagem.crop((0, y, w, y + novo_h))


def chave() -> str:
    valor = os.environ.get("GATEWAY_CHAVE", "")
    if not valor:
        raise GatewayFalhou("defina a variável de ambiente GATEWAY_CHAVE com a chave deste app no gateway")
    return valor


def gerar(url: str, chave_app: str, modelo: str, prompt: str, largura: int, altura: int, semente: int,
          espera_max: float = 300, intervalo: float = 1.5,
          abrir=urllib.request.urlopen) -> tuple[Image.Image, float | None]:
    """Pede a imagem ao gateway e espera. Devolve (imagem já cortada na proporção, custo em US$ ou None)."""
    w, h = tamanho_do_gateway(largura, altura)
    cabecalho = {"Authorization": f"Bearer {chave_app}", "Content-Type": "application/json"}
    corpo = json.dumps({"model": modelo, "prompt": prompt, "size": f"{w}x{h}", "seed": semente,
                        "wait": True}).encode()
    job = _json(abrir, urllib.request.Request(f"{url}/v1/images", corpo, cabecalho, method="POST"))
    limite = time.monotonic() + espera_max
    while job["status"] == "running":
        if time.monotonic() > limite:
            raise GatewayFalhou(f"o job {job['id']} não terminou em {espera_max:.0f} s")
        time.sleep(intervalo)
        job = _json(abrir, urllib.request.Request(f"{url}/v1/jobs/{job['id']}", headers=cabecalho))
    if job["status"] != "succeeded" or not job.get("images"):
        raise GatewayFalhou(f"o gateway não gerou a imagem: {job.get('error') or job['status']}")
    imagem = Image.open(io.BytesIO(_baixar(abrir, job["images"][0])))
    imagem.load()
    return ajustar(imagem.convert("RGB"), largura, altura), job.get("cost_usd")


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
