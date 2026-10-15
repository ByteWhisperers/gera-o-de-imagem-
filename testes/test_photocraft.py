import json
import os
import shutil

import numpy as np
import pytest
from PIL import Image, ImageFilter

from integracoes.photocraft import acabar as A
from integracoes.photocraft import bordas as B
from integracoes.photocraft import casar_cor as CC
from motor import comparar as CMP
from motor import ficha as F

from test_tentativa import GRAFO, RAIZ, _comfyui_falso

TEM_PHOTOCRAFT = bool(os.environ.get("PHOTOCRAFT_CLI") or shutil.which("photocraft-cli"))
FICHA = F.carregar(RAIZ / "fichas/arara/ficha-v1.2.yaml")


def _imagem(semente=0, h=64, w=64):
    return np.random.default_rng(semente).integers(0, 256, (h, w, 3)).astype(np.uint8)


# ---------------------------------------------------------------- casar cor


def test_curvas_levam_as_cores_da_parte_para_as_da_referencia():
    ref = _imagem()
    atual = (ref.astype(np.float64) * 0.7 + 20).astype(np.uint8)    # mais apagada e lavada
    m = np.ones(ref.shape[:2], bool)
    curvas = CC.curvas_para_casar(atual, m, ref, m)
    casada = CC.aplicar(atual, curvas)
    assert np.abs(casada.astype(float) - ref).mean() < np.abs(atual.astype(float) - ref).mean() / 3


def test_curvas_sao_monotonas_de_0_a_255_e_forca_zero_nao_muda_nada():
    ref, atual = _imagem(1), _imagem(2)
    m = np.ones(ref.shape[:2], bool)
    for forca in (0.0, 0.5, 1.0):
        curvas = CC.curvas_para_casar(atual, m, ref, m, forca=forca)
        for canal in CC.CANAIS:
            p = np.array(curvas[canal])
            assert p[0, 0] == 0 and p[-1, 0] == 255
            assert (np.diff(p[:, 0]) >= 4).all() and (np.diff(p[:, 1]) >= 0).all()
            if forca == 0.0:
                assert np.abs(p[1:-1, 0] - p[1:-1, 1]).max() <= 1


def test_casar_cor_recusa_mascara_vazia():
    with pytest.raises(ValueError):
        CC.curvas_para_casar(_imagem(), np.zeros((64, 64), bool), _imagem(), np.ones((64, 64), bool))


def test_curvas_tem_inclinacao_limitada_mesmo_quando_a_referencia_e_outra_coisa():
    m = np.ones((64, 64), bool)
    atual = np.full((64, 64, 3), 120, np.uint8)
    atual[:, 32:] = 130                                               # quase sem variação
    ref = _imagem(4)                                                  # de 0 a 255
    for canal, pontos in CC.curvas_para_casar(atual, m, ref, m).items():
        p = np.array(pontos, np.float64)
        inclinacoes = np.diff(p[:, 1]) / np.diff(p[:, 0])
        assert inclinacoes.min() >= 0.5 - 0.05 and inclinacoes.max() <= 2.0 + 0.05, canal


def test_curva_de_luz_leva_a_luz_para_a_da_referencia_sem_mexer_na_cor():
    ref = _imagem(5)
    atual = (ref.astype(np.float64) * 0.6 + 30).astype(np.uint8)      # contraste baixo
    m = np.ones(ref.shape[:2], bool)
    p = np.array(CC.curva_de_luz(atual, m, ref, m), np.float64)
    nova = np.interp(CC.luminancia(atual), p[:, 0], p[:, 1])
    assert nova.std() > CC.luminancia(atual).std() * 1.3
    assert abs(nova.std() - CC.luminancia(ref).std()) < abs(CC.luminancia(atual).std() - CC.luminancia(ref).std())


# ---------------------------------------------------------------- perfil e medida


def test_perfil_mostra_a_perda_de_nitidez_e_de_saturacao():
    nitida = Image.fromarray(_imagem(3, 96, 96))
    mole = nitida.filter(ImageFilter.GaussianBlur(2))
    m = np.ones((96, 96), bool)
    a, b = CMP.perfil(np.asarray(nitida), m), CMP.perfil(np.asarray(mole), m)
    assert b["nitidez"] < a["nitidez"] / 2
    cinza = np.asarray(nitida.convert("L").convert("RGB"))
    assert CMP.perfil(cinza, m)["saturacao"] < a["saturacao"] / 5


def test_diagnostico_poe_a_maior_diferenca_primeiro_e_ignora_as_pequenas():
    p = {"mascote": {"peca": {"luz": 50, "contraste": 20, "saturacao": 40, "nitidez": 1.0},
                     "referencia": {"luz": 51, "contraste": 20, "saturacao": 50, "nitidez": 2.0}}}
    d = A.diagnostico(p)
    assert len(d) == 2 and d[0].startswith("mascote: menos nítida") and "menos saturada" in d[1]


def test_camadas_no_final_usam_a_cor_da_peca_e_o_alfa_da_camada():
    final = Image.new("RGB", (10, 10), (200, 10, 10))
    rgba = np.zeros((4, 4, 4), np.uint8)
    rgba[..., 3] = 255
    rgba[0, 0, 3] = 0
    nova, x, y = CMP.camadas_no_final(final, {"mascote": (rgba, 8, 8)})["mascote"]
    assert (x, y) == (8, 8)
    assert tuple(nova[1, 1]) == (200, 10, 10, 255) and nova[0, 0, 3] == 0
    assert tuple(nova[3, 3, :3]) == (0, 0, 0)                     # fora da peça fica vazio


# ---------------------------------------------------------------- receita


def _receita(*passos):
    return {"nome": "teste", "passos": list(passos)}


@pytest.mark.parametrize("passo, trecho", [
    ({"camada": "texto", "comando": "layer.newAdjustmentLayer.curves", "params": {}}, "sai de código"),
    ({"camada": "logo", "comando": "layer.layerStyle.outerGlow", "params": {}}, "sai de código"),
    ({"camada": "mascote", "comando": "layer.layerStyle.clear", "params": {"layer": "logo"}}, "sai de código"),
    ({"camada": "mascote", "comando": "layer.layerStyle.clear", "params": {"layer": 7}}, "pelo nome"),
    ({"camada": "nuvem", "comando": "filter.blur.gaussianBlur"}, "não é camada da ficha"),
    ({"camada": "mascote", "comando": "filter.blur.gaussianBlur", "casar_cor": {}}, "um só"),
    ({"camada": "mascote", "casar_cor": {}, "casar_luz": {}}, "um só"),
    ({"camada": "mascote", "alvo": "texto", "comando": "layer.layerStyle.clear"}, "alvo"),
    ({"camada": "mascote", "comando": "layer.vectorMask.fromPath", "params": {}}, "vetorial"),
    ({"camada": "mascote", "comando": "layer.layerMask.edit", "params": {"feather": 2}}, "difusão"),
    ({"camada": "mascote", "comando": "select.refineEdge", "params": {"decontaminate": True}}, "decontaminate"),
    ({"camada": "mascote", "comando": "image.adjustments.levels", "params": {"layer": "cena"}}, "alvo"),
    ({"camada": "mascote", "comando": "layer.new.layer", "props": {"name": "x"}}, "props"),
    ({"camada": "mascote", "comando": "layer.new.layer", "props": {"opacity": 60}}, "0 a 1"),
    ({"camada": "mascote", "casar_luz": {"inclinacao": [2, 3]}}, "inclinacao"),
])
def test_receita_nao_mexe_no_que_sai_de_codigo_nem_em_camada_desconhecida(passo, trecho):
    with pytest.raises(A.ReceitaInvalida, match=trecho):
        A.conferir_receita(_receita(passo), FICHA)


def test_pilha_acusa_camada_nova_acima_do_texto_e_texto_mudado():
    antes = [{"name": "logo", "id": 9, "opacity": 1.0}, {"name": "texto", "id": 8, "opacity": 1.0},
             {"name": "mascote", "id": 5, "opacity": 1.0}]
    ok = [antes[0], antes[1], {"name": "acabamento mascote 1", "id": 10}, antes[2]]
    assert A.conferir_pilha(FICHA, antes, ok) == []
    acima = [antes[0], {"name": "Curves 1", "id": 10}, antes[1], antes[2]]
    assert "acima" in A.conferir_pilha(FICHA, antes, acima)[0]
    texto_mudado = [antes[0], {**antes[1], "opacity": 0.5, "selected": True}, antes[2]]
    assert "propriedades" in A.conferir_pilha(FICHA, antes, texto_mudado)[0]


def test_receita_que_a_peca_nao_tem_e_recusada_antes_de_medir():
    receita = _receita({"camada": "frente", "comando": "layer.layerStyle.clear"})
    with pytest.raises(A.ReceitaInvalida, match="frente"):
        A.conferir_camadas(receita, {"cena", "entorno", "mascote", "texto", "logo"})


def test_pilha_acusa_parte_escondida_ou_renomeada():
    antes = [{"name": "texto", "id": 8}, {"name": "mascote", "id": 5, "visible": True}]
    escondida = [{"name": "texto", "id": 8}, {"name": "mascote copy", "id": 12, "visible": True},
                 {"name": "mascote", "id": 5, "visible": False}]
    assert "escondida" in A.conferir_pilha(FICHA, antes, escondida)[0]
    trocada = [{"name": "texto", "id": 8}, {"name": "mascote", "id": 12, "visible": True}]   # id novo, mesmo nome
    assert A.conferir_pilha(FICHA, antes, trocada) == []


def test_estouro_acha_o_contorno_claro_da_nitidez_so_na_borda():
    antes = np.zeros((60, 60, 4), np.uint8)
    antes[10:50, 10:50] = (90, 90, 90, 255)
    depois = antes.copy()
    depois[10:12, 10:50, :3] = 200                                     # contorno branco em cima
    e = B.estouro(antes, depois)
    assert e["borda_%"] > 10 and e["dentro_%"] == 0
    assert B.estouro(antes, antes) == {"borda_%": 0.0, "dentro_%": 0.0}


def test_diagnostico_junta_perfil_e_bordas_com_a_area_de_cada_frase():
    p = {"mascote": {"peca": {"luz": 50, "contraste": 20, "saturacao": 50, "nitidez": 1.0},
                     "referencia": {"luz": 50, "contraste": 20, "saturacao": 50, "nitidez": 2.0}}}
    b = {"mascote": {"recorte": {"franja": -14.0, "semi_%": 13.4, "ilhas": 36, "borda_opaca": 0.0, "quadro_%": 15.0},
                     "contorno": {"peca": {"brilho_fora": -3.4, "luz_borda": 1.8},
                                  "referencia": {"brilho_fora": 5.3, "luz_borda": 6.6}}},
         "frente": {"recorte": {"franja": 0.0, "semi_%": 0.0, "ilhas": 0, "borda_opaca": 0.0, "quadro_%": 100.0}}}
    d = A.diagnostico(p, b)
    assert d[0].startswith("frente: cobre 100%")
    texto = "\n".join(d)
    for trecho in ("(retoque)", "franja escura", "névoa", "36 pedacinhos", "menos brilho em volta", "(luz)"):
        assert trecho in texto


# ---------------------------------------------------------------- com o PhotoCraft


@pytest.mark.skipif(not TEM_PHOTOCRAFT, reason="photocraft-cli não instalado")
def test_acabamento_aplica_a_receita_mede_e_anota_sem_mexer_no_texto(tmp_path, monkeypatch):
    import tentativa as T

    _comfyui_falso(monkeypatch)
    tentativa = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    psd = RAIZ / tentativa["arquivos"]["psd"] if not tentativa["arquivos"]["psd"].startswith("/") \
        else tentativa["arquivos"]["psd"]
    receita = tmp_path / "receita.json"
    receita.write_text(json.dumps(_receita(
        {"camada": "mascote", "comando": "layer.newAdjustmentLayer.curves",
         "params": {"points": [[0, 0], [128, 90], [255, 255]]}, "prender": True, "nome": "acabamento mascote mais escuro"},
        {"camada": "entorno", "casar_cor": {"forca": 1.0}},
    )), encoding="utf-8")
    linha = A.aplicar(psd, receita, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos", mudanca="teste")
    assert linha["id"] == "promo-telegram-ac001" and linha["decisao"] is None and linha["custo_usd"] == 0.0
    assert linha["origem"]["id"] == tentativa["id"]                 # o grafo veio do diário da tentativa
    # a peça falsa é a própria referência: escurecer o mascote afasta, casar a cor do entorno não
    assert linha["notas"]["mascote"]["dE00"] > linha["notas_antes"]["mascote"]["dE00"] + 3
    assert linha["notas"]["entorno"]["dE00"] < 1.5
    assert linha["perfis"]["mascote"]["peca"]["luz"] < linha["perfis_antes"]["mascote"]["peca"]["luz"]
    from psd_tools import PSDImage

    psd_final = PSDImage.open(linha["arquivos"]["psd"] if linha["arquivos"]["psd"].startswith("/")
                              else RAIZ / linha["arquivos"]["psd"])
    nomes = [l.name for l in psd_final]
    assert nomes.index("acabamento mascote mais escuro") == nomes.index("mascote") + 1
    assert nomes[-2:] == ["texto", "logo"]
    ajuste = next(l for l in psd_final if l.name == "acabamento mascote mais escuro")
    assert ajuste.clipping
    diario = (tmp_path / "fluxos/arara/acabamentos.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(diario[-1])["receita"]["sha256"] == linha["receita"]["sha256"]


@pytest.mark.skipif(not TEM_PHOTOCRAFT, reason="photocraft-cli não instalado")
def test_acabamento_recusa_ajuste_acima_do_texto(tmp_path, monkeypatch):
    import tentativa as T

    _comfyui_falso(monkeypatch)
    tentativa = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    receita = tmp_path / "receita.json"
    # selecionar o mascote e mandar o ajuste para o topo da pilha põe o ajuste acima do texto
    receita.write_text(json.dumps(_receita(
        {"camada": "mascote", "comando": "layer.newAdjustmentLayer.hueSaturation", "params": {"saturation": 40}},
        {"camada": "mascote", "comando": "layer.arrange.bringToFront", "params": {}},
    )), encoding="utf-8")
    with pytest.raises(RuntimeError, match="acima"):
        A.aplicar(tentativa["arquivos"]["psd"], receita, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    assert not (tmp_path / "fluxos/arara/acabamentos.jsonl").exists()


@pytest.mark.skipif(not TEM_PHOTOCRAFT, reason="photocraft-cli não instalado")
def test_receita_com_objeto_inteligente_alvo_props_e_passos_medidos(tmp_path, monkeypatch):
    import tentativa as T
    from psd_tools import PSDImage

    _comfyui_falso(monkeypatch)
    tentativa = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    receita = tmp_path / "receita.json"
    receita.write_text(json.dumps(_receita(
        {"camada": "mascote", "comando": "layer.smartObjects.convertToSmartObject", "params": {}},
        {"camada": "mascote", "comando": "select.loadSelection", "params": {"channel": "transparency", "layer": "mascote"}},
        {"camada": "mascote", "comando": "select.modify.contract", "params": {"radius": 3}},
        {"camada": "mascote", "comando": "filter.sharpen.unsharpMask", "params": {"amount": 80, "radius": 1.0, "threshold": 3}},
        {"camada": "mascote", "comando": "select.deselect", "params": {}},
        {"camada": "mascote", "comando": "select.deselect", "params": {}},          # sem seleção: pulado
        {"camada": "mascote", "casar_luz": {"forca": 1.0}},
        {"camada": "entorno", "mascara_do_grafo": {}},
        {"camada": "entorno", "comando": "layer.duplicate", "params": {}, "nome": "entorno brilho",
         "props": {"blend": "Screen", "opacity": 0.3}},
        {"camada": "entorno", "alvo": "entorno brilho", "comando": "filter.blur.gaussianBlur", "params": {"radius": 4}},
    )), encoding="utf-8")
    linha = A.aplicar(tentativa["arquivos"]["psd"], receita, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    passos = linha["passos"]
    assert passos[0]["camadas_novas"] == 0 and passos[0]["mesma_camada_id_novo"] == ["mascote"]
    assert passos[1]["params"]["layer"] == "mascote"                              # o diário guarda o nome
    assert passos[5].get("pulado") == "sem seleção"
    assert passos[6]["comando"] == "layer.newAdjustmentLayer.curves" and "points" in passos[6]["params"]
    assert passos[7]["comando"] == "mascara_do_grafo" and passos[9]["alvo"] == "entorno brilho"
    psd = PSDImage.open(linha["arquivos"]["psd"])
    por_nome = {l.name: l for l in psd}
    assert por_nome["mascote"].kind == "smartobject"
    luz = por_nome["acabamento mascote luz por medida"]
    assert luz.clipping and "LUMINOSITY" in str(luz.blend_mode)
    brilho = por_nome["entorno brilho"]
    assert "SCREEN" in str(brilho.blend_mode) and abs(brilho.opacity - 77) <= 1
    assert por_nome["entorno"].mask is not None
    assert set(linha["bordas"]) == {"entorno", "mascote"}
    assert "estouro" in linha["bordas"]["mascote"] and "recorte" in linha["bordas"]["mascote"]
    assert linha["notas"]["peca"]["dE00"] < 3                                     # a peça falsa é a referência


@pytest.mark.skipif(not TEM_PHOTOCRAFT, reason="photocraft-cli não instalado")
def test_acabamento_para_quando_o_psd_nao_guarda_o_filtro(tmp_path, monkeypatch):
    import tentativa as T

    _comfyui_falso(monkeypatch)
    tentativa = T.rodar(GRAFO, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    receita = tmp_path / "receita.json"
    receita.write_text(json.dumps(_receita(
        {"camada": "mascote", "comando": "layer.smartObjects.convertToSmartObject", "params": {}},
        {"camada": "mascote", "comando": "filter.sharpen.smartSharpen", "params": {"amount": 120, "radius": 1.2}},
    )), encoding="utf-8")
    with pytest.raises(RuntimeError, match="não guarda"):
        A.aplicar(tentativa["arquivos"]["psd"], receita, saida=tmp_path / "saida", fluxos=tmp_path / "fluxos")
    assert not (tmp_path / "fluxos/arara/acabamentos.jsonl").exists()
