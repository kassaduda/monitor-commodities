"""Orquestra coleta -> limpeza -> armazenamento.

Uso: python -m monitor.pipeline
"""

import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import requests

from monitor import config
from monitor.armazenamento import (
    caminho_edicoes,
    caminho_parquet,
    ler_json,
    ler_serie,
    mesclar,
    salvar_json,
    salvar_serie,
)
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


CHAVE_EDICAO_WB = "wb_pink_sheet"
URL_PINK_SHEET = "https://www.worldbank.org/en/research/commodity-markets"


class EdicaoInvalida(ValueError):
    """Arquivo do Pink Sheet sem data de edição ou mais antigo que o último processado."""


def verificar_edicao(atualizado_em: date | None, ultima_processada: str | None, arquivo: Path) -> None:
    """Recusa arquivo sem data "Updated on" ou de edição anterior à última processada.

    Edição igual é aceita (reprocessar é idempotente); edição mais nova é aceita.
    """
    if atualizado_em is None:
        raise EdicaoInvalida(
            f"Pink Sheet recusado: {arquivo.name} não tem a linha \"Updated on ...\", então não dá "
            f"para saber de qual edição ele é. Nada foi alterado. Baixe o arquivo oficial em {URL_PINK_SHEET}."
        )
    if ultima_processada and atualizado_em < date.fromisoformat(ultima_processada):
        ultima = date.fromisoformat(ultima_processada)
        raise EdicaoInvalida(
            f"Pink Sheet recusado: {arquivo.name} é da edição de {atualizado_em:%d/%m/%Y}, mais antiga "
            f"que a última processada ({ultima:%d/%m/%Y}). Usá-lo desfaria revisões já salvas. "
            f"Nada foi alterado. Baixe a edição mais recente em {URL_PINK_SHEET}."
        )


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

    caminho_ed = caminho_edicoes(dir_processed)
    edicoes = ler_json(caminho_ed)
    verificar_edicao(planilha.atualizado_em, edicoes.get(CHAVE_EDICAO_WB), arquivo)

    # Limpa todas as séries antes de gravar qualquer uma: um erro não deixa soja e milho dessincronizados.
    novos = {serie: limpar_pink_sheet(planilha.series[coluna], serie) for serie, coluna in config.WB_SERIES.items()}
    resultados = []
    for serie, novo in novos.items():
        caminho = caminho_parquet(dir_processed, serie)
        existente = ler_serie(caminho)
        combinado = mesclar(existente, novo)
        alterado = salvar_serie(combinado, caminho)
        resultados.append(ResultadoAtualizacao(caminho, len(combinado) - len(existente), len(combinado), alterado))
    # Registrada só depois dos Parquet: se algo falhar antes, a mesma edição pode ser reprocessada.
    salvar_json({**edicoes, CHAVE_EDICAO_WB: planilha.atualizado_em.isoformat()}, caminho_ed)
    return resultados


def _imprimir(r: ResultadoAtualizacao) -> None:
    estado = "atualizado" if r.alterado else "sem mudanças"
    print(f"{r.caminho.name}: {estado}, {r.linhas_novas} linhas novas, {r.total_linhas} no total")


def main() -> int:
    _imprimir(atualizar_dolar())
    try:
        resultados_wb = atualizar_pink_sheet()
    except EdicaoInvalida as exc:
        print(exc, file=sys.stderr)
        return 1
    if not resultados_wb:
        print(f"Pink Sheet: arquivo não encontrado em {caminho_arquivo()}; baixe-o em "
              f"{URL_PINK_SHEET} (Monthly prices, XLS)")
    for r in resultados_wb:
        _imprimir(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
