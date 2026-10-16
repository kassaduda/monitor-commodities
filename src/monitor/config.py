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

# CEPEA e CONAB: identificadores definidos nas etapas 3 e 4, após conferir os arquivos.

AVISO_INVESTIMENTO: str = "Não é recomendação de investimento."
