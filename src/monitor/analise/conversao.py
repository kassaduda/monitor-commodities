"""Conversão de moeda (US$ -> R$ pela PTAX média do mês) e de unidade (t -> saca de 60 kg)."""

import pandas as pd

from monitor.limpeza import COLUNAS_PADRAO

KG_POR_TONELADA = 1000
KG_POR_SACA = 60
UNIDADE_CAMBIO = "R$/US$"

_PARA_SACA = {"US$/t": "US$/sc 60 kg", "R$/t": "R$/sc 60 kg"}


def converter_para_reais(preco: pd.DataFrame, cambio_mensal: pd.DataFrame) -> pd.DataFrame:
    """R$/t = US$/t × (R$/US$ médio do mês). Exige câmbio para todos os meses do preço."""
    _exigir_unidade(preco, "US$/t")
    _exigir_unidade(cambio_mensal, UNIDADE_CAMBIO)
    faltando = sorted(set(preco["data"]) - set(cambio_mensal["data"]))
    if faltando:
        meses = ", ".join(f"{d:%Y-%m}" for d in faltando[:5])
        raise ValueError(f"Câmbio ausente para {len(faltando)} mês(es) do preço: {meses}")

    juntos = preco.merge(cambio_mensal[["data", "valor"]], on="data", suffixes=("", "_cambio"))
    out = pd.DataFrame({"data": juntos["data"], "valor": juntos["valor"] * juntos["valor_cambio"]})
    out["serie"] = f"{preco['serie'].iloc[0]}_brl"
    out["unidade"] = "R$/t"
    out["fonte"] = f"{preco['fonte'].iloc[0]}; câmbio: {cambio_mensal['fonte'].iloc[0]}"
    return out[COLUNAS_PADRAO]


def tonelada_para_saca(df: pd.DataFrame) -> pd.DataFrame:
    """Converte US$/t ou R$/t para a mesma moeda por saca de 60 kg (× 60/1000)."""
    unidade = _unidade_unica(df)
    if unidade not in _PARA_SACA:
        raise ValueError(f"Unidade {unidade!r} não é por tonelada ({sorted(_PARA_SACA)})")
    out = df.copy()
    out["valor"] = df["valor"] * KG_POR_SACA / KG_POR_TONELADA
    out["serie"] = df["serie"] + "_sc60"
    out["unidade"] = _PARA_SACA[unidade]
    return out[COLUNAS_PADRAO]


def _unidade_unica(df: pd.DataFrame) -> str:
    unidades = df["unidade"].unique()
    if len(unidades) != 1:
        raise ValueError(f"Esperada uma única unidade, encontradas {list(unidades)}")
    return str(unidades[0])


def _exigir_unidade(df: pd.DataFrame, esperada: str) -> None:
    unidade = _unidade_unica(df)
    if unidade != esperada:
        raise ValueError(f"Série {df['serie'].iloc[0]!r} em {unidade!r}, esperada {esperada!r}")
