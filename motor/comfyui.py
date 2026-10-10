"""Conversa com um ComfyUI (local ou remoto) pela API HTTP.

  enviar_imagem   sobe uma imagem para a pasta de entrada (para o LoadImage)
  executar        manda um workflow em formato API, espera e devolve as imagens
                  salvas, por nó
  object_info     a lista de nós e modelos instalados, para conferir um workflow

Se o workflow for inválido, o ComfyUI recusa no /prompt e devolve node_errors;
aqui isso vira WorkflowRecusado com a lista de erros.
"""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image


class WorkflowRecusado(RuntimeError):
    def __init__(self, mensagem: str, erros: dict):
        super().__init__(mensagem)
        self.erros = erros


def enviar_imagem(url: str, nome: str, imagem: Image.Image, abrir=urllib.request.urlopen) -> str:
    """Sobe a imagem como PNG com esse nome (sobrescreve). Devolve o nome que o ComfyUI usou."""
    dados = io.BytesIO()
    imagem.save(dados, "PNG")
    fronteira = uuid.uuid4().hex
    corpo = b"".join([
        f"--{fronteira}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{nome}\"\r\n"
        "Content-Type: image/png\r\n\r\n".encode(), dados.getvalue(), b"\r\n",
        f"--{fronteira}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{fronteira}--\r\n".encode(),
    ])
    pedido = urllib.request.Request(f"{url}/upload/image", corpo,
                                    {"Content-Type": f"multipart/form-data; boundary={fronteira}"})
    return json.load(abrir(pedido))["name"]


def object_info(url: str, abrir=urllib.request.urlopen) -> dict:
    return json.load(abrir(f"{url}/object_info"))


def versao(url: str, abrir=urllib.request.urlopen) -> str | None:
    try:
        return json.load(abrir(f"{url}/system_stats"))["system"]["comfyui_version"]
    except (OSError, KeyError, ValueError):
        return None


def enfileirar(url: str, workflow: dict, abrir=urllib.request.urlopen) -> str:
    corpo = json.dumps({"prompt": workflow, "client_id": uuid.uuid4().hex}).encode()
    pedido = urllib.request.Request(f"{url}/prompt", corpo, {"Content-Type": "application/json"})
    try:
        resposta = json.load(abrir(pedido))
    except urllib.error.HTTPError as e:
        detalhe = json.loads(e.read() or b"{}")
        raise WorkflowRecusado(f"o ComfyUI recusou o workflow: {detalhe.get('error', {}).get('message', e)}",
                               detalhe.get("node_errors", {})) from None
    if resposta.get("node_errors"):
        raise WorkflowRecusado("o ComfyUI recusou o workflow", resposta["node_errors"])
    return resposta["prompt_id"]


def executar(url: str, workflow: dict, espera_max: float = 1800, abrir=urllib.request.urlopen) -> dict[str, list]:
    """Roda o workflow e devolve {id do nó: [imagens salvas por ele]}."""
    pid = enfileirar(url, workflow, abrir)
    limite = time.time() + espera_max
    while time.time() < limite:
        hist = json.load(abrir(f"{url}/history/{pid}")).get(pid)
        if hist and hist.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"ComfyUI falhou: {hist['status']}")
        if hist and hist.get("status", {}).get("completed"):
            saidas: dict[str, list] = {}
            for no, saida in hist["outputs"].items():
                for img in saida.get("images", []):
                    q = urllib.parse.urlencode({k: img[k] for k in ("filename", "subfolder", "type")})
                    with abrir(f"{url}/view?{q}") as r:
                        im = Image.open(io.BytesIO(r.read()))
                        im.load()
                    saidas.setdefault(no, []).append(im)
            if not saidas:
                raise RuntimeError("ComfyUI terminou sem imagem")
            return saidas
        time.sleep(1)
    raise TimeoutError(f"ComfyUI não terminou em {espera_max}s")
