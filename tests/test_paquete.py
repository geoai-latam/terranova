from importlib.metadata import version

import terranova


def test_version_del_paquete_coincide_con_la_instalada() -> None:
    assert terranova.__version__ == version("terranova")
