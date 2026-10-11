"""Acabamento no PhotoCraft: aplica uma receita de edição a um PSD e mede antes e depois.

A receita é uma lista de comandos do PhotoCraft (os ids do catálogo,
`.claude/skills/photocraft/referencia/catalogo.md`), cada um ligado a uma camada da
ficha pelo nome. O acabamento é não destrutivo sempre que dá: camadas de ajuste
presas à parte, estilos de camada, máscaras, filtros inteligentes. Texto e logo saem
de código e a receita não mexe neles (o script confere pixel a pixel).

Uso:
    python integracoes/photocraft/acabar.py medir saida/arara/tentativas/promo-deposito-001/peca.psd
    python integracoes/photocraft/acabar.py curvas saida/arara/tentativas/promo-deposito-001/peca.psd --camada mascote
    python integracoes/photocraft/acabar.py aplicar saida/arara/tentativas/promo-deposito-001/peca.psd \\
        --receita integracoes/photocraft/receitas/arara/nitidez-loop.json --mudanca "nitidez com máscara de filtro"

O grafo da peça vem do diário (tentativas.jsonl ou acabamentos.jsonl da marca) ou de --grafo.

Cada `aplicar` grava em saida/<marca>/acabamentos/<id>/ o PSD, o PNG, o WebP e a
prancha antes x depois, guarda a receita em fluxos/<marca>/receitas/<sha256>.json e
acrescenta uma linha em fluxos/<marca>/acabamentos.jsonl com "decisao": null. Custo zero.

Formato da receita (JSON):
    {"nome": "...", "descricao": "...",
     "passos": [
        {"camada": "mascote", "casar_luz": {"forca": 1.0}},
        {"camada": "mascote", "comando": "layer.newAdjustmentLayer.vibrance", "params": {"vibrance": 12},
         "prender": true, "nome": "acabamento mascote vibração", "props": {"opacity": 0.6}},
        {"camada": "cena", "comando": "layer.duplicate", "nome": "raios de luz", "props": {"blend": "Screen"}},
        {"camada": "cena", "alvo": "raios de luz", "comando": "filter.blur.radialBlur", "params": {"amount": 80}},
        {"camada": "frente", "mascara_do_grafo": {}}]}

Em cada passo:
- `camada`: a camada da ficha a que o passo pertence; o passo a seleciona antes de rodar;
- `alvo`: outra camada (pelo nome) para selecionar no lugar dela, por exemplo uma criada
  num passo anterior; os comandos que agem na camada ativa (`image.adjustments.*`,
  `edit.fill`, `paint.gradient`...) caem nela;
- `prender`: a camada nova que o comando criar fica presa à camada (máscara de corte);
- `nome`: nome da camada nova (sem ele, "acabamento <camada> <n>");
- `props`: propriedades da camada nova (`blend`, `opacity` de 0 a 1, `visible`...), pelo
  `layer.setProps`: o PhotoCraft ignora modo e opacidade no comando que cria a camada;
- em `params`, "layer": "<nome>" vira o id da camada com esse nome (a de cima que está visível).

Passos medidos (no lugar de `comando`):
- `casar_cor` {"forca", "inclinacao"}: Curvas por canal calculadas contra a mesma parte na
  referência, presa à parte (integracoes/photocraft/casar_cor.py);
- `casar_luz` {"forca", "inclinacao"}: uma Curvas só de luz, em modo Luminosidade, presa à
  parte: acerta claro e escuro sem mexer na cor;
- `selecao_do_grafo` {}: a seleção vira o contorno da parte desenhado no grafo (só quando a
  camada está no lugar da referência, como nas tentativas do loop);
- `mascara_do_grafo` {}: o mesmo, gravado como máscara da camada (troca a que houver).

Comando que troca o id da camada (converter em objeto inteligente) não cria camada nova:
a parte segue com o nome dela. Um `select.deselect` sem seleção é pulado.

O script recusa o que já se sabe que dá errado (ver `RECUSADOS` e `SO_NA_ATIVA`) e
para, sem anotar nada, quando: a peça não tem uma camada da receita; um passo põe
camada acima do texto ou do logo; uma parte some ou fica escondida; o PSD salvo
perde alguma coisa (aviso do `doc.save`, como filtro inteligente sem par no PSD).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from integracoes.photocraft import bordas as B  # noqa: E402
from integracoes.photocraft import casar_cor as CC  # noqa: E402
from integracoes.photocraft.sessao import ErroPhotoCraft, Sessao, versao  # noqa: E402
from motor import comparar as CMP  # noqa: E402
from motor import ficha as F  # noqa: E402
from motor import grafo as G  # noqa: E402

TIPOS_PROTEGIDOS = {"texto", "arquivo"}     # saem de código: o acabamento não toca
TIPOS_QUE_COBREM = {"gerada", "texto", "arquivo"}
MEDIDOS = ("casar_cor", "casar_luz", "selecao_do_grafo", "mascara_do_grafo")

# o que já se sabe que dá errado, com o caminho certo
RECUSADOS = {
    "layer.vectorMask.": "máscara vetorial: o PhotoCraft desenha, mas a medida (psd-tools) não vê; faça a máscara "
                         "pela seleção (select.* e layer.layerMask.revealSelection)",
    "layer.smartObjects.updateModifiedContent": "desligado na automação",
    "file.": "comandos de arquivo são desligados na automação; use mascara_do_grafo ou selecao_do_grafo",
}
SO_NA_ATIVA = ("image.adjustments.", "edit.fill", "paint.gradient", "layer.layerMask.enabled", "layer.layerMask.apply")
PERMITIDOS_VETOR = {"layer.vectorMask.delete"}


class ReceitaInvalida(ValueError):
    pass


def _rel(caminho: Path) -> str:
    caminho = Path(caminho).resolve()
    return caminho.relative_to(RAIZ).as_posix() if caminho.is_relative_to(RAIZ) else caminho.as_posix()


# ---------------------------------------------------------------- de onde veio o PSD


def origem_do_psd(psd: Path, fluxos: Path = RAIZ / "fluxos") -> dict | None:
    """A linha do diário (tentativa ou acabamento) que gravou este PSD, com a marca."""
    alvo = _rel(psd)
    for diario in sorted(Path(fluxos).glob("*/*.jsonl")):
        for linha in diario.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            l = json.loads(linha)
            if l.get("arquivos", {}).get("psd") == alvo:
                return {**l, "_diario": diario.name, "_marca": diario.parent.name}
    return None


def achar_grafo(psd: Path, grafo: str | None, fluxos: Path = RAIZ / "fluxos") -> tuple[dict, dict | None]:
    origem = origem_do_psd(psd, fluxos)
    if origem is None and Path(fluxos).resolve() != (RAIZ / "fluxos").resolve():
        origem = origem_do_psd(psd)                  # peça do repositório, diário de teste em outra pasta
    if grafo is None:
        if origem is None:
            raise SystemExit(f"{psd}: não achei no diário de onde veio este PSD; passe --grafo")
        grafo = origem["grafo"]["arquivo"]
    return G.carregar(RAIZ / grafo if not Path(grafo).is_absolute() else grafo), origem


@lru_cache(maxsize=8)
def _ficha(caminho: str) -> dict:
    return F.carregar(RAIZ / caminho)


def tipos_da_ficha(grafo: dict) -> dict[str, str]:
    return {c["id"]: c["tipo"] for c in _ficha(grafo["ficha"])["camadas"]}


# ---------------------------------------------------------------- camadas e medida


def camadas_de_pixels(psd: Path) -> dict[str, tuple[np.ndarray, int, int]]:
    """Camadas de imagem do PSD por nome, de baixo para cima (ver `motor.comparar.camadas_do_psd`).

    Objeto inteligente conta: o psd-tools devolve a prévia guardada, que já vem com os
    filtros inteligentes aplicados.
    """
    return CMP.camadas_do_psd(psd)


def medir(grafo: dict, psd: Path, final: Image.Image, camadas: dict | None = None) -> dict:
    """Notas de cada parte como ela aparece na peça achatada (vale ajuste, estilo e filtro)."""
    camadas = camadas_de_pixels(psd) if camadas is None else camadas
    geradas = [c for c in G.camadas_geradas(grafo) if c in camadas]
    W, H = grafo["tamanho_px"]
    final = final.convert("RGB").resize((W, H)) if final.size != (W, H) else final.convert("RGB")
    return CMP.medir(grafo, final, CMP.camadas_no_final(final, camadas), geradas)


def cobertas(grafo: dict, camadas: dict, camada: str) -> tuple[np.ndarray, np.ndarray]:
    """O que as camadas da ficha acima da parte cobrem, na peça e na referência.

    Só contam partes geradas, texto e logo; efeitos (brilho, escurecimento) e as camadas
    de acabamento presas à parte não cobrem.
    """
    W, H = grafo["tamanho_px"]
    tipos = tipos_da_ficha(grafo)
    ordem_ficha = list(tipos)
    peca, ref = np.zeros((H, W), bool), np.zeros((H, W), bool)
    nomes = list(camadas)
    if camada in nomes:
        for outra in nomes[nomes.index(camada) + 1 :]:
            if tipos.get(outra) in TIPOS_QUE_COBREM:
                peca |= CMP.na_tela(*camadas[outra], W, H)[..., 3] > 128
    if camada in ordem_ficha:
        for outra in ordem_ficha[ordem_ficha.index(camada) + 1 :]:
            if tipos[outra] in TIPOS_QUE_COBREM:
                ref |= G.mascara_camada(grafo, outra)
    return peca, ref


def _regioes(grafo: dict, camadas: dict, camada: str) -> tuple[np.ndarray, np.ndarray]:
    """Onde olhar a parte na peça e na referência, sem o que fica coberto por cima.

    Na tentativa do loop a parte está no mesmo lugar da referência: as duas regiões são a
    interseção. Numa parte nova (outra pose, outro tema) cada uma usa a sua região.
    """
    W, H = grafo["tamanho_px"]
    rgba, x, y = camadas[camada]
    alvo = G.mascara_camada(grafo, camada)
    acima_peca, acima_ref = cobertas(grafo, camadas, camada)
    if camada == "cena":
        livre = ~_zona_de_codigo(grafo)
        return livre & ~acima_peca, livre & alvo & ~acima_ref
    gerada = CMP.na_tela(rgba, x, y, W, H)[..., 3] > 128
    junto = alvo & gerada
    if alvo.any() and gerada.any() and junto.sum() >= 0.5 * min(alvo.sum(), gerada.sum()):
        visivel = junto & ~acima_peca & ~acima_ref
        return visivel, visivel
    return gerada & ~acima_peca, alvo & ~acima_ref


def _zona_de_codigo(grafo: dict) -> np.ndarray:
    W, H = grafo["tamanho_px"]
    zona = np.zeros((H, W), bool)
    for n in grafo["nos"]:
        if n["tipo"] in ("texto", "logo") and "caixa" in n:
            x, y, w, h = n["caixa"]
            f = 0.3 * h * H
            zona[max(0, int(y * H - f)) : int((y + h) * H + f), max(0, int(x * W - f)) : int((x + w) * W + f)] = True
    return zona


def _referencia(grafo: dict) -> np.ndarray:
    W, H = grafo["tamanho_px"]
    return np.asarray(Image.open(G.RAIZ / grafo["referencia"]).convert("RGB").resize((W, H)))


def perfis(grafo: dict, psd: Path, final: Image.Image, camadas: dict | None = None) -> dict:
    """Luz, contraste, saturação e nitidez de cada parte na peça e na referência."""
    W, H = grafo["tamanho_px"]
    fim = np.asarray(final.convert("RGB").resize((W, H)))
    ref = _referencia(grafo)
    camadas = camadas_de_pixels(psd) if camadas is None else camadas
    saida = {}
    for camada in G.camadas_geradas(grafo):
        if camada not in camadas:
            continue
        m_peca, m_ref = _regioes(grafo, camadas, camada)
        saida[camada] = {"peca": CMP.perfil(fim, m_peca), "referencia": CMP.perfil(ref, m_ref)}
    return saida


def bordas(grafo: dict, camadas: dict, final: Image.Image, renders: dict) -> dict:
    """Réguas de recorte e de luz de contorno de cada parte recortada (integracoes/photocraft/bordas.py)."""
    return B.medir(grafo, tipos_da_ficha(grafo), camadas, final, renders["sem"], renders["sem_estilo"],
                   lambda p: cobertas(grafo, camadas, p))


def renders_sem_partes(pc: Sessao, partes: list[str]) -> dict[str, dict[str, Image.Image]]:
    """A peça achatada com cada parte escondida, e sem os estilos da parte (brilho, sombra).

    A régua de recorte compara as duas: o que a borda da parte faz no fundo, sem contar o
    brilho externo que o iluminador pôs de propósito.
    """
    sem, sem_estilo = {}, {}
    visiveis = {c["name"]: c for c in reversed(pc.camadas()) if c.get("visible", True)}
    for parte in partes:
        c = visiveis.get(parte)            # a de cima que está visível, como na medida
        if c is None:
            continue
        if (c.get("effects") or {}).get("enabled"):
            pc.executar("layer.setEffectsVisible", {"layer": c["id"], "visible": False})
            try:
                sem_estilo[parte] = pc.render(lado_max=0)
            finally:
                pc.executar("layer.setEffectsVisible", {"layer": c["id"], "visible": True})
        pc.executar("layer.setProps", {"layer": c["id"], "visible": False})
        try:
            sem[parte] = pc.render(lado_max=0)
        finally:
            pc.executar("layer.setProps", {"layer": c["id"], "visible": True})
    return {"sem": sem, "sem_estilo": sem_estilo}


def diagnostico(perfis_: dict, bordas_: dict | None = None) -> list[str]:
    """As diferenças de acabamento em palavras, da maior para a menor."""
    nomes = {"luz": ("mais clara", "mais escura"), "contraste": ("com mais contraste", "com menos contraste"),
             "saturacao": ("mais saturada", "menos saturada"), "nitidez": ("mais nítida", "menos nítida")}
    area = {"luz": "cor", "contraste": "cor", "saturacao": "cor", "nitidez": "retoque"}
    achados = []
    for parte, p in perfis_.items():
        for chave, (mais, menos) in nomes.items():
            a, r = p["peca"][chave], p["referencia"][chave]
            if a is None or r is None or r == 0:
                continue
            rel = (a - r) / abs(r)
            if abs(rel) >= 0.1:
                texto = f"{parte}: {mais if rel > 0 else menos} que a referência ({chave} {a} x {r}, {rel:+.0%})"
                achados.append((abs(rel), texto + (f" ({area[chave]})" if bordas_ is not None else "")))
    achados += B.diagnostico(bordas_ or {})
    return [t for _, t in sorted(achados, key=lambda a: -a[0])]


def _parte_na_referencia(grafo: dict, camadas: dict, camada: str) -> np.ndarray:
    """O contorno do grafo, se a camada estiver no lugar da referência (senão, erro)."""
    W, H = grafo["tamanho_px"]
    alvo = G.mascara_camada(grafo, camada)
    if not alvo.any():
        raise ReceitaInvalida(f"o grafo não marca a parte {camada!r} na referência")
    if camada not in camadas:
        raise ReceitaInvalida(f"não há camada de pixels {camada!r} no PSD")
    gerada = CMP.na_tela(*camadas[camada], W, H)[..., 3] > 128
    dentro = (alvo & gerada).sum() / alvo.sum()
    if dentro < 0.8:
        raise ReceitaInvalida(f"a camada {camada!r} não está no lugar da referência (cobre {dentro:.0%} do contorno "
                              "do grafo): o contorno do grafo só serve para peça alinhada, como as do loop")
    return alvo


def curvas_da_camada(grafo: dict, camadas: dict, camada: str, forca: float,
                     inclinacao: tuple[float, float] = CC.INCLINACAO) -> dict:
    """Curvas que casam a camada (pixels originais) com a mesma parte na referência."""
    tela, m_atual, ref, m_ref = _par_da_camada(grafo, camadas, camada, "casar_cor")
    return CC.curvas_para_casar(tela, m_atual, ref, m_ref, forca=forca, inclinacao=inclinacao)


def curva_de_luz_da_camada(grafo: dict, camadas: dict, camada: str, forca: float,
                           inclinacao: tuple[float, float] = CC.INCLINACAO) -> list[list[int]]:
    tela, m_atual, ref, m_ref = _par_da_camada(grafo, camadas, camada, "casar_luz")
    return CC.curva_de_luz(tela, m_atual, ref, m_ref, forca=forca, inclinacao=inclinacao)


def _par_da_camada(grafo: dict, camadas: dict, camada: str, passo: str):
    if camada not in camadas:
        raise ReceitaInvalida(f"{passo}: não há camada de pixels {camada!r} no PSD")
    if not G.mascara_camada(grafo, camada).any():
        raise ReceitaInvalida(f"{passo}: o grafo não marca a parte {camada!r} na referência")
    W, H = grafo["tamanho_px"]
    tela = CMP.na_tela(*camadas[camada], W, H)[..., :3]
    m_atual, m_ref = _regioes(grafo, camadas, camada)
    if not m_atual.any() or not m_ref.any():
        raise ReceitaInvalida(f"{passo}: a parte {camada!r} fica toda coberta na peça ou na referência")
    return tela, m_atual, _referencia(grafo), m_ref


# ---------------------------------------------------------------- receita


def carregar_receita(caminho: Path) -> dict:
    receita = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if not isinstance(receita.get("passos"), list) or not receita["passos"]:
        raise ReceitaInvalida(f"{caminho}: a receita precisa de uma lista 'passos'")
    return receita


def _recusa(comando: str, params: dict) -> str | None:
    for prefixo, motivo in RECUSADOS.items():
        if comando.startswith(prefixo) and comando not in PERMITIDOS_VETOR:
            return motivo
    if comando == "layer.layerMask.edit" and (params.get("feather") or params.get("density", 100) != 100):
        return ("difusão e densidade ao vivo na máscara: o PhotoCraft desenha, mas a medida não vê; suavize a "
                "seleção (select.modify.feather) e revele")
    if comando == "select.refineEdge" and (params.get("decontaminate") or
                                           params.get("output") in ("newLayer", "newLayerWithMask")):
        return ("refineEdge com decontaminate (ou saída em camada nova) cria uma cópia e esconde a parte; use "
                "\"output\": \"layerMask\" sem decontaminate e depois layer.matting.colorDecontaminate")
    return None


def conferir_receita(receita: dict, ficha: dict) -> None:
    tipos = {c["id"]: c["tipo"] for c in ficha["camadas"]}
    for i, p in enumerate(receita["passos"], 1):
        camada = p.get("camada")
        if camada not in tipos:
            raise ReceitaInvalida(f"passo {i}: 'camada' {camada!r} não é camada da ficha {ficha['versao']}")
        if tipos[camada] in TIPOS_PROTEGIDOS:
            raise ReceitaInvalida(f"passo {i}: {camada!r} sai de código ({tipos[camada]}); o acabamento não mexe nela")
        alvo = p.get("alvo")
        if alvo is not None and (not isinstance(alvo, str) or tipos.get(alvo) in TIPOS_PROTEGIDOS):
            raise ReceitaInvalida(f"passo {i}: 'alvo' é o nome de uma camada que não sai de código")
        alvo_params = (p.get("params") or {}).get("layer")
        if alvo_params is not None and not isinstance(alvo_params, str):
            raise ReceitaInvalida(f"passo {i}: params.layer vai pelo nome da camada, não pelo id (o id muda a cada PSD)")
        if isinstance(alvo_params, str) and tipos.get(alvo_params) in TIPOS_PROTEGIDOS:
            raise ReceitaInvalida(f"passo {i}: params.layer {alvo_params!r} sai de código")
        especiais = [k for k in MEDIDOS if k in p]
        if len(especiais) + ("comando" in p) != 1:
            raise ReceitaInvalida(f"passo {i}: use 'comando' ou um passo medido ({', '.join(MEDIDOS)}), um só")
        if "comando" in p and not isinstance(p["comando"], str):
            raise ReceitaInvalida(f"passo {i}: 'comando' é o id do PhotoCraft")
        props = p.get("props")
        if props is not None and (not isinstance(props, dict) or "layer" in props or "name" in props):
            raise ReceitaInvalida(f"passo {i}: 'props' são propriedades da camada nova (blend, opacity...), sem "
                                  "'layer' nem 'name' (o nome vai em 'nome')")
        if props and isinstance(props.get("opacity"), (int, float)) and props["opacity"] > 1:
            raise ReceitaInvalida(f"passo {i}: opacity vai de 0 a 1 (0.6 = 60%)")
        if "comando" in p:
            params = p.get("params") or {}
            motivo = _recusa(p["comando"], params)
            if motivo:
                raise ReceitaInvalida(f"passo {i}: {p['comando']}: {motivo}")
            if p["comando"].startswith(SO_NA_ATIVA) and isinstance(alvo_params, str) \
                    and alvo_params != (alvo or camada):
                raise ReceitaInvalida(f"passo {i}: {p['comando']} age na camada ativa e ignora 'layer': ponha "
                                      f"\"alvo\": {alvo_params!r} no passo")
        for chave in ("casar_cor", "casar_luz"):
            if chave in p:
                inc = (p[chave] or {}).get("inclinacao", CC.INCLINACAO)
                if not (isinstance(inc, (list, tuple)) and len(inc) == 2 and 0 <= inc[0] <= 1 <= inc[1]):
                    raise ReceitaInvalida(f"passo {i}: {chave}.inclinacao é [mínimo de 0 a 1, máximo 1 ou mais]")


def conferir_camadas(receita: dict, nomes: set[str]) -> None:
    """Toda camada da receita existe na peça (um PSD da ficha v1.1 não tem `frente`)."""
    faltam = sorted({p["camada"] for p in receita["passos"]} - nomes)
    if faltam:
        raise ReceitaInvalida(f"a peça não tem a(s) camada(s) {', '.join(faltam)} (o PSD é de outra versão da "
                              "ficha?); tire esses passos da receita")


class Documentos:
    """O PSD é o documento 0; as máscaras do grafo abrem como documentos extras, uma por parte.

    `camadas_agora` grava o documento como está numa pasta de trabalho e lê as camadas de
    novo: os passos medidos (casar_cor, casar_luz) olham a parte já com o que os passos
    anteriores fizeram nela (máscara do recorte, descontaminação...).
    """

    def __init__(self, pc: Sessao, pasta: Path, grafo: dict, camadas: dict):
        self.pc, self.pasta, self.grafo, self.camadas = pc, pasta, grafo, camadas
        self.abertos: dict[str, int] = {}
        self._gravacoes = 0

    def camadas_agora(self) -> dict:
        self._gravacoes += 1
        meio = self.pasta / f"meio-{self._gravacoes}.psd"
        self.pc.salvar(meio)
        self.camadas = camadas_de_pixels(meio)
        return self.camadas

    def mascara(self, camada: str) -> int:
        if camada not in self.abertos:
            alvo = _parte_na_referencia(self.grafo, self.camadas, camada)
            png = self.pasta / f"mascara-{camada}.png"
            Image.fromarray((alvo * 255).astype(np.uint8)).convert("RGB").save(png)
            self.abertos[camada] = self.pc.abrir(png)["index"]
            self.pc.chamar("doc.select", {"index": 0})
        return self.abertos[camada]


def aplicar_passos(pc: Sessao, receita: dict, grafo: dict, camadas: dict, docs: Documentos | None = None) -> list[dict]:
    feitos = []
    contagem: dict[str, int] = {}
    for i, p in enumerate(receita["passos"], 1):
        camada = p["camada"]
        try:
            feito = _um_passo(pc, p, grafo, camadas, docs, contagem)
        except KeyError as e:
            raise ReceitaInvalida(f"passo {i}: {e.args[0]}") from None
        except ErroPhotoCraft as e:
            raise RuntimeError(f"passo {i} ({p.get('comando') or next(k for k in MEDIDOS if k in p)} em {camada!r}): "
                               f"{e}") from None
        feitos.append({"passo": i, "camada": camada, **feito})
    return feitos


def _um_passo(pc: Sessao, p: dict, grafo: dict, camadas: dict, docs: Documentos | None,
              contagem: dict[str, int]) -> dict:
    camada = p["camada"]
    selecionada = pc.camada(p.get("alvo") or camada)
    pc.executar("layer.select", {"layer": selecionada})
    props = dict(p.get("props") or {})
    if "casar_cor" in p or "casar_luz" in p:
        chave = "casar_cor" if "casar_cor" in p else "casar_luz"
        opcoes = p[chave] or {}
        if docs is not None:
            camadas = docs.camadas_agora()
            pc.executar("layer.select", {"layer": selecionada})
        forca, inc = float(opcoes.get("forca", 1.0)), tuple(opcoes.get("inclinacao", CC.INCLINACAO))
        comando = "layer.newAdjustmentLayer.curves"
        if chave == "casar_cor":
            params = curvas_da_camada(grafo, camadas, camada, forca, inc)
            nome = p.get("nome") or f"acabamento {camada} cor por medida"
        else:
            params = {"points": curva_de_luz_da_camada(grafo, camadas, camada, forca, inc)}
            nome = p.get("nome") or f"acabamento {camada} luz por medida"
            props = {"blend": "Luminosity", **props}
        prender, enviados = True, params
    elif "selecao_do_grafo" in p or "mascara_do_grafo" in p:
        if docs is None:
            raise ReceitaInvalida("a máscara do grafo só roda pelo `aplicar`")
        doc = docs.mascara(camada)
        pc.executar("select.loadSelection", {"channel": "red", "document": doc})
        if "mascara_do_grafo" in p:
            if next(c for c in pc.camadas() if c["id"] == selecionada).get("hasMask"):
                pc.executar("layer.layerMask.delete", {"layer": selecionada})
            pc.executar("layer.layerMask.revealSelection", {"layer": selecionada})
            pc.executar("select.deselect", {})
        return {"comando": "selecao_do_grafo" if "selecao_do_grafo" in p else "mascara_do_grafo",
                "params": {}, "camadas_novas": 0}
    else:
        comando = p["comando"]
        params = dict(p.get("params") or {})
        enviados = dict(params)
        if isinstance(params.get("layer"), str):
            enviados["layer"] = pc.camada(params["layer"])
        prender, nome = bool(p.get("prender")), p.get("nome")
        if comando == "select.deselect" and not pc.inspecionar().get("hasSelection"):
            return {"comando": comando, "params": params, "camadas_novas": 0, "pulado": "sem seleção"}
    antes = {c["id"]: c["name"] for c in pc.camadas()}
    resultado = pc.executar(comando, enviados)
    depois = pc.camadas()
    sumiram = {antes[i] for i in set(antes) - {c["id"] for c in depois}}
    novas, trocadas = [], []
    for c in depois:
        if c["id"] in antes:
            continue
        (trocadas if c["name"] in sumiram else novas).append(c)      # id novo, mesmo nome: a mesma camada
    for nova in novas:
        if prender:
            pc.executar("layer.createClippingMask", {"layer": nova["id"]})
        contagem[camada] = contagem.get(camada, 0) + 1
        pc.executar("layer.setProps", {"layer": nova["id"], **props,
                                       "name": nome or f"acabamento {camada} {contagem[camada]}"})
    saida = {"comando": comando, "params": params, "camadas_novas": len(novas)}
    if p.get("alvo"):
        saida["alvo"] = p["alvo"]
    if trocadas:
        saida["mesma_camada_id_novo"] = [c["name"] for c in trocadas]
    if isinstance(resultado, dict) and resultado.get("warnings"):
        saida["avisos"] = resultado["warnings"]
    return saida


def _pilha(pc: Sessao) -> list[dict]:
    """Camadas do topo do documento, de cima para baixo."""
    doc = pc.inspecionar()
    return list(doc.get("layers") or [])


def conferir_pilha(ficha: dict, antes: list[dict], depois: list[dict]) -> list[str]:
    """Nada novo acima do texto e do logo, texto e logo como antes, e as partes ainda à vista."""
    protegidas = {c["id"] for c in ficha["camadas"] if c["tipo"] in TIPOS_PROTEGIDOS}
    geradas = {c["id"] for c in ficha["camadas"] if c["tipo"] == "gerada"}

    def acima(pilha: list[dict]) -> set[str]:
        nomes = [c["name"] for c in pilha]
        presentes = [i for i, n in enumerate(nomes) if n in protegidas]
        return set(nomes[: max(presentes)]) - protegidas if presentes else set()

    problemas = [f"a camada {n!r} ficou acima do texto ou do logo" for n in sorted(acima(depois) - acima(antes))]
    ignorar = {"id", "selected"}
    for nome in sorted(protegidas):
        a = next((c for c in antes if c["name"] == nome), None)
        d = next((c for c in depois if c["name"] == nome), None)
        if a is None:
            continue
        if d is None:
            problemas.append(f"a camada {nome!r} sumiu")
        elif {k: v for k, v in a.items() if k not in ignorar} != {k: v for k, v in d.items() if k not in ignorar}:
            problemas.append(f"a camada {nome!r} mudou de propriedades (estilo, opacidade, modo ou visibilidade)")

    def a_vista(pilha: list[dict]) -> set[str]:
        return {c["name"] for c in pilha if c["name"] in geradas and c.get("visible", True)}

    for nome in sorted(a_vista(antes) - a_vista(depois)):
        problemas.append(f"a parte {nome!r} sumiu ou ficou escondida (um passo renomeou a parte ou criou uma cópia e "
                         "escondeu o original; dê à camada que fica o nome da parte)")
    return problemas


def conferir_protegidas(ficha: dict, antes: dict, depois: dict, W: int, H: int) -> list[str]:
    """Texto e logo têm de sair do acabamento pixel a pixel iguais."""
    mudaram = []
    for c in ficha["camadas"]:
        if c["tipo"] not in TIPOS_PROTEGIDOS or c["id"] not in antes:
            continue
        if c["id"] not in depois or not np.array_equal(CMP.na_tela(*antes[c["id"]], W, H), CMP.na_tela(*depois[c["id"]], W, H)):
            mudaram.append(c["id"])
    return mudaram


def proximo_id(diario: Path, peca: str) -> str:
    n = 0
    if diario.exists():
        n = sum(1 for l in diario.read_text(encoding="utf-8").splitlines() if l.strip()
                and json.loads(l).get("peca") == peca)
    return f"{peca}-ac{n + 1:03d}"


def medir_tudo(pc: Sessao, grafo: dict, psd: Path, final: Image.Image | None = None) -> dict:
    """Notas (ΔE), perfis e bordas da peça aberta em `pc`, lida do `psd` salvo."""
    final = pc.render(lado_max=0) if final is None else final
    camadas = camadas_de_pixels(psd)
    sem = renders_sem_partes(pc, B.partes_recortadas(grafo, camadas))
    return {"final": final, "camadas": camadas, "notas": medir(grafo, psd, final, camadas),
            "perfis": perfis(grafo, psd, final, camadas), "bordas": bordas(grafo, camadas, final, sem)}


def aplicar(psd: Path, receita_arq: Path, grafo_arq: str | None = None, mudanca: str = "",
            saida: Path = RAIZ / "saida", fluxos: Path = RAIZ / "fluxos") -> dict:
    tempos: dict[str, float] = {}
    t0 = time.perf_counter()
    psd = Path(psd).resolve()
    grafo, origem = achar_grafo(psd, grafo_arq, fluxos)
    ficha = F.carregar(RAIZ / grafo["ficha"])
    receita = carregar_receita(receita_arq)
    conferir_receita(receita, ficha)
    W, H = grafo["tamanho_px"]
    marca = grafo["marca"]
    diario = fluxos / marca / "acabamentos.jsonl"
    id_ = proximo_id(diario, grafo["peca"])
    destino = saida / marca / "acabamentos" / id_
    destino.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=destino, prefix=".trabalho-") as trabalho, \
            Sessao(leitura=Path(trabalho), escrita=destino.parent) as pc:
        trabalho = Path(trabalho)
        shutil.copy(psd, trabalho / "peca.psd")
        aberto = pc.abrir(trabalho / "peca.psd")
        conferir_camadas(receita, {c["name"] for c in pc.camadas()})
        antes = medir_tudo(pc, grafo, psd)
        tempos["medir_antes"] = round(time.perf_counter() - t0, 1)
        t = time.perf_counter()
        pilha_antes = _pilha(pc)
        docs = Documentos(pc, trabalho, grafo, antes["camadas"])
        feitos = aplicar_passos(pc, receita, grafo, antes["camadas"], docs)
        problemas = conferir_pilha(ficha, pilha_antes, _pilha(pc))
        if problemas:
            raise RuntimeError("a receita quebrou uma regra: " + "; ".join(problemas) + " (nada foi anotado)")
        tempos["passos"] = round(time.perf_counter() - t, 1)
        t = time.perf_counter()
        salvo = pc.salvar(destino / "acabado.psd") or {}
        avisos = list(salvo.get("warnings") or [])
        if avisos:
            raise RuntimeError("o PSD salvo não guarda tudo o que a receita fez: " + "; ".join(map(str, avisos))
                               + " (troque o comando por um que vá para o PSD; nada foi anotado)")
        depois_img = pc.exportar(destino / "acabado.png")
        depois_img.convert("RGB").save(destino / "acabado.webp", "WEBP", quality=90)
        depois = medir_tudo(pc, grafo, destino / "acabado.psd", depois_img)
        ver = versao(pc.cli)
    mudaram = conferir_protegidas(ficha, antes["camadas"], depois["camadas"], W, H)
    if mudaram:
        raise RuntimeError(f"o acabamento mudou camadas que saem de código: {', '.join(mudaram)} "
                           f"(arquivos em {_rel(destino)}, nada foi anotado no diário)")
    for parte in depois["bordas"]:
        if parte in antes["camadas"]:
            depois["bordas"][parte]["estouro"] = B.estouro(CMP.na_tela(*antes["camadas"][parte], W, H),
                                                           CMP.na_tela(*depois["camadas"][parte], W, H))
    CMP.prancha(grafo, {"antes": antes["final"], "depois": depois_img},
                {"antes": antes["notas"], "depois": depois["notas"]}).save(destino / "prancha.jpg", quality=88)
    tempos["salvar_e_medir"] = round(time.perf_counter() - t, 1)
    tempos["total"] = round(time.perf_counter() - t0, 1)

    texto_receita = Path(receita_arq).read_bytes()
    sha = hashlib.sha256(texto_receita).hexdigest()
    guardada = fluxos / marca / "receitas" / f"{sha[:16]}.json"
    guardada.parent.mkdir(parents=True, exist_ok=True)
    guardada.write_bytes(texto_receita)
    linha = {
        "id": id_, "peca": grafo["peca"], "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem": {"psd": _rel(psd), "id": origem.get("id") if origem else None},
        "grafo": {"arquivo": _rel(Path(grafo["_caminho"])), "sha256": grafo["_sha256"]},
        "ficha": ficha["versao"],
        "receita": {"nome": receita.get("nome"), "arquivo": _rel(Path(receita_arq)), "guardada": _rel(guardada),
                    "sha256": sha},
        "photocraft": ver, "mudanca": mudanca, "custo_usd": 0.0, "tempos_s": tempos,
        "avisos_ao_abrir": aberto.get("warnings") or [],
        "passos": feitos,
        "notas_antes": antes["notas"], "notas": depois["notas"],
        "perfis_antes": antes["perfis"], "perfis": depois["perfis"],
        "bordas_antes": antes["bordas"], "bordas": depois["bordas"],
        "diagnostico_antes": diagnostico(antes["perfis"], antes["bordas"]),
        "diagnostico": diagnostico(depois["perfis"], depois["bordas"]),
        "arquivos": {"psd": _rel(destino / "acabado.psd"), "png": _rel(destino / "acabado.png"),
                     "webp": _rel(destino / "acabado.webp"), "prancha": _rel(destino / "prancha.jpg")},
        "decisao": None,
    }
    diario.parent.mkdir(parents=True, exist_ok=True)
    with diario.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def resumo(antes: dict, depois: dict) -> list[str]:
    linhas = []
    for parte in depois:
        a, d = antes.get(parte, {}).get("dE00"), depois[parte].get("dE00")
        if a is None or d is None:
            continue
        linhas.append(f"{parte:>8}: ΔE {a:5.1f} -> {d:5.1f} ({d - a:+.1f})")
    return linhas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="acao", required=True)
    m = sub.add_parser("medir", help="notas, perfis e bordas do PSD como o PhotoCraft o achata, contra a referência")
    m.add_argument("psd", type=Path)
    m.add_argument("--grafo")
    c = sub.add_parser("curvas", help="mostra as curvas de casar_cor e casar_luz para uma camada")
    c.add_argument("psd", type=Path)
    c.add_argument("--grafo")
    c.add_argument("--camada", required=True)
    c.add_argument("--forca", type=float, default=1.0)
    a = sub.add_parser("aplicar", help="aplica uma receita e anota no diário")
    a.add_argument("psd", type=Path)
    a.add_argument("--receita", type=Path, required=True)
    a.add_argument("--grafo")
    a.add_argument("--mudanca", default="")
    a.add_argument("--saida", type=Path, default=RAIZ / "saida")
    a.add_argument("--fluxos", type=Path, default=RAIZ / "fluxos", help="onde fica o diário (testes usam outra pasta)")
    args = ap.parse_args()

    if args.acao == "medir":
        psd = args.psd.resolve()
        grafo, _ = achar_grafo(psd, args.grafo)
        with Sessao(leitura=psd.parent) as pc:
            pc.abrir(psd)
            r = medir_tudo(pc, grafo, psd)
        print(json.dumps({"notas": r["notas"], "perfis": r["perfis"], "bordas": r["bordas"],
                          "diagnostico": diagnostico(r["perfis"], r["bordas"])}, ensure_ascii=False, indent=1))
    elif args.acao == "curvas":
        grafo, _ = achar_grafo(args.psd.resolve(), args.grafo)
        camadas = camadas_de_pixels(args.psd)
        print(json.dumps({"casar_cor": curvas_da_camada(grafo, camadas, args.camada, args.forca),
                          "casar_luz": curva_de_luz_da_camada(grafo, camadas, args.camada, args.forca)}))
    else:
        linha = aplicar(args.psd, args.receita, args.grafo, args.mudanca, args.saida, args.fluxos)
        print("\n".join(resumo(linha["notas_antes"], linha["notas"])))
        print("\n".join(linha["diagnostico"]) or "acabamento parecido com a referência em luz, contraste, saturação, "
                                                 "nitidez e bordas")
        print(json.dumps({"id": linha["id"], "arquivos": linha["arquivos"], "tempos_s": linha["tempos_s"]},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
