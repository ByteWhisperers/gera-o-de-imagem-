"""Sessão do PhotoCraft sem janela, para scripts e agentes.

Abre `photocraft-cli serve` (JSON por linha no stdin/stdout) e mantém um
documento aberto entre os comandos, o que é bem mais rápido que chamar o CLI
uma vez por comando.

    from integracoes.photocraft.sessao import Sessao

    with Sessao() as pc:
        pc.abrir("saida/arara/tentativas/promo-deposito-001/peca.psd")
        mascote = pc.camada("mascote")
        pc.executar("layer.select", {"layer": mascote})
        pc.executar("layer.newAdjustmentLayer.curves", {"points": [[0, 0], [128, 140], [255, 255]]})
        pc.render("saida/teste.png")
        pc.salvar("saida/teste.psd")

Leitura e escrita de arquivos passam pelas raízes que o PhotoCraft aceita:
caminhos relativos, sem `..`. Por padrão a leitura é o repositório inteiro e a
escrita é `saida/`.

O executável vem de `PHOTOCRAFT_CLI` ou do `photocraft-cli` no PATH.
"""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]


class ErroPhotoCraft(RuntimeError):
    def __init__(self, metodo: str, params: dict, erro: str):
        super().__init__(f"{metodo}: {erro}")
        self.metodo, self.params, self.erro = metodo, params, erro


def achar_cli() -> str:
    cli = os.environ.get("PHOTOCRAFT_CLI") or shutil.which("photocraft-cli")
    if not cli:
        raise FileNotFoundError("photocraft-cli não encontrado: instale (integracoes/photocraft/LEIA-ME.md) "
                                "ou aponte PHOTOCRAFT_CLI para o executável")
    return cli


def versao(cli: str | None = None) -> str:
    saida = subprocess.run([cli or achar_cli(), "--version"], check=True, capture_output=True, text=True).stdout
    return saida.split()[1] if len(saida.split()) > 1 else saida.strip()


class Sessao:
    def __init__(self, cli: str | None = None, leitura: Path = RAIZ, escrita: Path = RAIZ / "saida"):
        self.cli = cli or achar_cli()
        self.leitura, self.escrita = Path(leitura).resolve(), Path(escrita).resolve()
        self.escrita.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [self.cli, "serve", "--automation-read-root", str(self.leitura),
             "--automation-write-root", str(self.escrita)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self._id = 0

    # ------------------------------------------------------------ transporte

    def chamar(self, metodo: str, params: dict | None = None):
        """Um pedido ao servidor. Devolve o `result`; erro vira ErroPhotoCraft."""
        if self._proc.poll() is not None:
            raise ErroPhotoCraft(metodo, params or {}, "o photocraft-cli serve terminou")
        self._id += 1
        assert self._proc.stdin and self._proc.stdout
        self._proc.stdin.write(json.dumps({"id": self._id, "method": metodo, "params": params or {}}) + "\n")
        self._proc.stdin.flush()
        while True:
            linha = self._proc.stdout.readline()
            if not linha:
                raise ErroPhotoCraft(metodo, params or {}, "o photocraft-cli serve fechou a conexão")
            resposta = json.loads(linha)
            if resposta.get("id") == self._id:
                break
        if not resposta.get("ok"):
            raise ErroPhotoCraft(metodo, params or {}, str(resposta.get("error")))
        return resposta.get("result")

    def fechar(self) -> None:
        if self._proc.poll() is None:
            assert self._proc.stdin
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def __enter__(self) -> "Sessao":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    # ------------------------------------------------------------ caminhos

    def _relativo(self, caminho: str | Path, raiz: Path) -> str:
        p = Path(caminho)
        p = (p if p.is_absolute() else Path.cwd() / p).resolve()
        try:
            return p.relative_to(raiz).as_posix()
        except ValueError:
            raise ValueError(f"{caminho} fica fora da raiz {raiz} que o PhotoCraft pode usar") from None

    # ------------------------------------------------------------ documento

    def abrir(self, caminho: str | Path) -> dict:
        return self.chamar("doc.open", {"path": self._relativo(caminho, self.leitura)})

    def salvar(self, caminho: str | Path, **extra) -> dict:
        destino = Path(caminho)
        destino = destino if destino.is_absolute() else Path.cwd() / destino
        destino.parent.mkdir(parents=True, exist_ok=True)
        return self.chamar("doc.save", {"path": self._relativo(destino, self.escrita), **extra})

    def inspecionar(self) -> dict:
        return self.chamar("doc.inspect")

    def executar(self, comando: str, params: dict | None = None):
        pedido = {"command": comando}
        if params is not None:
            pedido["params"] = params
        return self.chamar("engine.execute", pedido)

    def lote(self, passos: list[dict], parar_no_erro: bool = True) -> dict:
        """Passos no formato do servidor: {"command": id, "params": {...}}."""
        return self.chamar("batch", {"steps": passos, "stopOnError": parar_no_erro})

    def render(self, caminho: str | Path | None = None, lado_max: int = 1024) -> Image.Image:
        """Prévia achatada como o PhotoCraft a vê (com ajustes, estilos e filtros).

        `lado_max` 0 é o tamanho cheio, até 2048 px no lado maior; para o arquivo
        final use `exportar`, que não tem esse teto.
        """
        if caminho is None:
            r = self.chamar("doc.render", {"maxSide": lado_max})
            return Image.open(io.BytesIO(base64.b64decode(r["base64"]))).copy()
        destino = Path(caminho)
        destino = destino if destino.is_absolute() else Path.cwd() / destino
        destino.parent.mkdir(parents=True, exist_ok=True)
        self.chamar("doc.render", {"maxSide": lado_max, "path": self._relativo(destino, self.escrita)})
        return Image.open(destino).copy()

    def exportar(self, caminho: str | Path, **extra) -> Image.Image:
        """Grava o documento achatado (PNG, WebP, JPEG… pela extensão) no tamanho cheio."""
        self.salvar(caminho, **extra)
        destino = Path(caminho)
        return Image.open(destino if destino.is_absolute() else Path.cwd() / destino).copy()

    # ------------------------------------------------------------ camadas

    def camadas(self) -> list[dict]:
        """Camadas de cima para baixo, achatando grupos: [{id, name, kind, ...}]."""
        doc = self.inspecionar()
        doc = doc.get("document", doc) if isinstance(doc, dict) else doc
        saida: list[dict] = []

        def andar(lista):
            for c in lista or []:
                saida.append(c)
                andar(c.get("children"))

        andar(doc.get("layers") if isinstance(doc, dict) else None)
        return saida

    def camada(self, nome: str) -> int:
        """Id da camada com esse nome (a de cima, se houver repetidas)."""
        for c in self.camadas():
            if c.get("name") == nome:
                return c["id"]
        raise KeyError(f"não há camada {nome!r} no documento")
