"""Monta planilhas sintéticas no layout do Pink Sheet para os testes."""

from pathlib import Path

from openpyxl import Workbook

CABECALHO = [None, "Crude oil, WTI", "Soybeans", "Maize", "Wheat, US HRW"]
UNIDADES = [None, "($/bbl)", "($/mt)", "($/mt)", "($/mt)"]
TRIGO_PADRAO = 250.0  # linhas de 4 colunas ([período, wti, soja, milho]) ganham o trigo com este valor


def criar_planilha(
    caminho: Path,
    linhas: list[list],
    *,
    cabecalho: list | None = None,
    unidades: list | None = None,
    aba: str = "Monthly Prices",
    atualizado: str = "Updated on October 02, 2026",
) -> Path:
    """`linhas`: [[período, wti, soja, milho(, trigo)], ...] logo abaixo das unidades."""
    wb = Workbook()
    ws = wb.active
    ws.title = aba
    ws.append(["World Bank Commodity Price Data (The Pink Sheet)"])
    ws.append(["monthly prices in nominal US dollars, 1960 to present"])
    ws.append(["(monthly series are available only in nominal US dollars)"])
    ws.append([atualizado])
    ws.append(cabecalho or CABECALHO)
    ws.append(unidades or UNIDADES)
    for linha in linhas:
        ws.append(linha + [TRIGO_PADRAO] if cabecalho is None and len(linha) == 4 else linha)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho
