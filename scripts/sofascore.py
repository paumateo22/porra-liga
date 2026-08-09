"""Cliente mínimo de la API oculta de SofaScore.

Se reutiliza la técnica del proyecto del mundial: curl_cffi con impersonate
para saltar el filtro anti-bot de Cloudflare.
"""
import time
from datetime import datetime, timezone

from curl_cffi import requests

from utils import cargar_settings

BASE = "https://www.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Referer": "https://www.sofascore.com/",
    "Accept": "*/*",
}

# Normalización de nombres de equipo tal y como los queremos mostrar.
# SofaScore usa nombres cortos en inglés/español mezclados.
MAPA_EQUIPOS = {
    "Barcelona": "Barcelona",
    "Real Madrid": "Real Madrid",
    "Atlético Madrid": "Atlético",
    "Atletico Madrid": "Atlético",
    "Athletic Club": "Athletic",
    "Real Sociedad": "Real Sociedad",
    "Real Betis": "Betis",
    "Betis": "Betis",
    "Villarreal": "Villarreal",
    "Valencia": "Valencia",
    "Sevilla": "Sevilla",
    "Celta Vigo": "Celta",
    "Celta de Vigo": "Celta",
    "Rayo Vallecano": "Rayo",
    "Osasuna": "Osasuna",
    "Getafe": "Getafe",
    "Girona": "Girona",
    "Mallorca": "Mallorca",
    "Alavés": "Alavés",
    "Deportivo Alavés": "Alavés",
    "Espanyol": "Espanyol",
    "RCD Espanyol": "Espanyol",
    "Elche": "Elche",
    "Levante": "Levante",
    "Real Oviedo": "Oviedo",
    "Oviedo": "Oviedo",
}


def nombre_equipo(bruto):
    """Devuelve el nombre normalizado; si no está mapeado, deja el original."""
    return MAPA_EQUIPOS.get(bruto, bruto)


def crear_sesion():
    return requests.Session(impersonate="chrome")


def get(sesion, ruta, intentos=3):
    url = f"{BASE}{ruta}"
    for n in range(intentos):
        try:
            r = sesion.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 404:
                return None
            if r.status_code == 200:
                return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️  Fallo en {ruta} ({e}); reintento {n + 1}/{intentos}")
        time.sleep(1.5 * (n + 1))
    return None


def resolver_season_id(sesion, torneo_id, etiqueta="26/27"):
    """Busca el id de temporada a partir de su etiqueta ('26/27')."""
    datos = get(sesion, f"/unique-tournament/{torneo_id}/seasons")
    if not datos:
        return None, []
    temporadas = datos.get("seasons", [])
    for t in temporadas:
        if t.get("year") == etiqueta:
            return t.get("id"), temporadas
    return None, temporadas


def descargar_eventos(sesion, torneo_id, season_id):
    """Baja todos los partidos de la temporada (jugados y por jugar)."""
    eventos = {}
    for tipo in ("last", "next"):
        pagina = 0
        while True:
            datos = get(
                sesion,
                f"/unique-tournament/{torneo_id}/season/{season_id}/events/{tipo}/{pagina}",
            )
            if not datos:
                break
            lote = datos.get("events", [])
            for ev in lote:
                eventos[ev["id"]] = ev
            if not datos.get("hasNextPage") or not lote:
                break
            pagina += 1
            time.sleep(0.4)
    return list(eventos.values())


def fecha_local(timestamp_unix):
    """Unix -> ISO local naive, coherente con el formato del mundial."""
    if not timestamp_unix:
        return None
    tz = None
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(cargar_settings()["competicion"]["zona_horaria"])
    except Exception:  # noqa: BLE001
        pass
    dt = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)
    if tz:
        dt = dt.astimezone(tz)
    return dt.replace(tzinfo=None).isoformat(timespec="seconds")


def parsear_evento(ev):
    """Extrae los campos que nos interesan de un evento crudo."""
    ronda = (ev.get("roundInfo") or {}).get("round")
    equipo_local = ev.get("homeTeam") or {}
    equipo_visitante = ev.get("awayTeam") or {}
    local = nombre_equipo(equipo_local.get("name", "TBD"))
    visitante = nombre_equipo(equipo_visitante.get("name", "TBD"))
    estado = ((ev.get("status") or {}).get("type")) or "notstarted"
    gl = (ev.get("homeScore") or {}).get("current")
    gv = (ev.get("awayScore") or {}).get("current")
    return {
        "id": ev.get("id"),
        "jornada": ronda,
        "local": local,
        "visitante": visitante,
        "id_escudo_local": equipo_local.get("id"),
        "id_escudo_visitante": equipo_visitante.get("id"),
        "fecha": fecha_local(ev.get("startTimestamp")),
        "estado": estado,
        "goles_local": gl,
        "goles_visitante": gv,
    }
