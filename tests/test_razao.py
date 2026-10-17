import pandas as pd
import pytest

from monitor.analise.conversao import reais_por_saca
from monitor.analise.razao import razao_soja_milho
from monitor.limpeza import COLUNAS_PADRAO


def serie(valores, nome, unidade="US$/t"):
    datas = pd.date_range("2020-01-01", periods=len(valores), freq="MS")
    return pd.DataFrame({"data": datas, "serie": nome, "valor": valores, "unidade": unidade, "fonte": f"fonte {nome}"})[COLUNAS_PADRAO]


def test_razao_soja_milho_divide_e_alinha_datas():
    soja, milho = serie([500.0, 600.0, 450.0], "wb_soja"), serie([200.0, 240.0], "wb_milho")
    r = razao_soja_milho(soja, milho)
    assert list(r["valor"]) == [2.5, 2.5]  # só os meses nas duas séries
    assert r["serie"].iloc[0] == "razao_soja_milho" and "adimensional" in r["unidade"].iloc[0]
    assert r["fonte"].iloc[0] == "fonte wb_soja; fonte wb_milho"


def test_razao_exige_us_por_tonelada_e_milho_positivo():
    with pytest.raises(ValueError, match="US\$/t"):
        razao_soja_milho(serie([1.0], "wb_soja", "R$/t"), serie([1.0], "wb_milho"))
    with pytest.raises(ValueError, match="não positivo"):
        razao_soja_milho(serie([1.0], "wb_soja"), serie([0.0], "wb_milho"))


def test_reais_por_saca_e_proporcional_ao_cambio():
    assert reais_por_saca(500.0, 5.0) == pytest.approx(150.0)  # 500 US$/t × 5 R$/US$ = 2500 R$/t → 60 kg = 150
    assert reais_por_saca(500.0, 6.0) == pytest.approx(reais_por_saca(500.0, 5.0) * 6 / 5)
