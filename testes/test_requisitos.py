"""Todo pacote de terceiros que o código importa tem de estar num requirements*.txt.

Quem baixa o projeto instala só o que está nesses arquivos (INSTALAR.md). Se um import
novo não for declarado, o projeto quebra na máquina dos outros e passa na nossa.
"""

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# módulo importado -> pacote do pip
PACOTE = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "psd_tools": "psd-tools",
    "skimage": "scikit-image",
    "numpy": "numpy",
    "scipy": "scipy",
    "rembg": "rembg",
    "pytest": "pytest",
}
# vêm do ComfyUI, onde o nó roda (integracoes/comfyui/nos_gera_imagem): não são do pip do projeto
DO_COMFYUI = {"torch", "folder_paths", "comfy", "server", "nodes", "execution"}
PASTAS = ("motor", "ferramentas", "integracoes", "testes")


def _do_projeto():
    """Nomes de módulo que são do próprio projeto (scripts da raiz, pacotes e arquivos das pastas)."""
    nomes = {p.stem for p in RAIZ.glob("*.py")}
    for pasta in PASTAS:
        nomes.add(pasta)
        for arq in (RAIZ / pasta).rglob("*.py"):
            nomes.add(arq.stem)
            nomes.update(d.name for d in arq.parents if d != RAIZ and RAIZ in d.parents)
    return nomes


def _declarados():
    nomes = set()
    for arq in RAIZ.glob("requirements*.txt"):
        for linha in arq.read_text().splitlines():
            linha = linha.split("#")[0].strip()
            if not linha or linha.startswith("-"):
                continue
            nomes.add(re.split(r"[\[<>=!~ ;]", linha, maxsplit=1)[0].lower().replace("_", "-"))
    return nomes


def _importados():
    achados = {}
    arquivos = [RAIZ / "pipeline.py", RAIZ / "tentativa.py"]
    for pasta in PASTAS:
        arquivos += (RAIZ / pasta).rglob("*.py")
    for arq in arquivos:
        arvore = ast.parse(arq.read_text(), filename=str(arq))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                modulos = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
                modulos = [no.module]
            else:
                continue
            for m in modulos:
                achados.setdefault(m.split(".")[0], arq.relative_to(RAIZ))
    return achados


def test_todo_import_de_terceiros_esta_nos_requirements():
    declarados = _declarados()
    do_projeto = _do_projeto()
    faltando = []
    for modulo, onde in sorted(_importados().items()):
        if modulo in sys.stdlib_module_names or modulo in do_projeto or modulo in DO_COMFYUI:
            continue
        pacote = PACOTE.get(modulo)
        if pacote is None:
            faltando.append(f"{modulo} (em {onde}): diga a qual pacote do pip ele pertence, em testes/test_requisitos.py")
        elif pacote not in declarados:
            faltando.append(f"{modulo} (em {onde}): acrescente {pacote} a um requirements*.txt")
    assert not faltando, "\n" + "\n".join(faltando)
