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
  comfyui    biblioteca primeiro: se já existe parte registrada com a mesma
             receita, reaproveita (o fundo não muda quando só o tema muda).
             Se não existe, ou se a parte foi pedida em `novas`, gera num
             ComfyUI local com o grafo integracoes/comfyui/grafos/parte.json e
             a registra no registro.yaml. Custo zero.
  gateway    como o comfyui (biblioteca primeiro), mas gera pelo gateway de
             imagem (22kofking/gateway-imagem), configurado em
             integracoes/gateway/config.yaml. É pago: exige teto de gasto
             (teto_usd) e recusa a parte que passaria do teto. O custo de cada
             parte nova vai para o registro.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import json
import urllib.request
import uuid

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

from . import comfyui
from . import gateway
from . import ficha as F

RAIZ = Path(__file__).resolve().parent.parent


class ParteRecusada(RuntimeError):
    pass


TetoDeGasto = gateway.TetoDeGasto


@dataclass
class Portao:
    provedor: str = "rascunho"
    gasto_usd: float = 0.0
    log: list[dict] = field(default_factory=list)
    semente: int = 519
    recorte: dict = field(default_factory=dict)   # método de recorte de cada parte, vindo da receita
    novas: set = field(default_factory=set)       # partes que o dono pediu para gerar de novo (variação)
    teto_usd: float | None = None                 # gateway: quanto esta rodada pode gastar em partes novas
    gasto_novo_usd: float = 0.0                   # gateway: quanto esta rodada já gastou em partes novas

    def parte(self, ficha: dict, parte: str, formato: str, tema: str | None = None) -> Image.Image:
        prompt = F.prompt_da_parte(ficha, parte, tema)
        if self.provedor == "rascunho":
            im = _rascunho(ficha, parte, formato)
            self.log.append({"parte": parte, "formato": formato, "provedor": "rascunho", "custo_usd": 0.0})
            return im
        if self.provedor in ("comfyui", "gateway"):
            if self.provedor == "gateway" and self.teto_usd is None:
                raise TetoDeGasto("o provedor gateway é pago: defina o teto de gasto (--teto)")
            # o gateway só reaproveita partes feitas pelo próprio modelo dele (as do SD-Turbo são piores)
            modelo = f"gateway/{gateway.ler_config(RAIZ)['modelo']}" if self.provedor == "gateway" else None
            if parte not in self.novas:
                try:
                    return self._do_registro(ficha, parte, formato, prompt, modelo)
                except ParteRecusada:
                    pass                      # ainda não está na biblioteca: gera
            if self.provedor == "comfyui":
                self._do_comfyui(ficha, parte, formato, prompt)
            else:
                self._do_gateway(ficha, parte, formato, prompt)
            im = self._do_registro(ficha, parte, formato, prompt, modelo)
            self.log[-1]["gerada_agora"] = True
            return im
        if self.provedor == "registro":
            return self._do_registro(ficha, parte, formato, prompt)
        raise ValueError(f"provedor desconhecido: {self.provedor}")

    def _do_registro(self, ficha, parte, formato, prompt, modelo: str | None = None) -> Image.Image:
        pasta = RAIZ / "partes" / ficha["marca"]
        registro = _ler_registro(pasta)
        candidatas = [
            e for e in registro["entradas"]
            if e["parte"] == parte and e.get("escolhida") and e.get("formato", formato) == formato
            and (modelo is None or e.get("modelo") == modelo)
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
        _registrar(ficha, parte, formato, prompt, imagem, cfg, "comfyui", {
            "modelo": f"comfyui/{cfg['checkpoint']}", "semente": self.semente, "tamanho": [largura, altura],
            "passos": cfg["passos"], "custo_usd": 0.0})

    def _do_gateway(self, ficha, parte, formato, prompt) -> None:
        """Gera a parte pelo gateway, dentro do teto de gasto, e acrescenta a entrada ao registro."""
        cfg = gateway.ler_config(RAIZ)
        preco = cfg["preco_por_imagem_usd"]
        if self.gasto_novo_usd + preco > self.teto_usd + 1e-9:
            raise TetoDeGasto(f"{parte}/{formato}: gerar custaria US${preco}, a rodada já gastou "
                              f"US${self.gasto_novo_usd:.3f} e o teto é US${self.teto_usd}")
        tam = cfg["tamanhos"][parte]
        largura, altura = tam[formato] if isinstance(tam, dict) else tam
        imagem, custo = gerar_no_gateway(cfg["url"], gateway.chave(), cfg["modelo"], prompt, largura, altura,
                                         self.semente, cfg.get("espera_max", 300))
        custo = preco if custo is None else custo
        self.gasto_novo_usd += custo
        _registrar(ficha, parte, formato, prompt, imagem, cfg, "gateway", {
            "modelo": f"gateway/{cfg['modelo']}", "semente": self.semente, "tamanho": list(imagem.size),
            "custo_usd": custo})


def _registrar(ficha, parte, formato, prompt, imagem, cfg, origem: str, receita: dict) -> None:
    """Guarda a imagem em partes/<marca>/ e acrescenta a entrada, com a receita, ao registro.yaml."""
    pasta = RAIZ / "partes" / ficha["marca"]
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = f"{origem}-{parte}{'-' + formato if parte == 'cena' else ''}-{uuid.uuid4().hex[:8]}.png"
    imagem.save(pasta / arquivo)
    entrada = {"parte": parte, "arquivo": arquivo, **receita,
               "escolhida": True, "ficha_versao": ficha["versao"], "prompt": prompt}
    if ficha["partes"][parte].get("transparente"):
        entrada["recorte"] = cfg.get("recorte", {}).get(parte, "liso")
    if parte == "cena":
        entrada["formato"] = formato
    registro = _ler_registro(pasta)
    registro["entradas"].append(entrada)
    caminho = pasta / "registro.yaml"
    texto = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
    cabecalho = "".join(l for l in texto.splitlines(keepends=True)[: _fim_do_cabecalho(texto)])
    (pasta / "registro.yaml").write_text(
        cabecalho + yaml.safe_dump(registro, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def _fim_do_cabecalho(texto: str) -> int:
    """Quantas linhas do começo são comentário ou vazias (o cabeçalho que se mantém)."""
    linhas = texto.splitlines()
    n = 0
    while n < len(linhas) and (not linhas[n].strip() or linhas[n].lstrip().startswith("#")):
        n += 1
    return n


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


def gerar_no_gateway(url, chave_app, modelo, prompt, largura, altura, semente, espera_max=300):
    """Pede a parte ao gateway. Devolve (imagem, custo em US$ ou None)."""
    return gateway.gerar(url, chave_app, modelo, prompt, largura, altura, semente, espera_max=espera_max)


def executar_comfyui(url: str, grafo: dict, espera_max: float = 900, abrir=urllib.request.urlopen) -> Image.Image:
    """Manda o grafo (formato API) para o ComfyUI, espera e devolve a primeira imagem salva."""
    saidas = comfyui.executar(url, grafo, espera_max, abrir)
    return next(iter(saidas.values()))[0]


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
    if parte == "frente":
        im = Image.new("RGB", (768, 512), (205, 205, 205))
        d = ImageDraw.Draw(im)
        for x, y, r in ((230, 330, 150), (580, 390, 105)):
            d.ellipse((x - r, y - r, x + r, y + r), fill=cores["ouro"], outline=cores["ouro_escuro"], width=12)
        return im
    im = Image.new("RGB", (768, 1024), (205, 205, 205))
    d = ImageDraw.Draw(im)
    d.ellipse((184, 260, 584, 1024), fill=cores["vermelho_arara"])
    d.ellipse((264, 80, 504, 340), fill=cores["vermelho_arara"])
    d.polygon([(470, 180), (560, 230), (470, 280)], fill=(30, 30, 30))
    return im
