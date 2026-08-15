"""Utilidades compartidas por todos los scripts de la porra."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RESULTADOS_DIR = DATA_DIR / "resultados"
REPORTES_DIR = DATA_DIR / "reportes"
ANALISIS_DIR = DATA_DIR / "analisis"
ENTRADAS_DIR = ROOT / "entradas"
PROCESADAS_DIR = ENTRADAS_DIR / "procesadas"
PARTICIPANTES_DIR = ROOT / "participantes"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
CALENDARIO_FILE = CONFIG_DIR / "calendario.json"
PARTICIPANTES_FILE = CONFIG_DIR / "participantes.json"
NOMBRES_FILE = CONFIG_DIR / "nombres.txt"
REALIDAD_FILE = RESULTADOS_DIR / "realidad_oficial.json"
CLASIFICACION_FILE = DATA_DIR / "clasificacion.json"


def cargar_json(ruta, por_defecto=None):
    ruta = Path(ruta)
    if not ruta.exists():
        if por_defecto is None:
            raise FileNotFoundError(f"No existe {ruta}")
        return por_defecto
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta, datos):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def cargar_settings():
    return cargar_json(SETTINGS_FILE)


def slug(nombre):
    """'Miguel Dykan' -> 'miguel_dykan'. Mantiene acentos como en el mundial."""
    limpio = nombre.strip().lower()
    limpio = re.sub(r"\s+", "_", limpio)
    limpio = re.sub(r"[^\w_áéíóúüñ]", "", limpio, flags=re.UNICODE)
    return limpio


def sin_acentos(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    ).lower()


def clave_jornada(numero):
    """2 -> 'J02'."""
    return f"J{int(numero):02d}"


def numero_jornada(clave):
    """'J02' -> 2."""
    return int(str(clave).lstrip("Jj"))


def clave_partido(local, visitante):
    """Clave legible, misma convención que el proyecto del mundial."""
    return f"{local}_vs_{visitante}"


def signo(gl, gv):
    """1X2 a partir de un marcador."""
    if gl is None or gv is None:
        return None
    gl, gv = int(gl), int(gv)
    if gl > gv:
        return "1"
    if gl < gv:
        return "2"
    return "X"


def carpeta_participante(nombre_slug):
    return PARTICIPANTES_DIR / nombre_slug


def listar_participantes():
    """Devuelve la lista de participantes desde config/participantes.json."""
    datos = cargar_json(PARTICIPANTES_FILE, {"participantes": []})
    return datos.get("participantes", [])


PATRON_INSIGNIA_FINAL = re.compile(r"\s*([^\s(]+)\(([^)]*)\)$")


def cargar_nombres_mostrados():
    """Lee config/nombres.txt y devuelve {slug: (nombre_base, [insignias])}.

    Formato del fichero, una persona por línea:

        Pau; Pau 🏆(Liga 2025/26) ⭐(Mundial 2026)
        Ivan; Ivan

    Lo de antes de ";" es el nombre con el que esa persona pronostica (se
    convierte a slug para casar con participantes/<slug>/). Lo de después es
    lo que se muestra en la web: el nombre, seguido de cero o más insignias
    pegadas al final con la forma "emoji(descripción)" — la descripción puede
    llevar espacios, como "Liga 2025/26". Las insignias son acumulables y se
    van despegando siempre desde el final de la línea. Líneas vacías o que
    empiezan por # se ignoran.
    """
    resultado = {}
    if not NOMBRES_FILE.exists():
        return resultado

    for linea in NOMBRES_FILE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or ";" not in linea:
            continue
        login, mostrado = linea.split(";", 1)
        login, mostrado = login.strip(), mostrado.strip()
        if not login or not mostrado:
            continue

        insignias = []
        resto = mostrado
        while True:
            m = PATRON_INSIGNIA_FINAL.search(resto)
            if not m:
                break
            insignias.insert(0, {"emoji": m.group(1), "descripcion": m.group(2).strip()})
            resto = resto[:m.start()]
        nombre_base = resto.strip() or mostrado

        resultado[slug(login)] = (nombre_base, insignias)
    return resultado
