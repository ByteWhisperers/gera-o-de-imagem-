"""O que entrou para a ficha CAPIVARA362 no padrão da 9pmbet: letras chapadas sem
contorno, preto chapado à esquerda e referências menores que a peça final."""

import numpy as np
import pytest

import tentativa as T
from motor import compositor as M
from motor import ficha as F
from motor import grafo as G

FICHA = "fichas/capivara362/ficha-v1.0.yaml"


def test_ficha_carrega_e_todo_tema_monta_os_prompts():
    f = F.carregar(FICHA)
    for tema in f["temas"]:
        for parte in ("mascote", "entorno", "frente"):
            assert "capybara" in F.prompt_da_parte(f, "mascote", tema)
            F.prompt_da_parte(f, parte, tema)


def test_escurecimento_cheio_ate_e_depois_some():
    cfg = {"cor": "#000000", "opacidade_inicio": 1.0, "cheio_ate": 0.2, "fim_x": 0.5}
    alfa = np.asarray(M.escurecimento(cfg, 100, 4))[0, :, 3]
    assert (alfa[:20] == 255).all() and alfa[30] < 255 and (alfa[50:] == 0).all()
    sem = np.asarray(M.escurecimento({**cfg, "cheio_ate": 0.0}, 100, 4))[0, :, 3]
    assert sem[10] < alfa[10]                      # sem a chave, cai desde a borda (fichas antigas)


def test_tentativa_monta_no_tamanho_da_referencia():
    grafo = G.carregar("fichas/capivara362/grafos/promo-vip.json")
    efetiva = T.ficha_no_lugar(F.carregar(FICHA), grafo)
    assert F.tamanho(efetiva, "promo") == (710, 320)
    assert F.tamanho(F.carregar(FICHA), "promo") == (1420, 640)    # a ficha não muda


def test_letras_chapadas_sem_contorno_sobre_fundo_amarelo():
    pytest.importorskip("skimage")
    from ferramentas import desconstruir as D

    rgb = np.zeros((120, 300, 3), np.float32)
    rgb[:, :150] = [10, 5, 5]                      # esquerda preta
    rgb[:, 150:] = [250, 200, 60]                  # fogo amarelo-alaranjado
    rgb[40:70, 30:270] = [254, 247, 12]            # "letra" amarela chapada que passa para o fogo
    nada = np.zeros((120, 300), bool)
    _, com_contorno = D.medir_texto(rgb, [0.0, 0.2, 1.0, 0.6], nada, [[0.05, 0.3, 0.9, 0.3]])
    letras, linhas = D.medir_texto(rgb, [0.0, 0.2, 1.0, 0.6], nada, [[0.05, 0.3, 0.9, 0.3]], sem_contorno=True)
    assert letras[55, 260] and not letras[100, 260]           # pega a letra no fogo, não o fogo
    assert linhas[0]["caixa_px"][2] > com_contorno[0]["caixa_px"][2]
