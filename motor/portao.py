"""Portão de geração: o único lugar por onde uma parte gerada entra no pipeline.

O resto do código pede "a parte X da ficha" e não sabe de onde ela vem. A
escolha do modelo (computador próprio, nuvem, API externa) fica por trás
deste portão e pode mudar sem mexer no resto.

Provedores:
  rascunho   desenha uma imagem simples localmente. Custo zero. Serve para
             testar layout, texto e composição.
  registro   usa partes que o operador já gerou (por exemplo, via MCP) e
             registrou em partes/<marca>/registro.yaml com a receita completa.
             Só aceita a parte se o prompt registrado for o mesmo da ficha.
  comfyui    gera a parte num ComfyUI local com o grafo
             integracoes/comfyui/grafos/parte.json e a registra no
             registro.yaml, com a mesma receita. Custo zero.

Próximo provedor: API externa com teto de gasto obrigatório.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import json
import time
import urllib.parse
import urllib.request
import uuid

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

from . import ficha as F

RAIZ = Path(__file__).resolve().parent.parent


class ParteRecusada(RuntimeError):
    pass


@dataclass
class Portao:
    provedor: str = "rascunho"
    gasto_usd: float = 0.0
    log: list[dict] = field(default_factory=list)
    semente: int = 519
    recorte: dict = field(default_factory=dict)   # método de recorte de cada parte, vindo da receita

    def parte(self, ficha: dict, parte: str, formato: str, tema: str | None = None) -> Image.Image:
        prompt = F.prompt_da_parte(ficha, parte, tema)
        if self.provedor == "rascunho":
            im = _rascunho(ficha, parte, formato)
            self.log.append({"parte": parte, "formato": formato, "provedor": "rascunho", "custo_usd": 0.0})
            return im
        if self.provedor == "comfyui":
            self._do_comfyui(ficha, parte, formato, prompt)
        if self.provedor in ("registro", "comfyui"):
            return self._do_registro(ficha, parte, formato, prompt)
        raise ValueError(f"provedor desconhecido: {self.provedor}")

    def _do_registro(self, ficha, parte, formato, prompt) -> Image.Image:
        pasta = RAIZ / "partes" / ficha["marca"]
        registro = _ler_registro(pasta)
        candidatas = [
            e for e in registro["entradas"]
            if e["parte"] == parte and e.get("escolhida") and e.get("formato", formato) == formato
        ]
        if not candidatas:
            raise ParteRecusada(f"nenhuma parte escolhida para {parte}/{formato} em {pasta}/registro.yaml")
        iguais = [e for e in candidatas if " ".join(e["prompt"].split()) == prompt]
        if not iguais:
            raise ParteRecusada(f"{parte}/{formato}: nenhuma parte registrada tem o prompt da ficha {ficha['versao']}"
                                " (o tema ou a receita mudou: gere de novo)")
        e = iguais[-1]
        self.recorte[parte] = e.get("recorte", "liso")
        if not any(l.get("arquivo") == e["arquivo"] for l in self.log):  # cada arquivo pago uma vez
            self.gasto_usd += e.get("custo_usd", 0.0)
        self.log.append({"parte": parte, "formato": formato, "provedor": "registro", "arquivo": e["arquivo"],
                         "modelo": e["modelo"], "semente": e["semente"], "custo_usd": e.get("custo_usd", 0.0)})
        return Image.open(pasta / e["arquivo"])

    def _do_comfyui(self, ficha, parte, formato, prompt) -> None:
        """Gera a parte no ComfyUI e acrescenta a entrada ao registro."""
        cfg = yaml.safe_load((RAIZ / "integracoes/comfyui/config.yaml").read_text(encoding="utf-8"))
        tam = cfg["tamanhos"][parte]
        largura, altura = tam[formato] if isinstance(tam, dict) else tam
        valores = {"checkpoint": cfg["checkpoint"], "prompt": prompt, "negativo": cfg["negativo"],
                   "largura": largura, "altura": altura, "semente": self.semente,
                   "passos": cfg["passos"], "cfg": cfg["cfg"], "prefixo": f"gera/{ficha['marca']}-{parte}"}
        grafo = preencher(json.loads((RAIZ / "integracoes/comfyui/grafos/parte.json").read_text()), valores)
        imagem = executar_comfyui(cfg["url"], grafo)
        pasta = RAIZ / "partes" / ficha["marca"]
        arquivo = f"comfyui-{parte}{'-' + formato if parte == 'cena' else ''}-{uuid.uuid4().hex[:8]}.png"
        imagem.save(pasta / arquivo)
        entrada = {"parte": parte, "arquivo": arquivo, "modelo": f"comfyui/{cfg['checkpoint']}",
                   "semente": self.semente, "tamanho": [largura, altura], "passos": cfg["passos"],
                   "custo_usd": 0.0, "escolhida": True, "ficha_versao": ficha["versao"], "prompt": prompt}
        if ficha["partes"][parte].get("transparente"):
            entrada["recorte"] = cfg.get("recorte", {}).get(parte, "liso")
        if parte == "cena":
            entrada["formato"] = formato
        registro = _ler_registro(pasta)
        registro["entradas"].append(entrada)
        caminho = pasta / "registro.yaml"
        texto = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
        cabecalho = texto[: texto.index("ficha:")] if "ficha:" in texto else ""
        (pasta / "registro.yaml").write_text(
            cabecalho + yaml.safe_dump(registro, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def _ler_registro(pasta: Path) -> dict:
    caminho = pasta / "registro.yaml"
    if not caminho.exists():
        return {"entradas": []}
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def preencher(grafo, valores: dict):
    """Troca os "{{nome}}" do grafo pelos valores (mantendo o tipo do valor)."""
    if isinstance(grafo, dict):
        return {k: preencher(v, valores) for k, v in grafo.items()}
    if isinstance(grafo, list):
        return [preencher(v, valores) for v in grafo]
    if isinstance(grafo, str) and grafo.startswith("{{") and grafo.endswith("}}"):
        return valores[grafo[2:-2]]
    return grafo


def executar_comfyui(url: str, grafo: dict, espera_max: float = 900, abrir=urllib.request.urlopen) -> Image.Image:
    """Manda o grafo (formato API) para o ComfyUI, espera e devolve a primeira imagem salva."""
    corpo = json.dumps({"prompt": grafo, "client_id": uuid.uuid4().hex}).encode()
    pedido = urllib.request.Request(f"{url}/prompt", corpo, {"Content-Type": "application/json"})
    pid = json.load(abrir(pedido))["prompt_id"]
    limite = time.time() + espera_max
    while time.time() < limite:
        hist = json.load(abrir(f"{url}/history/{pid}")).get(pid)
        if hist and hist.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"ComfyUI falhou: {hist['status']}")
        if hist and hist.get("status", {}).get("completed"):
            for saida in hist["outputs"].values():
                for img in saida.get("images", []):
                    q = urllib.parse.urlencode({k: img[k] for k in ("filename", "subfolder", "type")})
                    with abrir(f"{url}/view?{q}") as r:
                        im = Image.open(r)
                        im.load()
                        return im
            raise RuntimeError("ComfyUI terminou sem imagem")
        time.sleep(1)
    raise TimeoutError(f"ComfyUI não terminou em {espera_max}s")


def _rascunho(ficha: dict, parte: str, formato: str) -> Image.Image:
    """Placa simples nas cores da ficha, para testar sem gastar."""
    cores = ficha["cores"]
    if parte == "cena":
        w, h = F.tamanho(ficha, formato)
        topo = np.array(Image.new("RGB", (1, 1), cores["ceu_topo"]).getpixel((0, 0)), dtype=np.float32)
        ouro = np.array(Image.new("RGB", (1, 1), cores["ouro"]).getpixel((0, 0)), dtype=np.float32)
        t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        ceu = (topo * (1 - t) + ouro * t).repeat(w, axis=1)
        im = Image.fromarray(ceu.astype(np.uint8), "RGB")
        d = ImageDraw.Draw(im)
        r = h * 0.1
        d.ellipse((w * 0.45 - r, h * 0.55 - r, w * 0.45 + r, h * 0.55 + r), fill=(255, 245, 200))
        selva = cores["selva_escura"]
        d.rectangle((0, 0, w * 0.18, h), fill=selva)
        d.rectangle((w * 0.85, 0, w, h), fill=selva)
        d.rectangle((0, h * 0.8, w, h), fill=selva)
        return im.filter(ImageFilter.GaussianBlur(h * 0.02))
    if parte == "entorno":
        im = Image.new("RGB", (768, 512), (205, 205, 205))
        d = ImageDraw.Draw(im)
        for x, y in ((90, 80), (620, 120), (160, 400), (560, 420), (380, 60)):
            d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=cores["ouro"], outline=cores["ouro_escuro"], width=6)
        return im
    im = Image.new("RGB", (768, 1024), (205, 205, 205))
    d = ImageDraw.Draw(im)
    d.ellipse((184, 260, 584, 1024), fill=cores["vermelho_arara"])
    d.ellipse((264, 80, 504, 340), fill=cores["vermelho_arara"])
    d.polygon([(470, 180), (560, 230), (470, 280)], fill=(30, 30, 30))
    return im
