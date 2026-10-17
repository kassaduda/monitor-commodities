import hashlib
import shutil
from datetime import date

import pandas as pd

from pathlib import Path

import pytest

from monitor import config, pipeline
from monitor.armazenamento import caminho_edicoes, caminho_parquet, ler_json, ler_serie
from monitor.coleta.worldbank import caminho_arquivo
from monitor.pipeline import EdicaoInvalida, atualizar_dolar, atualizar_pink_sheet
from pink_sheet_util import criar_planilha

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


# --- Pink Sheet ------------------------------------------------------------------

EDICAO_OUT = [  # [período, WTI, soja, milho]
    ["2026M07", 65.0, 478, 213.4],
    ["2026M08", 63.1, 482, 224],
    ["2026M09", 62.0, 524, 239.6],
]


def _pink(tmp_path, linhas, atualizado: str = "Updated on October 02, 2026"):
    criar_planilha(caminho_arquivo(tmp_path / "raw"), linhas, atualizado=atualizado)
    return atualizar_pink_sheet(dir_raw=tmp_path / "raw", dir_processed=tmp_path / "processed")


def _estado(tmp_path) -> dict[str, tuple[str, int]]:
    """Hash e mtime de tudo em data/processed (Parquet e _edicoes.json)."""
    return {p.name: (_sha256(p), p.stat().st_mtime_ns) for p in sorted((tmp_path / "processed").iterdir())}


def test_pink_sheet_sem_arquivo_nao_faz_nada(tmp_path) -> None:
    assert atualizar_pink_sheet(dir_raw=tmp_path / "raw", dir_processed=tmp_path / "processed") == []
    assert not (tmp_path / "processed").exists()


def test_pink_sheet_cria_parquets_de_soja_milho_e_trigo(tmp_path) -> None:
    resultados = _pink(tmp_path, EDICAO_OUT)
    assert [r.caminho.name for r in resultados] == ["wb_soja.parquet", "wb_milho.parquet", "wb_trigo.parquet"]
    assert ler_serie(resultados[2].caminho)["valor"].tolist() == [250.0] * 3  # valor padrão do trigo nas planilhas sintéticas
    soja = ler_serie(resultados[0].caminho)
    milho = ler_serie(resultados[1].caminho)
    assert soja["valor"].tolist() == [478.0, 482.0, 524.0]
    assert milho["valor"].tolist() == [213.4, 224.0, 239.6]
    assert (soja["unidade"] == config.WB_UNIDADE).all()
    assert all(r.alterado and r.linhas_novas == 3 for r in resultados)


def test_pink_sheet_idempotente_duas_execucoes_nao_mudam_os_arquivos(tmp_path) -> None:
    r1 = _pink(tmp_path, EDICAO_OUT)
    antes = [(_sha256(r.caminho), r.caminho.stat().st_mtime_ns) for r in r1]

    r2 = atualizar_pink_sheet(dir_raw=tmp_path / "raw", dir_processed=tmp_path / "processed")

    assert all(not r.alterado and r.linhas_novas == 0 for r in r2)
    assert [(_sha256(r.caminho), r.caminho.stat().st_mtime_ns) for r in r2] == antes


def test_pink_sheet_nova_edicao_acrescenta_mes_e_aplica_revisao(tmp_path) -> None:
    _pink(tmp_path, EDICAO_OUT)
    edicao_nov = [
        ["2026M08", 63.1, 482, 224],
        ["2026M09", 62.0, 521, 239.6],  # revisão da soja de set/2026
        ["2026M10", 61.5, 530, 241.0],
    ]
    r_soja, r_milho, _r_trigo = _pink(tmp_path, edicao_nov, atualizado="Updated on November 03, 2026")

    soja = ler_serie(r_soja.caminho)
    assert soja["data"].is_unique
    assert soja["data"].dt.strftime("%Y-%m").tolist() == ["2026-07", "2026-08", "2026-09", "2026-10"]
    assert soja["valor"].tolist() == [478.0, 482.0, 521.0, 530.0]  # jul/2026 mantido, set revisado
    assert r_soja.linhas_novas == 1 and r_milho.linhas_novas == 1
    assert ler_json(caminho_edicoes(tmp_path / "processed")) == {"wb_pink_sheet": "2026-11-03"}


# --- Pink Sheet: controle de edição --------------------------------------------------


def test_pink_sheet_registra_a_data_da_edicao(tmp_path) -> None:
    _pink(tmp_path, EDICAO_OUT)
    assert ler_json(caminho_edicoes(tmp_path / "processed")) == {"wb_pink_sheet": "2026-10-02"}


def test_pink_sheet_recusa_edicao_mais_antiga_sem_alterar_nada(tmp_path) -> None:
    _pink(tmp_path, EDICAO_OUT)
    antes = _estado(tmp_path)

    with pytest.raises(EdicaoInvalida) as exc:
        _pink(tmp_path, [["2026M08", 63.1, 400, 200]], atualizado="Updated on September 02, 2026")

    msg = str(exc.value)
    assert "02/09/2026" in msg and "02/10/2026" in msg
    assert "mais antiga" in msg and "Nada foi alterado" in msg
    assert config.WB_ARQUIVO in msg
    assert _estado(tmp_path) == antes  # Parquet e _edicoes.json intactos
    assert ler_serie(caminho_parquet(tmp_path / "processed", "wb_soja"))["valor"].tolist() == [478.0, 482.0, 524.0]


def test_pink_sheet_mesma_edicao_e_aceita_sem_mudar_arquivos(tmp_path) -> None:
    _pink(tmp_path, EDICAO_OUT)
    antes = _estado(tmp_path)
    resultados = _pink(tmp_path, EDICAO_OUT)
    assert all(not r.alterado for r in resultados)
    assert _estado(tmp_path) == antes


def test_pink_sheet_recusa_arquivo_sem_data_de_edicao(tmp_path) -> None:
    with pytest.raises(EdicaoInvalida, match="Updated on"):
        _pink(tmp_path, EDICAO_OUT, atualizado="")
    assert not (tmp_path / "processed").exists()


def test_pink_sheet_sem_registro_anterior_aceita_e_registra(tmp_path) -> None:
    """Parquet já existente sem _edicoes.json (estado do commit c4f1212) é aceito."""
    _pink(tmp_path, EDICAO_OUT)
    caminho_edicoes(tmp_path / "processed").unlink()
    _pink(tmp_path, EDICAO_OUT)
    assert ler_json(caminho_edicoes(tmp_path / "processed")) == {"wb_pink_sheet": "2026-10-02"}


def test_main_mostra_mensagem_e_sai_com_erro_para_edicao_antiga(tmp_path, monkeypatch, capsys) -> None:
    _pink(tmp_path, EDICAO_OUT)
    criar_planilha(caminho_arquivo(tmp_path / "raw"), EDICAO_OUT, atualizado="Updated on September 02, 2026")
    monkeypatch.setattr(pipeline, "atualizar_dolar", lambda: pipeline.ResultadoAtualizacao(Path("ptax_venda.parquet"), 0, 1, False))
    monkeypatch.setattr(pipeline, "atualizar_pink_sheet",
                        lambda: atualizar_pink_sheet(dir_raw=tmp_path / "raw", dir_processed=tmp_path / "processed"))

    assert pipeline.main() == 1
    assert "mais antiga que a última processada (02/10/2026)" in capsys.readouterr().err
