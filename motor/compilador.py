"""Compilador: grafo da peça + ficha + tema -> workflow do ComfyUI (formato API).

É aqui que "os dados da desconstrução viram instruções de geração". Cada
camada do PSD que a IA gera vira um ramo do workflow, montado a partir dos
nós do grafo que caem nela:

  caixa      -> ImageCrop: o ramo trabalha só na região da parte na referência
  mascara    -> LoadImageMask + CropMask + JoinImageWithAlpha: a parte sai recortada
  tipo       -> quanto a parte pode mudar (denoise do config): fundo pouco, figura mais
  tema       -> o prompt (figurino, o que o mascote segura, o entorno), pela ficha
  z          -> a ordem das camadas no PSD

Texto e logo nunca viram ramo: saem de código (motor/texto.py). As placas da
desconstrução já chegam sem eles, então a IA não tem como desenhar letras ali.

O mesmo grafo sempre dá o mesmo workflow (mesma ordem, mesmos nomes de
arquivo, que são o hash do conteúdo). Isso permite guardar cada workflow
pelo sha256 e saber exatamente o que gerou cada tentativa.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from . import ficha as F
from . import grafo as G

RAIZ = Path(__file__).resolve().parent.parent

CLASSE = {"fundo": "fundo", "personagem": "personagem", "objeto_segurado": "personagem", "acessorio": "personagem",
          "objeto": "objeto", "objeto_grupo": "objeto"}


@dataclass
class Compilado:
    workflow: dict
    entradas: dict[str, Image.Image]                 # nome no ComfyUI -> imagem que precisa subir antes
    saidas: dict[str, dict]                          # camada -> {"no": id do SaveImage, "x", "y", "w", "h"}
    parametros: dict = field(default_factory=dict)

    def json(self) -> str:
        return json.dumps(self.workflow, ensure_ascii=False, indent=1, sort_keys=True) + "\n"

    def sha256(self) -> str:
        return hashlib.sha256(self.json().encode()).hexdigest()


class _Montador:
    def __init__(self) -> None:
        self.nos: dict[str, dict] = {}

    def add(self, classe: str, **entradas) -> str:
        id_ = str(len(self.nos) + 1)
        self.nos[id_] = {"class_type": classe, "inputs": entradas}
        return id_


def ler_config(raiz: Path = RAIZ) -> dict:
    return yaml.safe_load((raiz / "integracoes/comfyui/config.yaml").read_text(encoding="utf-8"))


def nome_entrada(rotulo: str, imagem: Image.Image) -> str:
    """Nome do arquivo no ComfyUI a partir do conteúdo: mesma imagem, mesmo nome."""
    h = hashlib.sha256(f"{imagem.mode}{imagem.size}".encode() + imagem.tobytes()).hexdigest()[:12]
    return f"gera_{rotulo}_{h}.png"


def tamanho_geracao(largura: int, altura: int, lado: int) -> tuple[int, int]:
    """Tamanho de geração com o lado maior = `lado`, proporção mantida, múltiplos de 64."""
    escala = lado / max(largura, altura)
    return (max(64, round(largura * escala / 64) * 64), max(64, round(altura * escala / 64) * 64))


def prompt_no_lugar(ficha: dict, parte: str, tema: str, cfg: dict) -> str:
    """Prompt da ficha para refazer a parte no lugar dela (sem o pedido de fundo de estúdio)."""
    p = F.prompt_da_parte(ficha, parte, tema)
    for trecho in cfg["compilador"].get("tirar_do_prompt", []):
        p = p.replace(trecho, "")
    return p


def _base(m: _Montador, cfg: dict) -> tuple[str, str]:
    ck = m.add("CheckpointLoaderSimple", ckpt_name=cfg["checkpoint"])
    neg = m.add("CLIPTextEncode", clip=[ck, 1], text=cfg["negativo"])
    return ck, neg


def _amostrar(m: _Montador, cfg: dict, ck: str, neg: str, latente: list, prompt: str, semente: int,
              denoise: float) -> str:
    comp = cfg["compilador"]
    pos = m.add("CLIPTextEncode", clip=[ck, 1], text=prompt)
    ks = m.add("KSampler", model=[ck, 0], positive=[pos, 0], negative=[neg, 0], latent_image=latente,
               seed=semente, steps=cfg["passos"], cfg=cfg["cfg"], sampler_name=comp["sampler"],
               scheduler=comp["scheduler"], denoise=denoise)
    return m.add("VAEDecode", samples=[ks, 0], vae=[ck, 2])


def _placa(grafo: dict, nome: str) -> Image.Image:
    if nome not in grafo.get("placas", {}):
        raise G.GrafoInvalido(f"o grafo {grafo.get('peca')} não tem a placa '{nome}': rode a desconstrução com --placas")
    return Image.open(G.pasta(grafo) / grafo["placas"][nome]).convert("RGB")


def classe_da_camada(grafo: dict, camada: str) -> str:
    nos = sorted((n for n in grafo["nos"] if n.get("camada_psd") == camada and "mascara" in n
                  and n["tipo"] in G.GERAVEIS), key=lambda n: n.get("z", 0))
    return CLASSE[nos[0]["tipo"]]


def compilar(grafo: dict, ficha: dict, cfg: dict, tema: str | None = None, semente: int = 519,
             denoise: dict | None = None) -> Compilado:
    """Workflow que refaz as camadas geradas da peça, cada uma na sua região da referência."""
    tema = tema or grafo["tema"]
    comp = cfg["compilador"]
    forca = {**comp["denoise"], **(denoise or {})}
    W, H = grafo["tamanho_px"]
    m = _Montador()
    ck, neg = _base(m, cfg)
    entradas: dict[str, Image.Image] = {}
    saidas: dict[str, dict] = {}
    carregadas: dict[str, str] = {}

    def carregar(rotulo: str, imagem: Image.Image) -> str:
        nome = nome_entrada(rotulo, imagem)
        if nome not in carregadas:
            entradas[nome] = imagem
            carregadas[nome] = m.add("LoadImage", image=nome)
        return carregadas[nome]

    for camada in G.camadas_geradas(grafo):
        if camada not in ficha["partes"]:
            raise G.GrafoInvalido(f"a camada '{camada}' do grafo não é uma parte da ficha {ficha['versao']}")
        classe = classe_da_camada(grafo, camada)
        prompt = prompt_no_lugar(ficha, camada, tema, cfg)
        if classe == "fundo":
            img = carregar("cena_limpa", _placa(grafo, "cena_limpa"))
            x, y, w, h = 0, 0, W, H
            fonte = [img, 0]
        else:
            img = carregar("sem_texto", _placa(grafo, "sem_texto"))
            mascara = G.mascara_camada(grafo, camada)
            x, y, w, h = G.caixa_px(mascara, margem=comp["margem"])
            fonte = [m.add("ImageCrop", image=[img, 0], width=w, height=h, x=x, y=y), 0]
        gw, gh = tamanho_geracao(w, h, comp["lado"][classe])
        menor = m.add("ImageScale", image=fonte, upscale_method="lanczos", width=gw, height=gh, crop="disabled")
        lat = m.add("VAEEncode", pixels=[menor, 0], vae=[ck, 2])
        dec = _amostrar(m, cfg, ck, neg, [lat, 0], prompt, semente, forca[classe])
        volta = m.add("ImageScale", image=[dec, 0], upscale_method="lanczos", width=w, height=h, crop="disabled")
        if classe != "fundo":
            pixels = Image.fromarray((mascara * 255).astype(np.uint8))
            mk = m.add("LoadImageMask", image=nome_entrada(f"mascara_{camada}", pixels), channel="red")
            entradas[nome_entrada(f"mascara_{camada}", pixels)] = pixels
            corte = m.add("CropMask", mask=[mk, 0], x=x, y=y, width=w, height=h)
            alfa = m.add("InvertMask", mask=[corte, 0])          # JoinImageWithAlpha usa 1 - máscara
            volta = m.add("JoinImageWithAlpha", image=[volta, 0], alpha=[alfa, 0])
        salvar = m.add("SaveImage", images=[volta, 0], filename_prefix=f"gera/{grafo['peca']}/{camada}")
        saidas[camada] = {"no": salvar, "x": x, "y": y, "w": w, "h": h, "classe": classe,
                          "geracao": [gw, gh], "denoise": forca[classe], "prompt": prompt}
    parametros = {"tema": tema, "semente": semente, "denoise": forca, "passos": cfg["passos"], "cfg": cfg["cfg"],
                  "modelo": cfg["checkpoint"], "lado": comp["lado"], "margem": comp["margem"]}
    return Compilado(m.nos, entradas, saidas, parametros)


def compilar_placa(ficha: dict, grafo: dict, cfg: dict, preenchida: Image.Image, mascara: Image.Image,
                   semente: int = 7, prefixo: str = "gera/placa") -> Compilado:
    """Workflow de inpainting que apaga a região branca da máscara e devolve a peça inteira.

    `preenchida` já chega com o buraco pré-preenchido pelas cores de volta; fora do
    buraco os pixels da referência voltam intactos (ImageCompositeMasked).
    """
    W, H = grafo["tamanho_px"]
    comp = cfg["compilador"]
    m = _Montador()
    ck, neg = _base(m, cfg)
    nome_img, nome_mk = nome_entrada("preenchida", preenchida), nome_entrada("buraco", mascara)
    img = m.add("LoadImage", image=nome_img)
    mk = m.add("LoadImageMask", image=nome_mk, channel="red")
    gw, gh = tamanho_geracao(W, H, comp["lado"]["fundo"])
    menor = m.add("ImageScale", image=[img, 0], upscale_method="lanczos", width=gw, height=gh, crop="disabled")
    lat = m.add("VAEEncode", pixels=[menor, 0], vae=[ck, 2])
    lat = m.add("SetLatentNoiseMask", samples=[lat, 0], mask=[mk, 0])
    dec = _amostrar(m, cfg, ck, neg, [lat, 0], prompt_no_lugar(ficha, "cena", grafo["tema"], cfg), semente,
                    comp["denoise_placa"])
    volta = m.add("ImageScale", image=[dec, 0], upscale_method="lanczos", width=W, height=H, crop="disabled")
    junta = m.add("ImageCompositeMasked", destination=[img, 0], source=[volta, 0], x=0, y=0, resize_source=False,
                  mask=[mk, 0])
    salvar = m.add("SaveImage", images=[junta, 0], filename_prefix=prefixo)
    return Compilado(m.nos, {nome_img: preenchida, nome_mk: mascara}, {"placa": {"no": salvar}},
                     {"semente": semente, "denoise": comp["denoise_placa"]})


def conferir(workflow: dict, info: dict) -> list[str]:
    """Confere o workflow contra o /object_info do ComfyUI: nó que não existe, entrada que
    falta, valor fora da lista (um modelo que não está instalado) e nó pago (API externa)."""
    problemas = []
    for id_, no in workflow.items():
        classe = no["class_type"]
        if classe not in info:
            problemas.append(f"nó {id_}: '{classe}' não existe neste ComfyUI")
            continue
        definicao = info[classe]
        if definicao.get("api_node"):
            problemas.append(f"nó {id_}: '{classe}' é pago (API externa)")
        for nome, spec in definicao.get("input", {}).get("required", {}).items():
            if nome not in no["inputs"]:
                problemas.append(f"nó {id_} ({classe}): falta a entrada '{nome}'")
                continue
            valor = no["inputs"][nome]
            opcoes = spec[0] if spec and isinstance(spec[0], list) else None
            if opcoes is not None and not isinstance(valor, list) and classe not in ("LoadImage", "LoadImageMask") \
                    and valor not in opcoes:
                problemas.append(f"nó {id_} ({classe}): '{valor}' não está entre as opções de '{nome}'")
        for nome, valor in no["inputs"].items():
            if isinstance(valor, list) and valor and str(valor[0]) not in workflow:
                problemas.append(f"nó {id_} ({classe}): a entrada '{nome}' liga num nó que não existe ({valor[0]})")
    return problemas
