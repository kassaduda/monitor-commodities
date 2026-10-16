"""Orquestra coleta -> limpeza -> armazenamento.

Uso: python -m monitor.pipeline
"""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import requests

from monitor import config
from monitor.armazenamento import caminho_parquet, ler_serie, mesclar, salvar_serie
from monitor.coleta.bcb import coletar_sgs
from monitor.coleta.worldbank import caminho_arquivo, ler_pink_sheet
from monitor.limpeza.bcb import limpar_sgs
from monitor.limpeza.worldbank import limpar_pink_sheet


@dataclass(frozen=True)
class ResultadoAtualizacao:
    caminho: Path
    linhas_novas: int
    total_linhas: int
    alterado: bool


def atualizar_dolar(
    *,
    dir_raw: Path = config.DIR_RAW,
    dir_processed: Path = config.DIR_PROCESSED,
    hoje: date | None = None,
    session: requests.Session | None = None,
) -> ResultadoAtualizacao:
    """Atualiza data/processed/ptax_venda.parquet buscando só as datas após a última salva.

    O ponto de partida é o Parquet (que vai no repositório), não o cache bruto (que não vai):
    assim um clone novo também só busca o que falta.
    """
    serie = "ptax_venda"
    caminho = caminho_parquet(dir_processed, serie)
    existente = ler_serie(caminho)
    inicio = config.DATA_INICIO if existente.empty else existente["data"].max().date() + timedelta(days=1)

    registros = coletar_sgs(config.BCB_SERIES[serie], inicio, dir_raw=dir_raw, session=session, hoje=hoje)
    novo = limpar_sgs(registros, serie, config.BCB_SERIE_1_UNIDADE, config.FONTE_BCB)
    combinado = mesclar(existente, novo)
    alterado = salvar_serie(combinado, caminho)
    return ResultadoAtualizacao(caminho, len(combinado) - len(existente), len(combinado), alterado)


def atualizar_pink_sheet(
    *,
    dir_raw: Path = config.DIR_RAW,
    dir_processed: Path = config.DIR_PROCESSED,
) -> list[ResultadoAtualizacao]:
    """Atualiza wb_soja.parquet e wb_milho.parquet a partir do arquivo local do Pink Sheet.

    O arquivo traz o histórico completo; a mesclagem acrescenta meses novos e aplica revisões
    de meses já salvos, sem duplicar datas. Sem arquivo local, não faz nada (lista vazia).
    """
    arquivo = caminho_arquivo(dir_raw)
    if not arquivo.exists():
        return []
    planilha = ler_pink_sheet(arquivo, list(config.WB_SERIES.values()))
    resultados = []
    for serie, coluna in config.WB_SERIES.items():
        caminho = caminho_parquet(dir_processed, serie)
        existente = ler_serie(caminho)
        combinado = mesclar(existente, limpar_pink_sheet(planilha.series[coluna], serie))
        alterado = salvar_serie(combinado, caminho)
        resultados.append(ResultadoAtualizacao(caminho, len(combinado) - len(existente), len(combinado), alterado))
    return resultados


def _imprimir(r: ResultadoAtualizacao) -> None:
    estado = "atualizado" if r.alterado else "sem mudanças"
    print(f"{r.caminho.name}: {estado}, {r.linhas_novas} linhas novas, {r.total_linhas} no total")


def main() -> None:
    _imprimir(atualizar_dolar())
    resultados_wb = atualizar_pink_sheet()
    if not resultados_wb:
        print(f"Pink Sheet: arquivo não encontrado em {caminho_arquivo()}; baixe-o em "
              "https://www.worldbank.org/en/research/commodity-markets (Monthly prices, XLS)")
    for r in resultados_wb:
        _imprimir(r)


if __name__ == "__main__":
    main()
