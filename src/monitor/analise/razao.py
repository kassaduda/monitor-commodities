"""Razão de preços soja/milho (US$/t ÷ US$/t), mensal."""

import pandas as pd

from monitor.limpeza import COLUNAS_PADRAO

UNIDADE_RAZAO = "razão soja/milho (US$/t ÷ US$/t, adimensional)"


def razao_soja_milho(soja: pd.DataFrame, milho: pd.DataFrame) -> pd.DataFrame:
    """Preço da soja ÷ preço do milho nos meses presentes nas duas séries (ambas em US$/t)."""
    for nome, df in (("soja", soja), ("milho", milho)):
        if list(df["unidade"].unique()) != ["US$/t"]:
            raise ValueError(f"{nome}: esperada a unidade 'US$/t', encontrada {list(df['unidade'].unique())}")
    juntos = soja[["data", "valor"]].merge(milho[["data", "valor"]], on="data", suffixes=("_soja", "_milho"))
    if (juntos["valor_milho"] <= 0).any():
        raise ValueError("Preço do milho não positivo: razão indefinida")
    out = pd.DataFrame({"data": juntos["data"], "valor": juntos["valor_soja"] / juntos["valor_milho"]})
    out["serie"] = "razao_soja_milho"
    out["unidade"] = UNIDADE_RAZAO
    out["fonte"] = f"{soja['fonte'].iloc[0]}; {milho['fonte'].iloc[0]}"
    return out.sort_values("data", ignore_index=True)[COLUNAS_PADRAO]
