"""05 — Actualiza data/resultados/realidad_oficial.json con los resultados reales.

Fuente de verdad del proyecto. Se puede correr en bucle (cron) durante la jornada.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sofascore as ss
from utils import (
    REALIDAD_FILE,
    cargar_json,
    cargar_settings,
    clave_jornada,
    guardar_json,
)

ESTADOS_CERRADOS = {"finished"}


def main():
    settings = cargar_settings()
    comp = settings["competicion"]
    torneo_id = comp["sofascore_unique_tournament_id"]
    season_id = comp.get("sofascore_season_id")

    if not season_id:
        print("❌ Falta sofascore_season_id. Ejecuta antes el script 00.")
        return 1

    sesion = ss.crear_sesion()
    print(f"📥 Descargando resultados (temporada {season_id})...")
    eventos = ss.descargar_eventos(sesion, torneo_id, season_id)
    if not eventos:
        print("❌ SofaScore no devolvió partidos. Se conserva el fichero anterior.")
        return 1

    realidad = {}
    for ev in eventos:
        p = ss.parsear_evento(ev)
        if not p["jornada"]:
            continue
        clave = clave_jornada(p["jornada"])
        realidad.setdefault(clave, []).append({
            "id": p["id"],
            "local": p["local"],
            "visitante": p["visitante"],
            "id_escudo_local": p["id_escudo_local"],
            "id_escudo_visitante": p["id_escudo_visitante"],
            "fecha": p["fecha"],
            "goles_local": p["goles_local"],
            "goles_visitante": p["goles_visitante"],
            "estado": p["estado"],
        })

    for clave in realidad:
        realidad[clave].sort(key=lambda x: (x["fecha"] or "", x["local"]))
    realidad = {c: realidad[c] for c in sorted(realidad, key=lambda k: int(k[1:]))}

    anterior = cargar_json(REALIDAD_FILE, {})
    guardar_json(REALIDAD_FILE, realidad)

    jugados = sum(
        1 for js in realidad.values() for p in js if p["estado"] in ESTADOS_CERRADOS
    )
    total = sum(len(v) for v in realidad.values())
    cambios = "sin cambios" if anterior == realidad else "actualizado"
    print(f"✅ {jugados}/{total} partidos finalizados ({cambios}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
