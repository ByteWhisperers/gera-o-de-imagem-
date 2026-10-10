import json
from pathlib import Path

import numpy as np
from PIL import Image

import tentativa as T
from motor import comfyui as CU
from motor import grafo as G

RAIZ = Path(__file__).resolve().parent.parent
GRAFO = "fichas/arara/grafos/promo-telegram.json"


def _comfyui_falso(monkeypatch):
    """Faz o papel do ComfyUI: devolve, para cada SaveImage, o pedaço da referência que o ramo cobre."""
    from psd_tools import PSDImage  # noqa: F401  (o PSD precisa do psd-tools)

    g = G.carregar(RAIZ / GRAFO)
    ref = Image.open(RAIZ / g["referencia"]).convert("RGB")
    subidas = []

    def executar(url, wf):
        saidas = {}
        for id_, n in wf.items():
            if n["class_type"] != "SaveImage":
                continue
            camada = n["inputs"]["filename_prefix"].rsplit("/", 1)[-1]
            if camada == "cena":
                saidas[id_] = [ref]
                continue
            m = G.mascara_camada(g, camada)
            x, y, w, h = G.caixa_px(m, margem=0.04)
            rgba = ref.convert("RGBA")
            rgba.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
            saidas[id_] = [rgba.crop((x, y, x + w, y + h))]
        return saidas

    monkeypatch.setattr(CU, "object_info", lambda url: {})
    monkeypatch.setattr(T.C, "conferir", lambda wf, info: [])
    monkeypatch.setattr(CU, "enviar_imagem", lambda url, nome, im: subidas.append(nome))
    monkeypatch.setattr(CU, "executar", executar)
    monkeypatch.setattr(CU, "versao", lambda url: "teste")
    return subidas


def test_tentativa_monta_psd_mede_e_anota_no_diario(tmp_path, monkeypatch):
    subidas = _comfyui_falso(monkeypatch)
    linha = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", mudanca="primeira")
    assert len(subidas) == 4                       # 2 placas + 2 máscaras
    assert linha["id"] == "promo-telegram-001" and linha["decisao"] is None and linha["custo_usd"] == 0.0
    # devolvendo a própria referência, cada parte gerada fica igual à da referência
    for camada in ("entorno", "mascote"):
        assert linha["notas"][camada]["dE00"] < 1 and linha["notas"][camada]["cobertura"] > 0.97
    diario = (tmp_path / "fluxos/arara/tentativas.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(diario[-1])["workflow"]["sha256"] == linha["workflow"]["sha256"]
    assert Path(linha["workflow"]["arquivo"]).name.startswith(linha["workflow"]["sha256"][:16])
    # PSD com as 7 camadas da ficha; os efeitos embutidos no fundo entram desligados
    from psd_tools import PSDImage

    psd = PSDImage.open(tmp_path / "saida/arara/tentativas/promo-telegram-001/peca.psd")
    assert [l.name for l in psd] == ["cena", "escurecimento", "entorno", "mascote", "brilho", "texto", "logo"]
    assert {l.name for l in psd if not l.visible} == {"escurecimento", "brilho"}
    assert (tmp_path / "saida/arara/tentativas/promo-telegram-001/prancha.jpg").exists()
    segunda = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", pai=linha["id"])
    assert segunda["id"] == "promo-telegram-002" and segunda["pai"] == "promo-telegram-001"
