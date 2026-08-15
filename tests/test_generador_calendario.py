"""Test de scripts/00_generador_calendario.py — deduplicación de partidos.

Reproduce el patrón de bug real reportado: un partido reprogramado por
SofaScore puede quedarse "fantasma" con su id viejo en la respuesta de la
API, junto al id nuevo — dando una jornada con 11 partidos y uno duplicado
en vez de 10. Como no hay acceso a la API real desde este entorno, se
sustituye scripts.sofascore.descargar_eventos() por datos de prueba
construidos a mano que reproducen exactamente ese patrón.

Uso:
    python tests/test_generador_calendario.py
"""
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

from utils import CALENDARIO_FILE, SETTINGS_FILE, cargar_json, guardar_json  # noqa: E402

EQUIPOS = [
    "Barcelona", "Real Madrid", "Atlético", "Athletic", "Real Sociedad",
    "Betis", "Villarreal", "Valencia", "Sevilla", "Celta",
    "Rayo", "Osasuna", "Getafe", "Girona", "Mallorca",
    "Alavés", "Espanyol", "Elche", "Levante", "Oviedo",
]

fallos = []


def check(cond, desc):
    marca = "✅" if cond else "❌"
    print(f"  {marca} {desc}")
    if not cond:
        fallos.append(desc)


def evento(id_, jornada, local, visitante, offset_dias):
    ahora = datetime(2026, 8, 1)
    return {
        "id": id_,
        "roundInfo": {"round": jornada},
        "homeTeam": {"name": local, "id": 1000 + hash(local) % 100},
        "awayTeam": {"name": visitante, "id": 2000 + hash(visitante) % 100},
        "status": {"type": "notstarted"},
        "homeScore": {}, "awayScore": {},
        "startTimestamp": int((ahora + timedelta(days=offset_dias)).timestamp()),
    }


def construir_eventos_de_prueba():
    """J01 con 10 partidos normales + 1 duplicado real (Rayo-Osasuna con un
    segundo id más alto, simulando el reprogramado). J06 con 9 partidos +
    1 diez que se pierde por no tener roundInfo.round asignado."""
    eventos = []
    pid = 100
    for i in range(0, 20, 2):
        pid += 1
        eventos.append(evento(pid, 1, EQUIPOS[i], EQUIPOS[i + 1], 7))
    # Duplicado real: MISMO par exacto (Rayo, Osasuna) que ya está arriba.
    eventos.append(evento(9999, 1, "Rayo", "Osasuna", 9))

    for i in range(0, 18, 2):
        pid += 1
        eventos.append(evento(pid, 6, EQUIPOS[i], EQUIPOS[i + 1], 42))
    pid += 1
    eventos.append(evento(pid, None, EQUIPOS[18], EQUIPOS[19], 42))
    return eventos


def main():
    backup_calendario = CALENDARIO_FILE.read_text(encoding="utf-8") if CALENDARIO_FILE.exists() else None
    backup_settings = SETTINGS_FILE.read_text(encoding="utf-8")

    try:
        settings = cargar_json(SETTINGS_FILE)
        settings["competicion"]["sofascore_season_id"] = 99999  # ya "resuelto", que no intente buscarlo
        guardar_json(SETTINGS_FILE, settings)

        eventos = construir_eventos_de_prueba()

        import sofascore as ss
        with mock.patch.object(ss, "descargar_eventos", return_value=eventos), \
             mock.patch.object(ss, "crear_sesion", return_value=None):
            spec = importlib.util.spec_from_file_location("gen", RAIZ / "scripts" / "00_generador_calendario.py")
            gen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gen)
            gen.main()

        resultado = json.loads(CALENDARIO_FILE.read_text(encoding="utf-8"))

        print("\n═══ Deduplicación de partidos reprogramados ═══")
        check("J01" in resultado, "la J01 se generó")
        j01 = resultado.get("J01", [])
        check(len(j01) == 10, f"J01 tiene exactamente 10 partidos (vio {len(j01)})")
        ids_j01 = [p["id"] for p in j01]
        check(len(ids_j01) == len(set(ids_j01)), "sin ids repetidos dentro de la J01")
        pares = [(p["local"], p["visitante"]) for p in j01]
        check(len(pares) == len(set(pares)), "sin ningún emparejamiento de equipos repetido en la J01")
        rayo_osasuna = [p for p in j01 if p["local"] == "Rayo" and p["visitante"] == "Osasuna"]
        check(len(rayo_osasuna) == 1, "Rayo-Osasuna aparece una sola vez, no dos")
        check(rayo_osasuna and rayo_osasuna[0]["id"] == 9999,
              "se conserva el id más alto (el del partido reprogramado), no el fantasma viejo")

        print("\n═══ Jornada corta por partido sin ronda asignada ═══")
        j06 = resultado.get("J06", [])
        check(len(j06) == 9, f"J06 se queda en 9 partidos, no se inventa el que falta (vio {len(j06)})")

    finally:
        if backup_calendario is not None:
            CALENDARIO_FILE.write_text(backup_calendario, encoding="utf-8")
        elif CALENDARIO_FILE.exists():
            CALENDARIO_FILE.unlink()
        SETTINGS_FILE.write_text(backup_settings, encoding="utf-8")

    print("\n" + "─" * 62)
    if fallos:
        print(f"❌ {len(fallos)} comprobación(es) fallida(s):")
        for f in fallos:
            print(f"   · {f}")
        return 1
    print("✅ Todas las comprobaciones del generador de calendario pasan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
