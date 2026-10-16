"""Limpeza de uma série do Pink Sheet: período "AAAAMmm" -> data (1º dia do mês), valor float."""

import pandas as pd

from monitor import config
from monitor.coleta.worldbank import SeriePinkSheet
from monitor.limpeza import COLUNAS_PADRAO, dataframe_vazio

# Marcadores de valor ausente usados no arquivo ("…" é U+2026).
MARCADORES_AUSENTE = frozenset({"", "…", "...", ".."})


def periodo_para_data(periodo: str) -> pd.Timestamp:
    ano, mes = periodo.split("M")
    return pd.Timestamp(year=int(ano), month=int(mes), day=1)


def _valor(celula: object, periodo: str) -> float | None:
    if celula is None:
        return None
    if isinstance(celula, bool):
        raise ValueError(f"{periodo}: valor booleano inesperado")
    if isinstance(celula, int | float):
        return float(celula)
    texto = str(celula).strip()
    if texto in MARCADORES_AUSENTE:
        return None
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"{periodo}: valor não numérico {texto!r}") from None


def limpar_pink_sheet(
    serie_ps: SeriePinkSheet,
    serie: str,
    *,
    unidade_arquivo: str = config.WB_UNIDADE_ARQUIVO,
    unidade: str = config.WB_UNIDADE,
    fonte: str = config.FONTE_WB,
) -> pd.DataFrame:
    """Converte para o formato padrão. Meses marcados como ausentes são omitidos.

    Levanta ValueError se a unidade mudar, se houver valor não numérico (ex.: "#VALUE!"),
    não positivo ou período repetido.
    """
    if serie_ps.unidade != unidade_arquivo:
        raise ValueError(f"{serie_ps.nome}: unidade {serie_ps.unidade!r}, esperada {unidade_arquivo!r}")

    periodos = [p for p, _ in serie_ps.registros]
    if len(periodos) != len(set(periodos)):
        raise ValueError(f"{serie_ps.nome}: períodos repetidos no arquivo")

    pares = [(periodo_para_data(p), _valor(v, p)) for p, v in serie_ps.registros]
    pares = [(d, v) for d, v in pares if v is not None]
    if not pares:
        return dataframe_vazio()
    if any(v <= 0 for _, v in pares):
        raise ValueError(f"{serie_ps.nome}: valores não positivos")

    df = pd.DataFrame(pares, columns=["data", "valor"]).sort_values("data", ignore_index=True)
    df["data"] = df["data"].astype("datetime64[ns]")
    df["serie"] = serie
    df["unidade"] = unidade
    df["fonte"] = fonte
    return df[COLUNAS_PADRAO]
