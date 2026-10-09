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

Próximos provedores (fase 3 do plano): comfyui (grafo salvo, via API HTTP do
ComfyUI) e API externa com teto de gasto obrigatório.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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

    def parte(self, ficha: dict, parte: str, formato: str, figurino: str | None = None) -> Image.Image:
        if parte == "mascote":
            figurino = figurino or ficha["partes"]["mascote"].get("figurino_padrao")
        prompt = F.prompt_da_parte(ficha, parte, figurino)
        if self.provedor == "rascunho":
            im = _rascunho(ficha, parte, formato)
            self.log.append({"parte": parte, "formato": formato, "provedor": "rascunho", "custo_usd": 0.0})
            return im
        if self.provedor == "registro":
            return self._do_registro(ficha, parte, formato, figurino, prompt)
        raise ValueError(f"provedor desconhecido: {self.provedor}")

    def _do_registro(self, ficha, parte, formato, figurino, prompt) -> Image.Image:
        pasta = RAIZ / "partes" / ficha["marca"]
        registro = yaml.safe_load((pasta / "registro.yaml").read_text(encoding="utf-8"))
        candidatas = [
            e for e in registro["entradas"]
            if e["parte"] == parte and e.get("escolhida")
            and e.get("formato", formato) == formato
            and (figurino is None or e.get("figurino", figurino) == figurino)
        ]
        if not candidatas:
            raise ParteRecusada(f"nenhuma parte escolhida para {parte}/{formato}/{figurino} em {pasta}/registro.yaml")
        e = candidatas[-1]
        if " ".join(e["prompt"].split()) != prompt:
            raise ParteRecusada(f"{e['arquivo']}: o prompt registrado não é o da ficha {ficha['versao']}")
        if not any(l.get("arquivo") == e["arquivo"] for l in self.log):  # cada arquivo pago uma vez
            self.gasto_usd += e.get("custo_usd", 0.0)
        self.log.append({"parte": parte, "formato": formato, "provedor": "registro", "arquivo": e["arquivo"],
                         "modelo": e["modelo"], "semente": e["semente"], "custo_usd": e.get("custo_usd", 0.0)})
        return Image.open(pasta / e["arquivo"])


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
    im = Image.new("RGB", (768, 1024), (205, 205, 205))
    d = ImageDraw.Draw(im)
    d.ellipse((184, 260, 584, 1024), fill=cores["vermelho_arara"])
    d.ellipse((264, 80, 504, 340), fill=cores["vermelho_arara"])
    d.polygon([(470, 180), (560, 230), (470, 280)], fill=(30, 30, 30))
    return im
