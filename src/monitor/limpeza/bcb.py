"""Limpeza dos registros brutos do SGS: {"data": "dd/mm/aaaa", "valor": "5.0441"}."""

import pandas as pd

from monitor.limpeza import COLUNAS_PADRAO, dataframe_vazio


def limpar_sgs(registros: list[dict[str, str]], serie: str, unidade: str, fonte: str) -> pd.DataFrame:
    """Converte data e valor para os tipos certos, ordena por data e remove datas duplicadas.

    Levanta ValueError se alguma data ou valor não puder ser convertido (em vez de descartar
    silenciosamente).
    """
    if not registros:
        return dataframe_vazio()

    bruto = pd.DataFrame(registros)
    faltando = {"data", "valor"} - set(bruto.columns)
    if faltando:
        raise ValueError(f"Registros do SGS sem as colunas {sorted(faltando)}")

    df = pd.DataFrame(
        {
            "data": pd.to_datetime(bruto["data"].str.strip(), format="%d/%m/%Y", errors="raise"),
            "valor": pd.to_numeric(bruto["valor"].str.strip(), errors="raise").astype("float64"),
        }
    )
    if df["valor"].isna().any():  # to_numeric converte "" em NaN sem levantar erro
        raise ValueError("Valores vazios na série do SGS")
    if (df["valor"] <= 0).any():
        raise ValueError("Valores não positivos na série do SGS")

    df = df.drop_duplicates(subset="data", keep="last").sort_values("data", ignore_index=True)
    df["serie"] = serie
    df["unidade"] = unidade
    df["fonte"] = fonte
    return df[COLUNAS_PADRAO]
