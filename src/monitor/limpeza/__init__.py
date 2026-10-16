"""Limpeza: converte dados brutos no formato padrão (data, serie, valor, unidade, fonte)."""

import pandas as pd

COLUNAS_PADRAO: list[str] = ["data", "serie", "valor", "unidade", "fonte"]


def dataframe_vazio() -> pd.DataFrame:
    """DataFrame sem linhas, já com as colunas e tipos do formato padrão."""
    return pd.DataFrame(columns=COLUNAS_PADRAO).astype({"data": "datetime64[ns]", "valor": "float64"})
