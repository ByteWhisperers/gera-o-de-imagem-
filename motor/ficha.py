"""Lê e confere a ficha de estilo, o contrato entre as etapas."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

OBRIGATORIOS = ("versao", "marca", "formatos", "camadas", "layout", "partes", "texto", "qa")


class FichaInvalida(ValueError):
    pass


def carregar(caminho: str | Path) -> dict:
    caminho = Path(caminho)
    ficha = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    faltando = [k for k in OBRIGATORIOS if k not in ficha]
    if faltando:
        raise FichaInvalida(f"{caminho}: faltam as chaves {faltando}")
    for formato in ficha["formatos"]:
        if formato not in ficha["layout"]:
            raise FichaInvalida(f"{caminho}: formato '{formato}' sem layout")
    for nome, t in ficha.get("temas", {}).items():
        if t.get("figurino") not in ficha["partes"]["mascote"].get("figurinos", {}):
            raise FichaInvalida(f"{caminho}: o tema '{nome}' pede o figurino '{t.get('figurino')}', que não existe")
    for camada in ficha["camadas"]:
        if camada["tipo"] == "gerada" and camada["parte"] not in ficha["partes"]:
            raise FichaInvalida(f"{caminho}: camada '{camada['id']}' pede a parte '{camada['parte']}', que não existe")
    ficha["_caminho"] = caminho.as_posix()
    return ficha


def resolver_tema(ficha: dict, tema: str | None = None) -> dict:
    """O tema liga a mensagem ao mascote: figurino, o que ele segura e o entorno.

    Fichas sem `temas` (v1.0) só conhecem o figurino; nelas `tema` é o nome do figurino.
    """
    temas = ficha.get("temas")
    if not temas:
        return {"nome": None, "figurino": tema or ficha["partes"]["mascote"].get("figurino_padrao")}
    nome = tema or ficha["tema_padrao"]
    if nome not in temas:
        raise FichaInvalida(f"tema '{nome}' não existe; temas da ficha: {sorted(temas)}")
    return {"nome": nome, **temas[nome]}


def prompt_da_parte(ficha: dict, parte: str, tema: str | None = None) -> str:
    """O prompt final de uma parte, já com o figurino e os elementos do tema."""
    p = ficha["partes"][parte]
    t = resolver_tema(ficha, tema)
    texto = " ".join(p["prompt"].split())
    if "{figurino}" in texto:
        texto = texto.replace("{figurino}", " ".join(ficha["partes"]["mascote"]["figurinos"][t["figurino"]].split()))
    for chave, valor in t.items():                 # segura, entorno, frente... o que o tema trouxer
        if isinstance(valor, str) and "{" + chave + "}" in texto:
            texto = texto.replace("{" + chave + "}", " ".join(valor.split()))
    falta = sorted(set(re.findall(r"\{(\w+)\}", texto)))
    if falta:
        raise FichaInvalida(f"o prompt da parte '{parte}' pede {falta}, que o tema '{t.get('nome')}' não traz")
    return texto


def linhas_de_texto(ficha: dict, tema: str | None = None) -> list[dict]:
    """As linhas de exemplo do tema, ou as linhas neutras da ficha."""
    return resolver_tema(ficha, tema).get("texto_exemplo") or ficha["texto"]["exemplo"]


def tamanho(ficha: dict, formato: str) -> tuple[int, int]:
    f = ficha["formatos"][formato]
    return f["largura"], f["altura"]
