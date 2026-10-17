"""Texto de interface com `$` escapado. O Streamlit lê `$...$` como LaTeX, e "R$/US$" tem dois cifrões.

Todo texto de interface passa por aqui (nunca por `st.markdown`, `st.caption` etc. direto); o teste
`tests/test_app.py` falha se algum texto chegar à tela com `$` sem escape. Gráficos Plotly não passam por aqui.
"""

import re

import streamlit as st

_CIFRAO_SEM_ESCAPE = re.compile(r"(?<!\\)\$")


def escapar(texto: str) -> str:
    r"""Troca `$` por `\$` (idempotente: não duplica a barra de um cifrão já escapado)."""
    return _CIFRAO_SEM_ESCAPE.sub(r"\\$", texto)


def markdown(texto: str) -> None:
    st.markdown(escapar(texto))


def caption(texto: str) -> None:
    st.caption(escapar(texto))


def subheader(texto: str) -> None:
    st.subheader(escapar(texto))


def title(texto: str) -> None:
    st.title(escapar(texto))


def info(texto: str, **kw) -> None:
    st.info(escapar(texto), **kw)


def warning(texto: str, **kw) -> None:
    st.warning(escapar(texto), **kw)


def success(texto: str, **kw) -> None:
    st.success(escapar(texto), **kw)


def error(texto: str, **kw) -> None:
    st.error(escapar(texto), **kw)


def metric(destino, rotulo: str, valor: str, **kw) -> None:
    """`destino` é `st` ou uma coluna (`st.columns`)."""
    if "help" in kw:
        kw["help"] = escapar(kw["help"])
    if "delta" in kw:
        kw["delta"] = escapar(kw["delta"])
    destino.metric(escapar(rotulo), escapar(valor), **kw)


def html(texto: str) -> None:
    """HTML próprio (selos, banners). O `$` vira entidade, que o Streamlit não lê como LaTeX."""
    st.markdown(texto.replace("$", "&#36;"), unsafe_allow_html=True)


def radio(rotulo: str, opcoes: list[str], **kw) -> str:
    return st.radio(escapar(rotulo), opcoes, format_func=escapar, **kw)


def selectbox(rotulo: str, opcoes: list[str], **kw) -> str:
    return st.selectbox(escapar(rotulo), opcoes, format_func=escapar, **kw)


def expander(rotulo: str):
    return st.expander(escapar(rotulo))
