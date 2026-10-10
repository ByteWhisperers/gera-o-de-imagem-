import numpy as np
import pytest

pytest.importorskip("skimage")

from ferramentas import desconstruir as D  # noqa: E402


def test_contorno_aproximado_encaixa_na_borda_real():
    yy, xx = np.mgrid[:200, :300]
    disco = ((xx - 150) ** 2 + (yy - 100) ** 2) < 60 ** 2
    rgb = np.where(disco[..., None], [220, 40, 20], [20, 60, 30]).astype(np.float32)
    rgb += np.random.default_rng(1).normal(0, 6, rgb.shape)
    # contorno do agente: 4 px maior que o disco, como um contorno feito a olho
    aproximada = D.mascara_elipse([86 / 300, 36 / 200, 128 / 300, 128 / 200], 300, 200)
    encaixada = D.encaixar_na_borda(rgb.clip(0, 255), aproximada)
    iou = (encaixada & disco).sum() / (encaixada | disco).sum()
    assert iou > 0.95
    assert (aproximada & disco).sum() / (aproximada | disco).sum() < iou


def test_buraco_e_preenchido_com_as_cores_de_volta():
    rgb = np.zeros((80, 120, 3), np.float32)
    rgb[:] = [30, 90, 40]
    rgb[30:50, 40:80] = [255, 255, 255]                                     # "texto" branco
    buraco = np.zeros((80, 120), bool)
    buraco[28:52, 38:82] = True
    cheio = D.preencher_buraco(rgb, buraco, reducao=2)
    assert np.abs(cheio[buraco] - [30, 90, 40]).max() < 12
    assert (cheio[~buraco] == rgb[~buraco]).all()


def _faixa_de_texto(caixas):
    """Fundo verde com retângulos brancos de contorno preto, como letras grossas."""
    rgb = np.zeros((200, 400, 3), np.float32)
    rgb[:] = [30, 90, 40]
    for x0, y0, x1, y1 in caixas:
        rgb[y0 - 3 : y1 + 3, x0 - 3 : x1 + 3] = [10, 10, 10]
        rgb[y0:y1, x0:x1] = [255, 255, 255]
    return rgb


def test_caixas_de_linha_do_agente_viram_linhas_apertadas_nas_letras():
    rgb = _faixa_de_texto([(40, 40, 120, 70), (140, 40, 220, 70), (40, 100, 300, 150)])
    nada = np.zeros(rgb.shape[:2], bool)
    _, auto = D.medir_texto(rgb, [0, 0, 1, 1], nada)
    # a projeção junta as duas palavras da primeira linha; com caixas, o agente separa
    _, marcadas = D.medir_texto(rgb, [0, 0, 1, 1], nada,
                                [[0.08, 0.15, 0.25, 0.25], [0.33, 0.15, 0.25, 0.25], [0.08, 0.45, 0.75, 0.35]])
    assert len(auto) == 2 and len(marcadas) == 3
    assert marcadas[0]["caixa_px"] == [40, 40, 80, 30]
    assert marcadas[2]["altura_px"] == 50 and marcadas[2]["peso_rel"] == round(50 / 30, 2)


def test_rotulo_solto_pega_so_as_letras_claras_dentro_da_caixa():
    rgb = np.zeros((100, 200, 3), np.float32)
    rgb[:] = [20, 70, 30]
    rgb[40:60, 60:140] = [20, 110, 40]                     # plaquinha verde
    rgb[45:55, 70:130] = [250, 250, 250]                   # "letras"
    rgb[5:15, 5:30] = [250, 250, 250]                      # algo claro fora da caixa
    m, info = D.medir_rotulo(rgb, [0.28, 0.38, 0.45, 0.25], np.zeros((100, 200), bool))
    assert m[46:54, 71:129].all() and not m[5:15, 5:30].any()    # a abertura só arredonda os cantos
    assert info["altura_px"] == 10 and info["estilo_ficha"] == "branco"


def test_cena_limpa_nao_apaga_camada_que_a_ficha_nao_conhece():
    H, W = 120, 200
    vazio = np.zeros((H, W), bool)
    mascote, frente = vazio.copy(), vazio.copy()
    mascote[20:80, 100:160] = True
    frente[80:110, 90:170] = True                          # folhagem na frente, encostada no mascote
    mascaras = {"mascote": mascote, "frente": frente, "texto": vazio, "logo": vazio}
    b = D.buracos({"tamanho_px": [W, H]}, mascaras, [], partes={"cena", "mascote", "entorno"})
    assert b["cena_limpa"][mascote].all()
    assert not (b["cena_limpa"] & frente).any()            # nem a folga do mascote come a folhagem
    assert D.buracos({"tamanho_px": [W, H]}, mascaras, [])["cena_limpa"][frente].all()


def test_prancha_cabe_todas_as_partes_numa_linha():
    from PIL import Image

    im = Image.new("RGB", (1867, 842), (30, 90, 40))
    pecas = {f"parte{i}": Image.new("RGBA", (900, 400), (200, 50, 50, 255)) for i in range(5)}
    p = D.prancha(im, {"mascote": np.zeros((842, 1867), bool)}, pecas, {})
    assert p.width == 1600 and p.height < 1600 * 842 / 1867 + 340


def test_grade_desenha_marcacao_no_zoom():
    from PIL import Image

    from ferramentas import grade as GR

    im = Image.new("RGB", (400, 200), (30, 90, 40))
    mc = {"zona_texto": [0, 0.2, 0.5, 0.6], "nos": {"m": {"contorno": [[0.6, 0.2], [0.9, 0.2], [0.8, 0.9]]},
                                                       "c": {"elipses": [[0.1, 0.1, 0.1, 0.2]]}}}
    tela = GR.grade(im, (0.5, 0, 0.5, 1), largura=800, marcacao=mc)
    so_grade = GR.grade(im, (0.5, 0, 0.5, 1), largura=800)
    assert tela.size == (800, 800)
    diferente = np.abs(np.asarray(tela, int) - np.asarray(so_grade, int)).sum(2) > 0
    assert diferente[:, 150:].any()                        # o contorno "m" aparece no zoom


def test_letra_grande_sai_inteira_e_o_miolo_do_o_continua_vazado():
    H, W = 120, 400
    rgb = np.zeros((H, W, 3), np.float32)
    rgb[:] = [20, 50, 25]                                  # fundo escuro
    yy, xx = np.mgrid[:H, :W]
    # uma barra dourada grossa com contorno escuro: o limiar só pega a borda dela
    rgb[16:104, 16:84] = [15, 10, 5]
    rgb[20:100, 20:80] = [250, 215, 30]
    rgb[60:100, 20:80] = [205, 125, 15]                   # parte de baixo laranja escura (fora do limiar)
    # um "O": anel dourado com contorno, miolo de fundo
    r = np.hypot(xx - 130, yy - 60)                        # colado na barra: mesma palavra
    rgb[(r < 44)] = [15, 10, 5]
    rgb[(r < 40) & (r > 18)] = [250, 215, 30]
    rgb[(r <= 18)] = [15, 10, 5]
    rgb[(r < 14)] = [20, 50, 25]
    letras, linhas = D.medir_texto(rgb, [0, 0, 1, 1], np.zeros((H, W), bool))
    assert len(linhas) == 1
    assert letras[24:96, 24:76].mean() > 0.97              # a barra inteira, inclusive a base laranja
    assert not letras[(r < 12)].any()                      # o miolo do O é fundo
    assert letras[(r < 37) & (r > 21)].mean() > 0.97
    assert linhas[0]["fracao_dourada"] == 1.0
