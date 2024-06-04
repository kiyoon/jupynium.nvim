from __future__ import annotations

import json
from collections.abc import Sequence
from os import PathLike


def load_ipynb(ipynb_path: str | PathLike):
    with open(ipynb_path) as f:
        ipynb = json.load(f)
    return ipynb


def read_ipynb_texts(ipynb, code_only: bool = False):
    texts = []
    cell_types = []
    for cell in ipynb["cells"]:
        if code_only and cell["cell_type"] != "code":
            continue
        cell_types.append(cell["cell_type"])
        texts.append("".join(cell["source"]))
    return cell_types, texts


def ipynb_language(ipynb):
    if (
        "metadata" in ipynb
        and "kernelspec" in ipynb["metadata"]
        and "language" in ipynb["metadata"]["kernelspec"]
    ):
        return ipynb["metadata"]["kernelspec"]["language"]

    return None


def cells_to_jupy(cell_types: list[str], texts: list[str]):
    cell_types_previous = ["code"] + cell_types[:-1]

    jupy: list[str] = []

    for cell_type_previous, cell_type, text in zip(
        cell_types_previous, cell_types, texts
    ):
        if cell_type == "code":
            if cell_type_previous == "code":
                jupy.append("# %%")
            else:
                jupy.append('%%"""')
        else:
            if cell_type_previous == "code":
                jupy.append('"""%%')
            else:
                jupy.append("# %%%")

        for line in text.split("\n"):
            if line.startswith("%"):
                line = "# " + line
            jupy.append(line)

    return jupy


def cells_to_jupytext(
    cell_types: Sequence[str], texts: Sequence[str], python: bool = True
):
    jupytext: list[str] = []

    for cell_type, text in zip(cell_types, texts):
        if cell_type == "code":
            jupytext.append("# %%")
            for line in text.split("\n"):
                if line.startswith("%"):
                    line = "# " + line
                jupytext.append(line)

            jupytext.append("")
        else:
            jupytext.append("# %% [markdown]")

            if python:
                jupytext.append('"""')
                for line in text.split("\n"):
                    jupytext.append(line)
                jupytext.append('"""')
            else:
                for line in text.split("\n"):
                    jupytext.append("# " + line)

            jupytext.append("")

    return jupytext


def ipynb2jupy(ipynb):
    """
    Deprecated. Use ipynb2jupytext instead.
    """
    cell_types, texts = read_ipynb_texts(ipynb)
    language = ipynb_language(ipynb)
    if language is None or language == "python":
        return cells_to_jupy(cell_types, texts)
    else:
        return cells_to_jupytext(cell_types, texts)


def ipynb2jupytext(ipynb, code_only=False):
    cell_types, texts = read_ipynb_texts(ipynb, code_only=code_only)
    language = ipynb_language(ipynb)
    if language is None or language == "python":
        python = True
    else:
        python = False

    return cells_to_jupytext(cell_types, texts, python)
