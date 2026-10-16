import json
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from monitor.coleta import bcb


def _data(txt: str) -> date:
    return datetime.strptime(txt, "%d/%m/%Y").date()


def _api_falsa(chamadas: list[tuple[date, date]]):
    """Imita o SGS: 406 acima de 10 anos, 404 sem valores, um valor nos dias 5 e 20 de cada mês."""

    def callback(request):
        q = parse_qs(urlparse(request.url).query)
        ini, fim = _data(q["dataInicial"][0]), _data(q["dataFinal"][0])
        chamadas.append((ini, fim))
        if fim - ini > timedelta(days=3653):
            return 406, {}, json.dumps({"erro": "janela acima de 10 anos"})
        dias = (ini + timedelta(days=i) for i in range((fim - ini).days + 1))
        dados = [{"data": d.strftime("%d/%m/%Y"), "valor": "5.0000"} for d in dias if d.day in (5, 20)]
        if not dados:
            return 404, {}, json.dumps({"erro": {"statusCode": 404, "detail": "Value(s) not found"}})
        return 200, {}, json.dumps(dados)

    return callback


@pytest.fixture
def api():
    """SGS série 1 simulado; a lista devolvida registra (inicio, fim) de cada requisição."""
    chamadas: list[tuple[date, date]] = []
    with responses.RequestsMock() as rsps:
        rsps.add_callback(responses.GET, bcb.URL_SGS.format(codigo=1), callback=_api_falsa(chamadas))
        yield chamadas
