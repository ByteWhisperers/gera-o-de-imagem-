"""Lê e confere a ficha de estilo, o contrato entre as etapas."""

from __future__ import annotations

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
    for camada in ficha["camadas"]:
        if camada["tipo"] == "gerada" and camada["parte"] not in ficha["partes"]:
            raise FichaInvalida(f"{caminho}: camada '{camada['id']}' pede a parte '{camada['parte']}', que não existe")
    ficha["_caminho"] = caminho.as_posix()
    return ficha


def prompt_da_parte(ficha: dict, parte: str, figurino: str | None = None) -> str:
    """O prompt final de uma parte, já com o figurino escolhido."""
    p = ficha["partes"][parte]
    texto = " ".join(p["prompt"].split())
    if "{figurino}" in texto:
        nome = figurino or p.get("figurino_padrao")
        texto = texto.replace("{figurino}", " ".join(p["figurinos"][nome].split()))
    return texto


def tamanho(ficha: dict, formato: str) -> tuple[int, int]:
    f = ficha["formatos"][formato]
    return f["largura"], f["altura"]
