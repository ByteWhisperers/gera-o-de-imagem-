"""Grafo de uma peça de referência: a peça inteira, as partes isoladas e as relações.

A desconstrução (ferramentas/desconstruir.py) escreve o grafo; o compilador
(motor/compilador.py) e o comparador (motor/comparar.py) só leem. O grafo não
substitui a ficha: descreve UMA peça, e a ficha continua sendo a regra da marca.

Formato grafo-peca/0.1 (JSON):
  referencia   a peça inteira, como chegou
  pasta        onde ficam as máscaras, os recortes e as placas desta peça
  placas       a peça sem texto e logo (sem_texto) e só o fundo (cena_limpa)
  nos          uma entrada por parte: id, tipo, z (de baixo para cima),
               camada_psd, caixa [x, y, w, h] em frações, mascara (PNG),
               descricao, e de onde veio cada número (medido:<método> ou estimativa)
  arestas      relações entre partes: segura, apresenta, cerca, veste,
               tema_liga, fica_sobre, alinhado_com, empilhado_acima, contraste
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
FORMATO = "grafo-peca/0.1"

TIPOS = {
    "fundo", "efeito", "personagem", "objeto", "objeto_grupo", "objeto_segurado", "acessorio", "texto", "logo",
}
# O que a IA pode gerar. Texto e logo saem de código, nunca da IA.
GERAVEIS = {"fundo", "personagem", "objeto", "objeto_grupo", "objeto_segurado", "acessorio"}
RELACOES = {
    "segura", "apresenta", "cerca", "veste", "tema_liga", "fica_sobre", "alinhado_com", "empilhado_acima", "contraste",
}


class GrafoInvalido(ValueError):
    pass


def carregar(caminho: str | Path) -> dict:
    caminho = Path(caminho)
    grafo = json.loads(caminho.read_text(encoding="utf-8"))
    conferir(grafo, caminho)
    grafo["_caminho"] = caminho.as_posix()
    grafo["_sha256"] = hashlib.sha256(caminho.read_bytes()).hexdigest()
    return grafo


def conferir(grafo: dict, origem: str | Path = "grafo") -> None:
    if grafo.get("formato") != FORMATO:
        raise GrafoInvalido(f"{origem}: formato '{grafo.get('formato')}', esperado '{FORMATO}'")
    for chave in ("marca", "ficha", "referencia", "formato_peca", "tamanho_px", "pasta", "nos", "arestas"):
        if chave not in grafo:
            raise GrafoInvalido(f"{origem}: falta a chave '{chave}'")
    ids = [n["id"] for n in grafo["nos"]]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise GrafoInvalido(f"{origem}: ids repetidos {repetidos}")
    for n in grafo["nos"]:
        if n.get("tipo") not in TIPOS:
            raise GrafoInvalido(f"{origem}: nó '{n['id']}' com tipo '{n.get('tipo')}' desconhecido")
        caixa = n.get("caixa")
        if caixa is not None:
            x, y, w, h = caixa
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1.0001 and 0 < h <= 1.0001):
                raise GrafoInvalido(f"{origem}: caixa de '{n['id']}' fora da peça: {caixa}")
    for a in grafo["arestas"]:
        for ponta in ("de", "para"):
            if a[ponta] not in ids:
                raise GrafoInvalido(f"{origem}: aresta {a} aponta para '{a[ponta]}', que não existe")
        if a["rel"] not in RELACOES:
            raise GrafoInvalido(f"{origem}: relação '{a['rel']}' desconhecida")


def no(grafo: dict, id_: str) -> dict:
    for n in grafo["nos"]:
        if n["id"] == id_:
            return n
    raise KeyError(id_)


def pasta(grafo: dict) -> Path:
    return RAIZ / grafo["pasta"]


def mascara(grafo: dict, id_: str) -> np.ndarray:
    """Máscara booleana (altura x largura) de um nó."""
    n = no(grafo, id_)
    if "mascara" not in n:
        raise KeyError(f"o nó '{id_}' não tem máscara")
    return np.asarray(Image.open(pasta(grafo) / n["mascara"]).convert("L")) > 127


def camadas_geradas(grafo: dict) -> list[str]:
    """Camadas do PSD que a IA gera nesta peça, de baixo para cima."""
    vistas: dict[str, int] = {}
    for n in grafo["nos"]:
        if n["tipo"] in GERAVEIS and n.get("camada_psd") and "mascara" in n:
            vistas[n["camada_psd"]] = min(vistas.get(n["camada_psd"], 99), n.get("z", 0))
    return sorted(vistas, key=lambda c: vistas[c])


def mascara_camada(grafo: dict, camada: str) -> np.ndarray:
    """União das máscaras dos nós que caem numa camada do PSD."""
    w, h = grafo["tamanho_px"]
    total = np.zeros((h, w), bool)
    for n in grafo["nos"]:
        if n.get("camada_psd") == camada and "mascara" in n:
            total |= mascara(grafo, n["id"])
    return total


def caixa_px(m: np.ndarray, margem: float = 0.0) -> tuple[int, int, int, int] | None:
    """Caixa (x, y, w, h) em pixels do que está ligado na máscara, com margem em fração do lado."""
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    h, w = m.shape
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    mx, my = round((x1 - x0) * margem), round((y1 - y0) * margem)
    x0, y0, x1, y1 = max(0, x0 - mx), max(0, y0 - my), min(w, x1 + mx), min(h, y1 + my)
    return int(x0), int(y0), int(x1 - x0), int(y1 - y0)


def caixa_frac(caixa: tuple[int, int, int, int], largura: int, altura: int) -> list[float]:
    x, y, w, h = caixa
    return [round(x / largura, 4), round(y / altura, 4), round(w / largura, 4), round(h / altura, 4)]


def uniao_caixas(caixas: list[list[float]]) -> list[float]:
    x0 = min(c[0] for c in caixas)
    y0 = min(c[1] for c in caixas)
    x1 = max(c[0] + c[2] for c in caixas)
    y1 = max(c[1] + c[3] for c in caixas)
    return [round(x0, 4), round(y0, 4), round(x1 - x0, 4), round(y1 - y0, 4)]


def layout_medido(grafo: dict) -> dict:
    """Caixas medidas do texto e do logo, no formato do `layout` da ficha.

    Serve para montar a peça no lugar da referência, em vez das estimativas da ficha.
    """
    textos = [n["caixa"] for n in grafo["nos"] if n["tipo"] == "texto" and "caixa" in n]
    logo = next((n["caixa"] for n in grafo["nos"] if n["tipo"] == "logo" and "caixa" in n), None)
    saida = {}
    if textos:
        x, y, w, h = uniao_caixas(textos)
        saida["texto"] = {"x": x, "y": y, "w": w, "h": h}
    if logo:
        x, y, w, h = logo
        saida["logo"] = {"x": x, "y": y, "w": w}
    return saida
