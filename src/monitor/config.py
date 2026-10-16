"""Configuração central: caminhos, período e códigos das séries."""

from datetime import date
from pathlib import Path

RAIZ: Path = Path(__file__).resolve().parents[2]
DIR_DADOS: Path = RAIZ / "data"
DIR_RAW: Path = DIR_DADOS / "raw"
DIR_PROCESSED: Path = DIR_DADOS / "processed"

DATA_INICIO: date = date(2010, 1, 1)

# BCB SGS 1. Desde 01/07/2011 é a PTAX de fechamento (venda); conferido contra a API PTAX/Olinda.
BCB_SERIES: dict[str, int] = {
    "ptax_venda": 1,
}
# Nome exato devolvido pelos metadados do SGS (campo nomeCompleto); usado no README e no dashboard.
BCB_SERIE_1_NOME: str = "Taxa de câmbio - Livre - Dólar americano (venda) - diário"
BCB_SERIE_1_UNIDADE: str = "R$/US$"
FONTE_BCB: str = "Banco Central do Brasil - SGS"

# Banco Mundial - Pink Sheet (CC BY 4.0). Arquivo baixado manualmente para data/raw/worldbank/.
WB_ARQUIVO: str = "CMO-Historical-Data-Monthly.xlsx"
WB_ABA: str = "Monthly Prices"
WB_SERIES: dict[str, str] = {  # série no projeto -> nome da coluna no arquivo
    "wb_soja": "Soybeans",
    "wb_milho": "Maize",
}
WB_UNIDADE_ARQUIVO: str = "($/mt)"
WB_UNIDADE: str = "US$/t"
FONTE_WB: str = "World Bank - Commodity Price Data (The Pink Sheet), CC BY 4.0"

# Mudanças de definição registradas na aba "Description" do Pink Sheet; marcadas nos gráficos.
QUEBRAS_DEFINICAO: dict[str, list[tuple[date, str]]] = {
    "wb_soja": [
        (date(2021, 1, 1), "U.S. Gulf Yellow Soybean #2, CIF Rotterdam"),
        (date(2025, 1, 1), "U.S. Soybeans, FOB U.S. Gulf"),
    ],
}

# CEPEA e CONAB: apenas locais; identificadores definidos quando houver arquivo baixado manualmente.

AVISO_INVESTIMENTO: str = "Não é recomendação de investimento."
