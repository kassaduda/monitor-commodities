import hashlib
import shutil
from datetime import date

import pandas as pd

from monitor.armazenamento import ler_serie
from monitor.pipeline import atualizar_dolar

HOJE = date(2026, 10, 14)


def _sha256(caminho) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _rodar(tmp_path, hoje: date):
    return atualizar_dolar(dir_raw=tmp_path / "raw", dir_processed=tmp_path / "processed", hoje=hoje)


def test_primeira_execucao_cria_parquet_desde_2010(api, tmp_path) -> None:
    r = _rodar(tmp_path, HOJE)
    df = ler_serie(r.caminho)
    assert r.alterado and r.caminho.name == "ptax_venda.parquet"
    assert r.linhas_novas == r.total_linhas == len(df)
    assert df["data"].min() == pd.Timestamp("2010-01-05")
    assert df["data"].max() == pd.Timestamp("2026-10-05")
    assert df["data"].is_unique


def test_idempotente_duas_execucoes_seguidas_nao_mudam_o_arquivo(api, tmp_path) -> None:
    r1 = _rodar(tmp_path, HOJE)
    hash_antes, mtime_antes = _sha256(r1.caminho), r1.caminho.stat().st_mtime_ns
    api.clear()

    r2 = _rodar(tmp_path, HOJE)

    assert api == []  # nada a buscar: o Parquet já está em dia
    assert r2.alterado is False and r2.linhas_novas == 0
    assert _sha256(r2.caminho) == hash_antes
    assert r2.caminho.stat().st_mtime_ns == mtime_antes


def test_incremental_busca_so_o_que_falta_e_nao_duplica(api, tmp_path) -> None:
    r1 = _rodar(tmp_path, HOJE)
    api.clear()

    r2 = _rodar(tmp_path, date(2026, 10, 21))

    assert api == [(date(2026, 1, 1), date(2026, 10, 21))]  # só o ano corrente
    df = ler_serie(r2.caminho)
    assert r2.linhas_novas == 1 and r2.total_linhas == r1.total_linhas + 1
    assert df["data"].max() == pd.Timestamp("2026-10-20")
    assert df["data"].is_unique


def test_clone_novo_sem_cache_bruto_nao_baixa_o_historico(api, tmp_path) -> None:
    """No Streamlit Cloud / clone novo só existe o Parquet: deve buscar apenas o trecho recente."""
    _rodar(tmp_path, HOJE)
    shutil.rmtree(tmp_path / "raw")
    api.clear()

    r = _rodar(tmp_path, date(2026, 10, 21))

    assert api == [(date(2026, 1, 1), date(2026, 10, 21))]
    assert r.linhas_novas == 1
    assert ler_serie(r.caminho)["data"].is_unique
