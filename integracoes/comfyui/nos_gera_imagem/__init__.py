"""Nós do ComfyUI que ligam o canvas ao motor do projeto.

Os nós são finos: a lógica mora em motor/ (testada fora do ComfyUI). Aqui só
se traduz entre os tipos do ComfyUI (IMAGE, STRING) e o motor.

Instalação: crie um link desta pasta em ComfyUI/custom_nodes/ (ver
integracoes/comfyui/LEIA-ME.md).
"""

import json
import sys
from pathlib import Path

import folder_paths
import numpy as np
import torch
import yaml
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from motor import compositor as C  # noqa: E402
from motor import ficha as F  # noqa: E402
from motor import qa  # noqa: E402


def _ficha(caminho):
    alvo = (RAIZ / caminho).resolve()
    if RAIZ not in alvo.parents or alvo.suffix != ".yaml":
        raise ValueError(f"a ficha precisa ser um .yaml dentro de {RAIZ}: {caminho}")
    return F.carregar(alvo)


def _pil(imagem):
    return Image.fromarray(np.clip(imagem[0].cpu().numpy() * 255, 0, 255).astype(np.uint8))


class FichaPrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "ficha": ("STRING", {"default": "fichas/arara/ficha-v1.2.yaml"}),
            "parte": (["cena", "mascote", "entorno", "frente"],),
            "tema": ("STRING", {"default": "instagram"}),
        }}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "montar"
    CATEGORY = "gera-imagem"

    def montar(self, ficha, parte, tema):
        return (F.prompt_da_parte(_ficha(ficha), parte, tema or None),)


class ComporPeca:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "cena": ("IMAGE",),
                "mascote": ("IMAGE",),
                "ficha": ("STRING", {"default": "fichas/arara/ficha-v1.2.yaml"}),
                "formato": (["home", "promo"],),
                "tema": ("STRING", {"default": "instagram"}),
            },
            "optional": {"entorno": ("IMAGE",), "frente": ("IMAGE",)},
        }

    RETURN_TYPES = ()
    FUNCTION = "compor"
    OUTPUT_NODE = True
    CATEGORY = "gera-imagem"

    def compor(self, cena, mascote, ficha, formato, tema, entorno=None, frente=None):
        f = _ficha(ficha)
        partes = {"cena": _pil(cena), "mascote": _pil(mascote)}
        for nome, im in (("entorno", entorno), ("frente", frente)):
            if im is not None:
                partes[nome] = _pil(im)
        faltam = [c["parte"] for c in f["camadas"] if c["tipo"] == "gerada" and c["parte"] not in partes]
        if faltam:
            raise ValueError(f"a ficha {ficha} pede a(s) parte(s) {', '.join(faltam)}: ligue essa(s) entrada(s)")
        cfg = yaml.safe_load((RAIZ / "integracoes/comfyui/config.yaml").read_text(encoding="utf-8"))
        camadas = C.montar(f, formato, partes, F.linhas_de_texto(f, tema or None), cfg.get("recorte"))
        w, h = F.tamanho(f, formato)
        subpasta = f"gera/{f['marca']}"
        nome = f"{formato}-{tema or 'padrao'}-comfyui"
        base = Path(folder_paths.get_output_directory()) / subpasta / nome
        C.salvar(camadas, w, h, base)
        resultados = qa.conferir(f, formato, C.achatar(camadas, w, h), camadas)
        base.with_suffix(".qa.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
        falhas = [r["regra"] for r in resultados if not r["ok"]]
        return {"ui": {
            "images": [{"filename": f"{nome}.png", "subfolder": subpasta, "type": "output"}],
            "text": [f"QA {'ok' if not falhas else 'falhou: ' + ', '.join(falhas)}"],
        }}


NODE_CLASS_MAPPINGS = {"GeraFichaPrompt": FichaPrompt, "GeraComporPeca": ComporPeca}
NODE_DISPLAY_NAME_MAPPINGS = {"GeraFichaPrompt": "Ficha de estilo: prompt", "GeraComporPeca": "Compor peça (PSD)"}
