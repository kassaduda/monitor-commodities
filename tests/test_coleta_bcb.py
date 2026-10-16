from datetime import date

import pytest
import requests
import responses

from monitor.coleta import bcb

URL = bcb.URL_SGS.format(codigo=1)


def _sem_espera(_: float) -> None:
    pass


# --- janelas ---------------------------------------------------------------


def test_janelas_respeitam_limite_de_10_anos() -> None:
    assert bcb.janelas_de_anos(list(range(2010, 2027))) == [(2010, 2019), (2020, 2026)]


def test_janelas_separam_anos_nao_consecutivos() -> None:
    assert bcb.janelas_de_anos([2015, 2010, 2011]) == [(2010, 2011), (2015, 2015)]


def test_janelas_vazias() -> None:
    assert bcb.janelas_de_anos([]) == []


# --- baixar_periodo --------------------------------------------------------


@responses.activate
def test_baixar_periodo_envia_datas_no_formato_do_sgs() -> None:
    params = {"formato": "json", "dataInicial": "01/01/2010", "dataFinal": "31/12/2010"}
    responses.get(URL, json=[{"data": "04/01/2010", "valor": "1.7240"}],
                  match=[responses.matchers.query_param_matcher(params)])
    dados = bcb.baixar_periodo(1, date(2010, 1, 1), date(2010, 12, 31), session=requests.Session())
    assert dados == [{"data": "04/01/2010", "valor": "1.7240"}]


@responses.activate
def test_baixar_periodo_404_significa_sem_dados() -> None:
    responses.get(URL, status=404, json={"erro": {"detail": "Value(s) not found"}})
    assert bcb.baixar_periodo(1, date(2026, 10, 11), date(2026, 10, 12), session=requests.Session()) == []


@responses.activate
def test_baixar_periodo_tenta_de_novo_apos_502() -> None:
    responses.get(URL, status=502, body="<html>Indisponível</html>")
    responses.get(URL, json=[{"data": "04/01/2010", "valor": "1.7240"}])
    esperas: list[float] = []
    dados = bcb.baixar_periodo(1, date(2010, 1, 1), date(2010, 1, 31), session=requests.Session(),
                               dormir=esperas.append, espera_inicial=1.0)
    assert len(dados) == 1
    assert esperas == [1.0]


@responses.activate
def test_baixar_periodo_tenta_de_novo_apos_erro_de_conexao() -> None:
    responses.get(URL, body=requests.ConnectionError("rede caiu"))
    responses.get(URL, body=requests.Timeout("lento"))
    responses.get(URL, json=[{"data": "04/01/2010", "valor": "1.7240"}])
    esperas: list[float] = []
    dados = bcb.baixar_periodo(1, date(2010, 1, 1), date(2010, 1, 31), session=requests.Session(),
                               dormir=esperas.append, espera_inicial=1.0)
    assert len(dados) == 1
    assert esperas == [1.0, 2.0]  # espera exponencial


@responses.activate
def test_baixar_periodo_desiste_apos_esgotar_tentativas() -> None:
    responses.get(URL, status=503)
    with pytest.raises(bcb.ErroSGS, match="3 tentativas"):
        bcb.baixar_periodo(1, date(2010, 1, 1), date(2010, 1, 31), session=requests.Session(),
                           dormir=_sem_espera)
    assert len(responses.calls) == 3


@responses.activate
def test_baixar_periodo_nao_repete_erro_definitivo() -> None:
    responses.get(URL, status=406, json={"erro": "janela acima de 10 anos"})
    with pytest.raises(bcb.ErroSGS, match="406"):
        bcb.baixar_periodo(1, date(2000, 1, 1), date(2026, 1, 1), session=requests.Session(),
                           dormir=_sem_espera)
    assert len(responses.calls) == 1


# --- coletar_sgs (cache) ---------------------------------------------------


def test_coleta_baixa_em_janelas_de_ate_10_anos(api, tmp_path) -> None:
    bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=date(2026, 10, 14))
    assert api == [
        (date(2010, 1, 1), date(2019, 12, 31)),
        (date(2020, 1, 1), date(2026, 10, 14)),
    ]
    arquivos = sorted(p.name for p in (tmp_path / "bcb" / "sgs_1").glob("*.json"))
    assert arquivos == [f"{a}.json" for a in range(2010, 2027)]


def test_coleta_junta_janelas_sem_buracos_nem_duplicatas(api, tmp_path) -> None:
    dados = bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=date(2026, 10, 14))
    datas = [r["data"] for r in dados]
    assert len(datas) == len(set(datas))
    assert datas[0] == "05/01/2010" and datas[-1] == "05/10/2026"
    assert len(datas) == 2 * 12 * 16 + 2 * 9 + 1  # 2010-2025 completos + jan-set/2026 + 05/10/2026


def test_coleta_nao_baixa_de_novo_no_mesmo_dia(api, tmp_path) -> None:
    hoje = date(2026, 10, 14)
    primeira = bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=hoje)
    api.clear()
    segunda = bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=hoje)
    assert api == []
    assert segunda == primeira


def test_coleta_no_dia_seguinte_baixa_so_o_ano_corrente(api, tmp_path) -> None:
    bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=date(2026, 10, 14))
    api.clear()
    bcb.coletar_sgs(1, date(2010, 1, 1), dir_raw=tmp_path, hoje=date(2026, 10, 21))
    assert api == [(date(2026, 1, 1), date(2026, 10, 21))]


def test_ano_baixado_ainda_aberto_e_atualizado_depois_de_fechar(api, tmp_path) -> None:
    bcb.coletar_sgs(1, date(2025, 1, 1), dir_raw=tmp_path, hoje=date(2025, 12, 30))
    api.clear()
    bcb.coletar_sgs(1, date(2025, 1, 1), dir_raw=tmp_path, hoje=date(2026, 1, 2))
    assert api == [(date(2025, 1, 1), date(2026, 1, 2))]
    api.clear()
    bcb.coletar_sgs(1, date(2025, 1, 1), dir_raw=tmp_path, hoje=date(2026, 3, 1))
    assert api == [(date(2026, 1, 1), date(2026, 3, 1))]  # 2025 fechado não é baixado de novo


def test_coleta_filtra_pelo_periodo_pedido(api, tmp_path) -> None:
    dados = bcb.coletar_sgs(1, date(2015, 3, 10), date(2015, 4, 10), dir_raw=tmp_path, hoje=date(2026, 10, 14))
    assert [r["data"] for r in dados] == ["20/03/2015", "05/04/2015"]


def test_coleta_salva_ano_sem_dados_para_nao_repetir_consulta(api, tmp_path) -> None:
    bcb.coletar_sgs(1, date(2026, 10, 1), dir_raw=tmp_path, hoje=date(2026, 1, 3))  # inicio > fim
    assert api == []
    bcb.coletar_sgs(1, date(2026, 1, 1), dir_raw=tmp_path, hoje=date(2026, 1, 3))  # sem dia 5 ainda: 404
    bcb.coletar_sgs(1, date(2026, 1, 1), dir_raw=tmp_path, hoje=date(2026, 1, 3))
    assert api == [(date(2026, 1, 1), date(2026, 1, 3))]
