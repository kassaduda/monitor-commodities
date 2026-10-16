from monitor import config


def test_caminhos_dentro_do_projeto() -> None:
    assert config.DIR_RAW.parent == config.DIR_DADOS
    assert config.DIR_PROCESSED.parent == config.DIR_DADOS
    assert (config.RAIZ / "pyproject.toml").exists()


def test_series_bcb_tem_codigos_inteiros() -> None:
    assert config.BCB_SERIES
    assert all(isinstance(c, int) and c > 0 for c in config.BCB_SERIES.values())


def test_readme_cita_nome_oficial_da_serie_sgs_1() -> None:
    readme = (config.RAIZ / "README.md").read_text(encoding="utf-8")
    assert config.BCB_SERIE_1_NOME in readme


def test_aviso_de_investimento() -> None:
    assert config.AVISO_INVESTIMENTO == "Não é recomendação de investimento."
