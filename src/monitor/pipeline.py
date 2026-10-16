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
from monitor.limpeza.bcb import limpar_sgs


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


def main() -> None:
    r = atualizar_dolar()
    estado = "atualizado" if r.alterado else "sem mudanças"
    print(f"{r.caminho.name}: {estado}, {r.linhas_novas} linhas novas, {r.total_linhas} no total")


if __name__ == "__main__":
    main()
