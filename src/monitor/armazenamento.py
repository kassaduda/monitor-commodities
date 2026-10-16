"""Armazenamento das séries limpas em Parquet (um arquivo por série em data/processed/)."""

import json
from pathlib import Path

import pandas as pd

from monitor.limpeza import COLUNAS_PADRAO, dataframe_vazio


def caminho_parquet(dir_processed: Path, serie: str) -> Path:
    return dir_processed / f"{serie}.parquet"


def ler_serie(caminho: Path) -> pd.DataFrame:
    """Lê a série salva; devolve DataFrame vazio tipado se o arquivo não existir."""
    if not caminho.exists():
        return dataframe_vazio()
    return pd.read_parquet(caminho)[COLUNAS_PADRAO]


def mesclar(existente: pd.DataFrame, novo: pd.DataFrame) -> pd.DataFrame:
    """Junta as duas tabelas sem duplicar datas; em datas repetidas vale o dado novo."""
    for nome, df in (("existente", existente), ("novo", novo)):
        if list(df.columns) != COLUNAS_PADRAO:
            raise ValueError(f"DataFrame {nome} fora do formato padrão: {list(df.columns)}")
    partes = [df for df in (existente, novo) if not df.empty]
    if not partes:
        return dataframe_vazio()
    series = pd.concat([df["serie"] for df in partes]).unique()
    if len(series) > 1:
        raise ValueError(f"Mistura de séries diferentes: {sorted(series)}")
    combinado = pd.concat(partes, ignore_index=True)
    combinado = combinado.drop_duplicates(subset="data", keep="last")
    return combinado.sort_values("data", ignore_index=True)


def salvar_serie(df: pd.DataFrame, caminho: Path) -> bool:
    """Grava o Parquet só se o conteúdo mudou. Retorna True se o arquivo foi (re)escrito."""
    if caminho.exists() and ler_serie(caminho).equals(df):
        return False
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    df.to_parquet(temporario, index=False, compression="zstd")
    temporario.replace(caminho)
    return True


def caminho_edicoes(dir_processed: Path) -> Path:
    return dir_processed / "_edicoes.json"


def ler_json(caminho: Path) -> dict:
    """Lê um JSON de metadados; devolve {} se o arquivo não existir."""
    if not caminho.exists():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar_json(dados: dict, caminho: Path) -> bool:
    """Grava o JSON só se o conteúdo mudou. Retorna True se o arquivo foi (re)escrito."""
    if ler_json(caminho) == dados:
        return False
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporario.replace(caminho)
    return True
