"""Variação mensal (%) e retorno logarítmico de séries mensais."""

import numpy as np
import pandas as pd

from monitor.limpeza import COLUNAS_PADRAO


def variacao_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Variação percentual sobre o mês anterior. Unidade: "% m/m (<unidade original>)"."""
    return _transformar(df, lambda v: (v / v.shift(1) - 1) * 100, "var_mensal", "% m/m")


def retorno_log(df: pd.DataFrame) -> pd.DataFrame:
    """ln(v_t / v_{t-1}). Unidade: "log-retorno mensal (<unidade original>)"."""
    return _transformar(df, lambda v: np.log(v / v.shift(1)), "ret_log", "log-retorno mensal")


def _transformar(df: pd.DataFrame, f, sufixo: str, rotulo: str) -> pd.DataFrame:
    if df["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única unidade")
    df = df.sort_values("data", ignore_index=True)
    _exigir_meses_consecutivos(df)
    out = df.copy()
    out["valor"] = f(df["valor"])
    out["serie"] = df["serie"] + f"_{sufixo}"
    out["unidade"] = f"{rotulo} ({df['unidade'].iloc[0]})"
    return out.dropna(subset=["valor"]).reset_index(drop=True)[COLUNAS_PADRAO]


def _exigir_meses_consecutivos(df: pd.DataFrame) -> None:
    """Uma variação entre meses não consecutivos misturaria horizontes diferentes."""
    indice_mes = df["data"].dt.year * 12 + df["data"].dt.month
    if not (indice_mes.diff().dropna() == 1).all():
        raise ValueError("A série mensal tem meses faltando ou repetidos")
