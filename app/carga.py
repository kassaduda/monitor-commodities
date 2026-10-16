"""Leitura dos arquivos para o dashboard. Só lê Parquet/JSON do repositório; não recalcula nem baixa."""

import json

import pandas as pd
import streamlit as st

from monitor import config
from monitor.analise.base import BaseMensal, montar_base
from monitor.armazenamento import caminho_parquet, ler_serie
from monitor.resultados import ARQUIVO_META, ARQUIVOS


@st.cache_data
def dolar_diario() -> pd.DataFrame:
    return ler_serie(caminho_parquet(config.DIR_PROCESSED, "ptax_venda"))


@st.cache_data
def base_mensal() -> BaseMensal:
    return montar_base(config.DIR_PROCESSED)


@st.cache_data
def resultado(nome: str) -> pd.DataFrame:
    return pd.read_parquet(config.DIR_PROCESSED / ARQUIVOS[nome])


@st.cache_data
def meta() -> dict:
    return json.loads((config.DIR_PROCESSED / ARQUIVO_META).read_text(encoding="utf-8"))
