"""O texto de interface não pode ter `$` sem escape (o Streamlit o leria como LaTeX)."""

import re
import sys
from pathlib import Path

import pytest

from monitor import config
from monitor.resultados import ARQUIVO_META, ARQUIVOS

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import ui  # noqa: E402

SEM_ESCAPE = re.compile(r"(?<!\\)\$")


def test_escapar_cifrao():
    assert ui.escapar("R$/US$") == r"R\$/US\$"
    assert ui.escapar(r"R\$ 5") == r"R\$ 5"  # idempotente
    assert ui.escapar("sem cifrão") == "sem cifrão"


def _textos(at) -> list[str]:
    textos: list[str] = []
    for tipo in ("markdown", "caption", "info", "warning", "success", "error", "subheader", "title"):
        textos += [str(e.value) for e in getattr(at, tipo)]
    for m in at.metric:
        textos += [m.label, m.value, m.help or "", m.delta or ""]
    for w in list(at.radio) + list(at.selectbox) + list(at.slider):
        textos += [w.label, *map(str, getattr(w, "options", []))]
    textos += [e.label for e in at.expander] + [t.label for t in at.tabs]
    return [t for t in textos if t]


def test_interface_sem_cifrao_sem_escape():
    if not all((config.DIR_PROCESSED / a).exists() for a in [*ARQUIVOS.values(), ARQUIVO_META]):
        pytest.skip("resultados ainda não gerados (python -m monitor.resultados)")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=120).run()
    assert not at.exception
    textos = _textos(at)
    assert any(r"R\$/US\$" in t for t in textos), "esperava textos com cifrão escapado (o teste não viu a interface)"
    ruins = [t[:80] for t in textos if SEM_ESCAPE.search(t)]
    assert not ruins, f"$ sem escape em: {ruins}"


def test_aviso_de_previsao_ilustrativa_aparece_uma_vez_so():
    if not all((config.DIR_PROCESSED / a).exists() for a in [*ARQUIVOS.values(), ARQUIVO_META]):
        pytest.skip("resultados ainda não gerados (python -m monitor.resultados)")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=120).run()
    com_aviso = [t for t in _textos(at) if config.AVISO_INVESTIMENTO.lower().rstrip(".") in t.lower()]
    assert len(com_aviso) == 1, com_aviso
    assert "Previsão ilustrativa" in com_aviso[0]
    # o selo fica fora das abas (visível em todas): é HTML próprio, não um alerta dentro de uma aba
    assert 'class="aviso-previsao"' in com_aviso[0]
    assert not any(config.AVISO_INVESTIMENTO.lower().rstrip(".") in str(w.value).lower() for w in at.warning)


def test_sem_cepea_conab_e_com_creditos_no_rodape():
    """Dashboard público: nada de CEPEA/CONAB na tela nem no código do app; créditos obrigatórios no rodapé."""
    if not all((config.DIR_PROCESSED / a).exists() for a in [*ARQUIVOS.values(), ARQUIVO_META]):
        pytest.skip("resultados ainda não gerados (python -m monitor.resultados)")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=120).run()
    assert not at.exception
    tela = " ".join(x for x in _textos(at) if not x.lstrip().startswith("<style>")).lower()  # o CSS leva a foto em base64
    codigo = " ".join(p.read_text(encoding="utf-8") for p in APP.glob("*.py")).lower()
    for proibida in ("cepea", "conab", "esalq"):
        assert proibida not in tela and proibida not in codigo, proibida
    assert [t.label for t in at.tabs] == ["Dólar", "Soja e milho", "Dólar × commodities", "Razão soja/milho", "Backtest e previsão"]
    rodape = [str(m.value) for m in at.markdown if 'class="rodape-fontes"' in str(m.value)]
    assert len(rodape) == 1
    for credito in ("Banco Central do Brasil", "Banco Mundial", "CC BY 4.0"):
        assert credito in rodape[0]


def test_css_fundo_com_imagem_local_e_overlay(tmp_path):
    import base64

    import estilo

    assert estilo.css_fundo(tmp_path / "nao_existe.jpg") == ""  # sem imagem, o app segue só com a cor do tema
    img = tmp_path / "fundo.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0fake")
    css = estilo.css_fundo(img)
    assert base64.b64encode(img.read_bytes()).decode() in css
    assert "data:image/jpeg;base64," in css and "cover" in css
    assert "rgba(10, 22, 18, 0.85)" in css and "rgba(10, 22, 18, 0.95)" in css
    assert not SEM_ESCAPE.search(css)


def test_imagem_de_fundo_do_repositorio_e_leve():
    assert config.ARQUIVO_FUNDO.exists()
    assert config.ARQUIVO_FUNDO.stat().st_size < 300_000  # vai inline no CSS a cada carga da página


def test_simulador_de_stress_mostra_conversao_e_aviso():
    if not all((config.DIR_PROCESSED / a).exists() for a in [*ARQUIVOS.values(), ARQUIVO_META]):
        pytest.skip("resultados ainda não gerados (python -m monitor.resultados)")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=120).run()
    def slider_do_dolar(a):
        return next(s for s in a.slider if "Dólar simulado" in s.label)

    def sacas(a) -> float:
        valor = next(m.value for m in a.metric if "sc 60 kg" in m.label)  # o `$` vem escapado na tela
        return float(valor.replace("\\", "").replace("R$", "").replace("/sc", "").replace(".", "").replace(",", ".").strip())

    assert (slider_do_dolar(at).min, slider_do_dolar(at).max) == (4.0, 7.0)
    avisos = [str(i.value) for i in at.info] + [str(c.value) for c in at.caption]
    assert any("Ceteris Paribus" in a and "Não prevê a reação real do mercado" in a for a in avisos)

    base = sacas(at)
    em_7 = sacas(slider_do_dolar(at).set_value(7.0).run())
    em_4 = sacas(slider_do_dolar(at).set_value(4.0).run())
    assert em_4 < base < em_7  # dólar mais caro, soja mais cara em R$/sc
    assert em_7 / em_4 == pytest.approx(7.0 / 4.0, rel=1e-3)  # conversão proporcional ao câmbio
