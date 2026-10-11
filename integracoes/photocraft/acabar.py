"""Acabamento no PhotoCraft: aplica uma receita de edição a um PSD e mede antes e depois.

A receita é uma lista de comandos do PhotoCraft (os ids do catálogo,
`.claude/skills/photocraft/referencia/catalogo.md`), cada um apontando para uma
camada da ficha pelo nome. O acabamento é não destrutivo sempre que dá: camadas
de ajuste presas à parte, estilos de camada, máscaras. Texto e logo saem de
código e a receita não mexe neles (o script confere pixel a pixel).

Uso:
    python integracoes/photocraft/acabar.py medir saida/arara/tentativas/promo-deposito-001/peca.psd
    python integracoes/photocraft/acabar.py curvas saida/arara/tentativas/promo-deposito-001/peca.psd --camada mascote
    python integracoes/photocraft/acabar.py aplicar saida/arara/tentativas/promo-deposito-001/peca.psd \\
        --receita integracoes/photocraft/receitas/arara/cor-por-medida.json --mudanca "cor casada por medida"

O grafo da peça vem do diário (tentativas.jsonl ou acabamentos.jsonl da marca) ou de --grafo.

Cada `aplicar` grava em saida/<marca>/acabamentos/<id>/ o PSD, o PNG, o WebP e a
prancha antes x depois, guarda a receita em fluxos/<marca>/receitas/<sha256>.json e
acrescenta uma linha em fluxos/<marca>/acabamentos.jsonl com "decisao": null. Custo zero.

Formato da receita (JSON):
    {"nome": "...", "descricao": "...",
     "passos": [
        {"camada": "mascote", "casar_cor": {"forca": 0.8}},
        {"camada": "mascote", "comando": "layer.newAdjustmentLayer.vibrance", "params": {"vibrance": 12},
         "prender": true, "nome": "acabamento mascote vibração"},
        {"camada": "frente", "comando": "filter.blur.gaussianBlur", "params": {"radius": 3}}]}

- `camada`: a camada da ficha que o passo seleciona antes do comando;
- `prender`: a camada nova que o comando criar fica presa à camada (máscara de corte);
- `nome`: nome da camada nova (sem ele, "acabamento <camada> <n>");
- `casar_cor`: curvas calculadas por medida contra a mesma parte na referência
  (integracoes/photocraft/casar_cor.py), feitas a partir dos pixels originais da camada;
- em `params`, "layer": "<nome>" vira o id da camada com esse nome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from integracoes.photocraft import casar_cor as CC  # noqa: E402
from integracoes.photocraft.sessao import Sessao, versao  # noqa: E402
from motor import comparar as CMP  # noqa: E402
from motor import ficha as F  # noqa: E402
from motor import grafo as G  # noqa: E402

TIPOS_PROTEGIDOS = {"texto", "arquivo"}     # saem de código: o acabamento não toca


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
    if grafo is None:
        if origem is None:
            raise SystemExit(f"{psd}: não achei no diário de onde veio este PSD; passe --grafo")
        grafo = origem["grafo"]["arquivo"]
    return G.carregar(RAIZ / grafo if not Path(grafo).is_absolute() else grafo), origem


# ---------------------------------------------------------------- camadas e medida


def camadas_de_pixels(psd: Path) -> dict[str, tuple[np.ndarray, int, int]]:
    """Camadas de imagem do PSD por nome (a máscara de camada já aplicada no alfa).

    Objeto inteligente conta (o acabamento converte partes para aplicar filtros que
    continuam editáveis); o psd-tools devolve a prévia dele, sem os filtros.
    """
    from psd_tools import PSDImage

    saida = {}
    for l in PSDImage.open(psd):
        if l.kind not in ("pixel", "smartobject"):
            continue
        im = l.topil()
        if im is None:
            continue
        rgba = np.asarray(im.convert("RGBA")).copy()
        if l.mask is not None and not l.mask.disabled:
            rgba[..., 3] = (rgba[..., 3].astype(np.uint16) * _mascara_na_camada(l) // 255).astype(np.uint8)
        saida.setdefault(l.name, (rgba, l.left, l.top))
    return saida


def _mascara_na_camada(l) -> np.ndarray:
    m = l.mask
    h, w = l.height, l.width
    tela = np.full((h, w), m.background_color, np.uint16)
    im = m.topil()
    if im is not None:
        a = np.asarray(im.convert("L"), np.uint16)
        x0, y0 = m.left - l.left, m.top - l.top
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(w, x0 + a.shape[1]), min(h, y0 + a.shape[0])
        if xb > xa and yb > ya:
            tela[ya:yb, xa:xb] = a[ya - y0 : yb - y0, xa - x0 : xb - x0]
    return tela


def medir(grafo: dict, psd: Path, final: Image.Image) -> dict:
    """Notas de cada parte como ela aparece na peça achatada (vale ajuste, estilo e filtro)."""
    camadas = camadas_de_pixels(psd)
    geradas = [c for c in G.camadas_geradas(grafo) if c in camadas]
    W, H = grafo["tamanho_px"]
    final = final.convert("RGB").resize((W, H)) if final.size != (W, H) else final.convert("RGB")
    return CMP.medir(grafo, final, CMP.camadas_no_final(final, camadas), geradas)


def _regioes(grafo: dict, rgba: np.ndarray, x: int, y: int, camada: str) -> tuple[np.ndarray, np.ndarray]:
    """Onde olhar a parte na peça e na referência.

    Na tentativa do loop a parte está no mesmo lugar da referência: as duas regiões são a
    interseção. Numa parte nova (outra pose, outro tema) cada uma usa a sua região.
    """
    W, H = grafo["tamanho_px"]
    alvo = G.mascara_camada(grafo, camada)
    if camada == "cena":
        livre = ~_zona_de_codigo(grafo)
        return alvo & livre, alvo & livre
    gerada = CMP.na_tela(rgba, x, y, W, H)[..., 3] > 128
    junto = alvo & gerada
    if alvo.any() and gerada.any() and junto.sum() >= 0.5 * min(alvo.sum(), gerada.sum()):
        return junto, junto
    return gerada, alvo


def _zona_de_codigo(grafo: dict) -> np.ndarray:
    W, H = grafo["tamanho_px"]
    zona = np.zeros((H, W), bool)
    for n in grafo["nos"]:
        if n["tipo"] in ("texto", "logo") and "caixa" in n:
            x, y, w, h = n["caixa"]
            f = 0.3 * h * H
            zona[max(0, int(y * H - f)) : int((y + h) * H + f), max(0, int(x * W - f)) : int((x + w) * W + f)] = True
    return zona


def perfis(grafo: dict, psd: Path, final: Image.Image) -> dict:
    """Luz, contraste, saturação e nitidez de cada parte na peça e na referência."""
    W, H = grafo["tamanho_px"]
    fim = np.asarray(final.convert("RGB").resize((W, H)))
    ref = np.asarray(Image.open(G.RAIZ / grafo["referencia"]).convert("RGB").resize((W, H)))
    camadas = camadas_de_pixels(psd)
    saida = {}
    for camada in G.camadas_geradas(grafo):
        if camada not in camadas:
            continue
        m_peca, m_ref = _regioes(grafo, *camadas[camada], camada)
        saida[camada] = {"peca": CMP.perfil(fim, m_peca), "referencia": CMP.perfil(ref, m_ref)}
    return saida


def diagnostico(perfis_: dict) -> list[str]:
    """As diferenças de acabamento em palavras, da maior para a menor."""
    nomes = {"luz": ("mais clara", "mais escura"), "contraste": ("com mais contraste", "com menos contraste"),
             "saturacao": ("mais saturada", "menos saturada"), "nitidez": ("mais nítida", "menos nítida")}
    achados = []
    for parte, p in perfis_.items():
        for chave, (mais, menos) in nomes.items():
            a, r = p["peca"][chave], p["referencia"][chave]
            if a is None or r is None or r == 0:
                continue
            rel = (a - r) / abs(r)
            if abs(rel) >= 0.1:
                achados.append((abs(rel), f"{parte}: {mais if rel > 0 else menos} que a referência "
                                          f"({chave} {a} x {r}, {rel:+.0%})"))
    return [t for _, t in sorted(achados, reverse=True)]


def curvas_da_camada(grafo: dict, camadas: dict, camada: str, forca: float) -> dict:
    """Curvas que casam a camada (pixels originais) com a mesma parte na referência."""
    if camada not in camadas:
        raise ReceitaInvalida(f"casar_cor: não há camada de pixels {camada!r} no PSD")
    W, H = grafo["tamanho_px"]
    rgba, x, y = camadas[camada]
    if not G.mascara_camada(grafo, camada).any():
        raise ReceitaInvalida(f"casar_cor: o grafo não marca a parte {camada!r} na referência")
    tela = CMP.na_tela(rgba, x, y, W, H)
    ref = np.asarray(Image.open(G.RAIZ / grafo["referencia"]).convert("RGB").resize((W, H)))
    m_atual, m_ref = _regioes(grafo, rgba, x, y, camada)
    return CC.curvas_para_casar(tela[..., :3], m_atual, ref, m_ref, forca=forca)


# ---------------------------------------------------------------- receita


def carregar_receita(caminho: Path) -> dict:
    receita = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if not isinstance(receita.get("passos"), list) or not receita["passos"]:
        raise ReceitaInvalida(f"{caminho}: a receita precisa de uma lista 'passos'")
    return receita


def conferir_receita(receita: dict, ficha: dict) -> None:
    tipos = {c["id"]: c["tipo"] for c in ficha["camadas"]}
    for i, p in enumerate(receita["passos"], 1):
        camada = p.get("camada")
        if camada not in tipos:
            raise ReceitaInvalida(f"passo {i}: 'camada' {camada!r} não é camada da ficha {ficha['versao']}")
        if tipos[camada] in TIPOS_PROTEGIDOS:
            raise ReceitaInvalida(f"passo {i}: {camada!r} sai de código ({tipos[camada]}); o acabamento não mexe nela")
        alvo_params = (p.get("params") or {}).get("layer")
        if alvo_params is not None and not isinstance(alvo_params, str):
            raise ReceitaInvalida(f"passo {i}: params.layer vai pelo nome da camada, não pelo id (o id muda a cada PSD)")
        if isinstance(alvo_params, str) and tipos.get(alvo_params) in TIPOS_PROTEGIDOS:
            raise ReceitaInvalida(f"passo {i}: params.layer {alvo_params!r} sai de código")
        if ("comando" in p) == ("casar_cor" in p):
            raise ReceitaInvalida(f"passo {i}: use 'comando' ou 'casar_cor' (um dos dois)")
        if "comando" in p and not isinstance(p["comando"], str):
            raise ReceitaInvalida(f"passo {i}: 'comando' é o id do PhotoCraft")


def aplicar_passos(pc: Sessao, receita: dict, grafo: dict, camadas: dict) -> list[dict]:
    feitos = []
    contagem: dict[str, int] = {}
    for i, p in enumerate(receita["passos"], 1):
        camada = p["camada"]
        alvo = pc.camada(camada)
        pc.executar("layer.select", {"layer": alvo})
        if "casar_cor" in p:
            forca = float((p["casar_cor"] or {}).get("forca", 1.0))
            comando = "layer.newAdjustmentLayer.curves"
            params = curvas_da_camada(grafo, camadas, camada, forca)
            prender, nome = True, p.get("nome") or f"acabamento {camada} cor por medida"
        else:
            comando = p["comando"]
            params = dict(p.get("params") or {})
            if isinstance(params.get("layer"), str):
                params["layer"] = pc.camada(params["layer"])
            prender, nome = bool(p.get("prender")), p.get("nome")
        antes = {c["id"] for c in pc.camadas()}
        resultado = pc.executar(comando, params)
        novas = [c for c in pc.camadas() if c["id"] not in antes]
        for nova in novas:
            if prender:
                pc.executar("layer.createClippingMask", {"layer": nova["id"]})
            contagem[camada] = contagem.get(camada, 0) + 1
            pc.executar("layer.setProps", {"layer": nova["id"],
                                           "name": nome or f"acabamento {camada} {contagem[camada]}"})
        feitos.append({"passo": i, "camada": camada, "comando": comando, "params": params,
                       "camadas_novas": len(novas), "resultado": resultado})
    return feitos


def _pilha(pc: Sessao) -> list[dict]:
    """Camadas do topo do documento, de cima para baixo."""
    doc = pc.inspecionar()
    return list(doc.get("layers") or [])


def conferir_pilha(ficha: dict, antes: list[dict], depois: list[dict]) -> list[str]:
    """Nada novo acima do texto e do logo, e os dois com as mesmas propriedades de antes."""
    protegidas = {c["id"] for c in ficha["camadas"] if c["tipo"] in TIPOS_PROTEGIDOS}

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
    camadas_antes = camadas_de_pixels(psd)

    with Sessao(leitura=psd.parent, escrita=destino.parent) as pc:
        pc.abrir(psd)
        antes = pc.render(lado_max=0)
        notas_antes = medir(grafo, psd, antes)
        perfis_antes = perfis(grafo, psd, antes)
        tempos["medir_antes"] = round(time.perf_counter() - t0, 1)
        t = time.perf_counter()
        pilha_antes = _pilha(pc)
        feitos = aplicar_passos(pc, receita, grafo, camadas_antes)
        problemas = conferir_pilha(ficha, pilha_antes, _pilha(pc))
        if problemas:
            raise RuntimeError("a receita mexeu no que sai de código: " + "; ".join(problemas)
                               + " (nada foi salvo nem anotado)")
        tempos["passos"] = round(time.perf_counter() - t, 1)
        t = time.perf_counter()
        pc.salvar(destino / "acabado.psd")
        depois = pc.exportar(destino / "acabado.png")
        depois.convert("RGB").save(destino / "acabado.webp", "WEBP", quality=90)
        ver = versao(pc.cli)
    notas_depois = medir(grafo, destino / "acabado.psd", depois)
    perfis_depois = perfis(grafo, destino / "acabado.psd", depois)
    camadas_depois = camadas_de_pixels(destino / "acabado.psd")
    mudaram = conferir_protegidas(ficha, camadas_antes, camadas_depois, W, H)
    if mudaram:
        raise RuntimeError(f"o acabamento mudou camadas que saem de código: {', '.join(mudaram)} "
                           f"(arquivos em {_rel(destino)}, nada foi anotado no diário)")
    CMP.prancha(grafo, {"antes": antes, "depois": depois}, {"antes": notas_antes, "depois": notas_depois}
                ).save(destino / "prancha.jpg", quality=88)
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
        "passos": [{k: v for k, v in f.items() if k != "resultado"} for f in feitos],
        "notas_antes": notas_antes, "notas": notas_depois,
        "perfis_antes": perfis_antes, "perfis": perfis_depois, "diagnostico": diagnostico(perfis_depois),
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
    m = sub.add_parser("medir", help="notas e perfis do PSD como o PhotoCraft o achata, contra a referência")
    m.add_argument("psd", type=Path)
    m.add_argument("--grafo")
    c = sub.add_parser("curvas", help="mostra as curvas de casar_cor para uma camada")
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
        grafo, _ = achar_grafo(args.psd, args.grafo)
        with Sessao(leitura=args.psd.resolve().parent) as pc:
            pc.abrir(args.psd)
            final = pc.render(lado_max=0)
        pf = perfis(grafo, args.psd, final)
        print(json.dumps({"notas": medir(grafo, args.psd, final), "perfis": pf, "diagnostico": diagnostico(pf)},
                         ensure_ascii=False, indent=1))
    elif args.acao == "curvas":
        grafo, _ = achar_grafo(args.psd, args.grafo)
        print(json.dumps(curvas_da_camada(grafo, camadas_de_pixels(args.psd), args.camada, args.forca)))
    else:
        linha = aplicar(args.psd, args.receita, args.grafo, args.mudanca, args.saida, args.fluxos)
        print("\n".join(resumo(linha["notas_antes"], linha["notas"])))
        print("\n".join(linha["diagnostico"]) or "acabamento parecido com a referência em luz, contraste, saturação e nitidez")
        print(json.dumps({"id": linha["id"], "arquivos": linha["arquivos"], "tempos_s": linha["tempos_s"]},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
