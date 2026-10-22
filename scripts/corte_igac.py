"""G2 (F5): descubre el corte vigente de la base catastral del IGAC y lo pone en el catálogo.

El servicio cambia de nombre cada mes (`Base_Catastral_Publica_del_Gestor_IGAC_<MM>_<AAAA>`), y no
siempre con ese patrón: en 2026 conviven `…_06_2026` y `Base_Catastral_Publica_IGAC_de_octubre`, que
es el corte de octubre de **2025**. Por eso el corte se lee de la descripción del servicio («a corte
de 30 de junio de 2026»), no del nombre.

Son pocas llamadas: el directorio de servicios y la descripción de cada candidato.

Uso: `uv run scripts/corte_igac.py` (informa) o `uv run scripts/corte_igac.py --escribir`.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import httpx

DIRECTORIO = "https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services"
PREFIJO = "Base_Catastral_Publica"
FUENTES = Path(__file__).resolve().parents[1] / "catalogo" / "fuentes"
_NOMBRES_MES = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"
)
MESES = {m: i for i, m in enumerate(_NOMBRES_MES.split(), start=1)}
CORTE = re.compile(r"corte de (\d{1,2}) de ([a-záéíóú]+) de (\d{4})", re.IGNORECASE)
URL_SERVICIO = re.compile(rf"^url: {re.escape(DIRECTORIO)}/({PREFIJO}[^/]*)/FeatureServer$", re.M)


def fecha_de_corte(descripcion: str) -> date | None:
    m = CORTE.search(descripcion or "")
    if not m or m.group(2).lower() not in MESES:
        return None
    return date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))


def vigente(http: httpx.Client) -> tuple[str, date]:
    """El servicio con la fecha de corte más reciente."""
    servicios = http.get(DIRECTORIO, params={"f": "json"}).json().get("services") or []
    candidatos = [
        s["name"]
        for s in servicios
        if s.get("type") == "FeatureServer" and s["name"].startswith(PREFIJO)
    ]
    cortes: list[tuple[date, str]] = []
    for nombre in candidatos:
        meta = http.get(f"{DIRECTORIO}/{nombre}/FeatureServer", params={"f": "json"}).json()
        corte = fecha_de_corte(meta.get("serviceDescription") or meta.get("description") or "")
        print(f"  {nombre}: {corte or 'sin fecha de corte en la descripción'}")
        if corte:
            cortes.append((corte, nombre))
    if not cortes:
        raise SystemExit("ningún servicio dice su fecha de corte: revisar a mano")
    corte, nombre = max(cortes)
    return nombre, corte


def fichas_catastrales() -> dict[Path, str]:
    """Las fichas que apuntan a la base catastral, con el servicio al que apuntan hoy."""
    out = {}
    for ficha in sorted(FUENTES.glob("igac.catastro.*.yaml")):
        m = URL_SERVICIO.search(ficha.read_text(encoding="utf-8"))
        if m:
            out[ficha] = m.group(1)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escribir", action="store_true", help="actualiza las fichas del catálogo")
    args = parser.parse_args()
    with httpx.Client(timeout=60, headers={"User-Agent": "terranova-catalogo/1"}) as http:
        nombre, corte = vigente(http)
    print(f"vigente: {nombre} (corte {corte.isoformat()})")
    viejas = {f: s for f, s in fichas_catastrales().items() if s != nombre}
    if not viejas:
        print("el catálogo ya apunta al corte vigente")
        return 0
    for ficha, servicio in viejas.items():
        print(f"  {ficha.name}: {servicio} → {nombre}")
        if args.escribir:
            texto = ficha.read_text(encoding="utf-8")
            ficha.write_text(texto.replace(f"/{servicio}/", f"/{nombre}/"), encoding="utf-8")
    if not args.escribir:
        print("corre con --escribir, regraba las doradas y abre un PR (runbook §2)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
