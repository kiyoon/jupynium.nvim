from __future__ import annotations

import json


def load_ipynb(ipynb_path):
    with open(ipynb_path, "r") as f:
        ipynb = json.load(f)
    return ipynb


def read_ipynb_texts(ipynb, code_only=False):
    texts = []
    cell_types = []
    for cell in ipynb["cells"]:
        if code_only:
            if cell["cell_type"] != "code":
                continue
        cell_types.append(cell["cell_type"])
        texts.append("".join(cell["source"]))
    return cell_types, texts


def ipynb_language(ipynb):
    if "metadata" in ipynb:
        if "kernelspec" in ipynb["metadata"]:
            if "language" in ipynb["metadata"]["kernelspec"]:
                return ipynb["metadata"]["kernelspec"]["language"]

    return None


def cells_to_jupy(cell_types, texts):
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


def cells_to_jupytext(cell_types, texts, python=True):
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
