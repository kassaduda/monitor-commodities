"""Agregação mensal e recorte no período em comum entre séries."""

import pandas as pd

from monitor import config
from monitor.limpeza import COLUNAS_PADRAO


def media_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Média dos valores de cada mês, datada no 1º dia do mês. Unidade e fonte preservadas.

    Atenção: o mês corrente sai como média parcial; use `periodo_comum` para descartá-lo.
    """
    if df.empty:
        return df.copy()
    _exigir_uma_serie(df)
    mensal = df.groupby(df["data"].dt.to_period("M"))["valor"].mean()
    out = pd.DataFrame({"data": mensal.index.to_timestamp().astype("datetime64[ns]"), "valor": mensal.to_numpy()})
    out["serie"] = f"{df['serie'].iloc[0]}_media_mensal"
    out["unidade"] = df["unidade"].iloc[0]
    out["fonte"] = df["fonte"].iloc[0]
    return out[COLUNAS_PADRAO]


def periodo_comum(*dfs: pd.DataFrame, inicio_minimo: pd.Timestamp | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Maior início e menor fim entre as séries (e não antes de `inicio_minimo`, padrão 2010-01)."""
    if not dfs or any(df.empty for df in dfs):
        raise ValueError("Todas as séries precisam ter dados para calcular o período em comum")
    piso = inicio_minimo if inicio_minimo is not None else pd.Timestamp(config.DATA_INICIO)
    inicio = max([piso, *(df["data"].min() for df in dfs)])
    fim = min(df["data"].max() for df in dfs)
    if inicio > fim:
        raise ValueError(f"Séries sem período em comum (início {inicio:%Y-%m} > fim {fim:%Y-%m})")
    return inicio, fim


def recortar(df: pd.DataFrame, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    return df[(df["data"] >= inicio) & (df["data"] <= fim)].reset_index(drop=True)


def _exigir_uma_serie(df: pd.DataFrame) -> None:
    if df["serie"].nunique() != 1 or df["unidade"].nunique() != 1:
        raise ValueError("Esperada uma única série com uma única unidade")
